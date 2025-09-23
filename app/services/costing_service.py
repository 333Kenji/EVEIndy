from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Dict, List, Tuple

import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings
from app.services.bom import build_bom_tree
from app.services.inventory import get_on_hand


def _engine():
    return sa.create_engine(Settings().database_url)


def _latest_mid(conn, region_id: int, type_id: int):
    row = conn.execute(
        text(
            """
            with latest as (
                select distinct on (type_id, side) type_id, side, ts, best_px
                from orderbook_snapshots
                where region_id=:r and type_id=:t
                order by type_id, side, ts desc
            )
            select (select best_px from latest where side='bid') as bid,
                   (select best_px from latest where side='ask') as ask
            """
        ),
        {"r": region_id, "t": type_id},
    ).fetchone()
    if not row:
        return None
    bid, ask = row
    if bid is None or ask is None:
        return None
    return (bid + ask) / 2


@dataclass
class CostLine:
    type_id: int
    qty: int
    unit_price: float
    cost: float


@dataclass
class CostSummary:
    product_id: int
    runs: int
    lines: List[CostLine]
    total_cost: float


def cost_product(product_id: int, *, region_id: int, runs: int = 1, me_bonus: float = 0.0, owner_scope: str | None = None) -> CostSummary | None:
    """Compute a simple material cost for a product using latest mid prices and ME bonus.

    This is a pragmatic costing that multiplies material quantities by (1 - me_bonus),
    applies ceil per-run integers, and sums using latest mid from orderbook_snapshots.
    """
    tree = build_bom_tree(product_id, max_depth=1)  # seed for top-level materials
    if not tree:
        return None
    me = max(0.0, min(0.5, me_bonus))
    engine = _engine()
    lines: List[CostLine] = []
    def _blueprint_for_product(conn, pid: int):
        row = conn.execute(text("select type_id, product_id, activity, materials, coalesce(output_qty,1) from blueprints where product_id=:p limit 1"), {"p": pid}).fetchone()
        if not row:
            return None
        return {"type_id": int(row[0]), "product_id": int(row[1]), "activity": row[2], "materials": row[3], "output_qty": int(row[4] or 1)}

    # Preload on-hand valuation if owner_scope provided (policy: RA for holdings; spot for shortfalls)
    on_hand = get_on_hand(owner_scope, None) if owner_scope else {}

    def cost_material(conn, t_id: int, qty_needed: int, depth: int = 0, max_depth: int = 4) -> Tuple[float, List[CostLine]]:
        bp = _blueprint_for_product(conn, t_id)
        if not bp or depth >= max_depth:
            # Apply policy: use RA for on-hand upto available; price only deficits via spot
            total_cost = 0.0
            lines: List[CostLine] = []
            remaining = qty_needed
            if owner_scope and t_id in on_hand and on_hand[t_id]["qty"] > 0:
                avail = int(on_hand[t_id]["qty"])
                use = min(avail, remaining)
                if use > 0:
                    ra = on_hand[t_id]["avg_cost"]
                    total_cost += ra * use
                    lines.append(CostLine(type_id=t_id, qty=use, unit_price=float(ra), cost=float(ra) * use))
                    remaining -= use
                    on_hand[t_id]["qty"] = avail - use  # reduce available for subsequent calls
            if remaining > 0:
                price = float(_latest_mid(conn, region_id, t_id) or 0)
                total_cost += price * remaining
                lines.append(CostLine(type_id=t_id, qty=remaining, unit_price=price, cost=price * remaining))
            return total_cost, lines
        subtotal = 0.0
        out_lines: List[CostLine] = []
        # Calculate required runs using output quantity
        output_qty = int(bp.get("output_qty") or 1)
        runs_required = max(1, ceil(qty_needed / max(1, output_qty)))
        for mat in bp["materials"]:
            mid = int(mat.get("type_id"))
            mqty = int(mat.get("qty") or mat.get("quantity") or 0)
            adj = ceil(mqty * (1 - me))
            child_cost, child_lines = cost_material(conn, mid, adj * runs_required, depth + 1, max_depth)
            subtotal += child_cost
            out_lines.extend(child_lines)
        return subtotal, out_lines

    with engine.connect() as conn:
        total_cost = 0.0
        for m in tree.materials:
            mid = int(m.get("type_id"))
            qty_per_run = int(m.get("qty") or m.get("quantity") or 0)
            adj = ceil(qty_per_run * (1 - me))
            c, ls = cost_material(conn, mid, adj * runs)
            total_cost += c
            lines.extend(ls)
    total = sum(l.cost for l in lines)
    return CostSummary(product_id=product_id, runs=runs, lines=lines, total_cost=total)
