from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sqlalchemy import text

from app.db import get_engine


@dataclass
class BOMNode:
    type_id: int
    product_id: int
    activity: str
    materials: List[dict]
    children: List["BOMNode"]


def search_products(query: str, limit: int = 20) -> List[dict]:
    sql = text("select type_id, name from type_ids where lower(name) like :q order by name limit :lim")
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"q": f"%{query.lower()}%", "lim": limit}).fetchall()
    return [{"type_id": int(r[0]), "name": r[1]} for r in rows]


def _blueprint_for_product(conn, product_id: int) -> dict | None:
    row = conn.execute(
        text("select type_id, product_id, activity, materials from blueprints where product_id=:p limit 1"),
        {"p": product_id},
    ).fetchone()
    if not row:
        return None
    return {"type_id": int(row[0]), "product_id": int(row[1]), "activity": row[2], "materials": row[3]}


def build_bom_tree(product_id: int, max_depth: int = 4) -> BOMNode | None:
    with get_engine().connect() as conn:
        bp = _blueprint_for_product(conn, product_id)
        if not bp:
            return None

        def rec(pid: int, depth: int) -> BOMNode | None:
            data = _blueprint_for_product(conn, pid)
            if not data:
                return None
            children: List[BOMNode] = []
            if depth < max_depth:
                for m in data["materials"]:
                    mid = int(m.get("type_id") or 0)
                    if mid:
                        child = rec(mid, depth + 1)
                        if child:
                            children.append(child)
            return BOMNode(
                type_id=int(data["type_id"]),
                product_id=int(data["product_id"]),
                activity=str(data["activity"]),
                materials=list(data["materials"]),
                children=children,
            )

        return rec(product_id, 0)

