from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.bom import build_bom_tree, search_products
from app.services.costing_service import cost_product

router = APIRouter(prefix="/bom", tags=["bom"])


@router.get("/search")
def bom_search(q: str = Query(..., min_length=2), limit: int = 20):
    return {"results": search_products(q, limit)}


@router.get("/tree")
def bom_tree(product_id: int, max_depth: int = 4):
    tree = build_bom_tree(product_id, max_depth)
    if not tree:
        raise HTTPException(status_code=404, detail="Blueprint not found for product")
    # Serialize dataclass recursively
    def to_dict(node):  # noqa: ANN001
        return {
            "type_id": node.type_id,
            "product_id": node.product_id,
            "activity": node.activity,
            "materials": node.materials,
            "children": [to_dict(c) for c in node.children],
        }

    return to_dict(tree)


@router.post("/cost")
def bom_cost(payload: dict):
    try:
        product_id = int(payload.get("product_id"))
        region_id = int(payload.get("region_id", 10000002))
        runs = int(payload.get("runs", 1))
        me = float(payload.get("me_bonus", 0.0))
        owner_scope = payload.get("owner_scope")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="Invalid payload") from exc
    res = cost_product(product_id, region_id=region_id, runs=runs, me_bonus=me, owner_scope=owner_scope)
    if not res:
        raise HTTPException(status_code=404, detail="Blueprint not found for product")
    return {
        "product_id": res.product_id,
        "runs": res.runs,
        "total_cost": res.total_cost,
        "lines": [
            {"type_id": l.type_id, "qty": l.qty, "unit_price": l.unit_price, "cost": l.cost} for l in res.lines
        ],
    }
