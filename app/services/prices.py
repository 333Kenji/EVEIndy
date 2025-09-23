from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from sqlalchemy import text

from app.db import get_engine


@dataclass(frozen=True)
class Quote:
    type_id: int
    region_id: int
    bid: Decimal
    ask: Decimal
    mid: Decimal
    bid_qty: Decimal
    ask_qty: Decimal
    depth_qty_1pct: Decimal
    depth_qty_5pct: Decimal
    stdev_pct: Decimal | None
    spread: Decimal
    ts: datetime


def latest_quotes(region_id: int, type_ids: Sequence[int]) -> list[Quote]:
    if not type_ids:
        return []
    sql = text(
        """
        with latest as (
            select distinct on (type_id, side)
                type_id,
                side,
                ts,
                best_px,
                best_qty,
                depth_qty_1pct,
                depth_qty_5pct,
                stdev_pct
            from orderbook_snapshots
            where region_id = :region_id and type_id = any(:type_ids)
            order by type_id, side, ts desc
        )
        select b.type_id as type_id,
               :region_id as region_id,
               b.best_px as bid,
               a.best_px as ask,
               (b.best_px + a.best_px)/2 as mid,
               b.best_qty as bid_qty,
               a.best_qty as ask_qty,
               a.depth_qty_1pct as depth_qty_1pct,
               a.depth_qty_5pct as depth_qty_5pct,
               coalesce(a.stdev_pct, b.stdev_pct) as stdev_pct,
               (a.best_px - b.best_px) as spread,
               greatest(b.ts, a.ts) as ts
        from latest b
        join latest a on a.type_id = b.type_id and a.side = 'ask'
        where b.side = 'bid'
        order by b.type_id
        """
    )
    # sqlalchemy passes arrays differently per dialect; for psycopg2 we can pass list
    params = {"region_id": region_id, "type_ids": list(type_ids)}
    out: list[Quote] = []
    with get_engine().connect() as conn:
        for row in conn.execute(sql, params):
            out.append(
                Quote(
                    type_id=int(row.type_id),
                    region_id=int(region_id),
                    bid=Decimal(row.bid),
                    ask=Decimal(row.ask),
                    mid=Decimal(row.mid),
                    bid_qty=Decimal(row.bid_qty or 0),
                    ask_qty=Decimal(row.ask_qty or 0),
                    depth_qty_1pct=Decimal(row.depth_qty_1pct or 0),
                    depth_qty_5pct=Decimal(row.depth_qty_5pct or 0),
                    stdev_pct=Decimal(row.stdev_pct) if row.stdev_pct is not None else None,
                    spread=Decimal(row.spread),
                    ts=row.ts,
                )
            )
    return out

