from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query

from app.services import inventory as inventory_service


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/valuation")
def inventory_valuation(owner_scope: str = Query(...), type_id: List[int] | None = Query(default=None)):
    data = inventory_service.get_on_hand(owner_scope, type_id)
    return {"owner_scope": owner_scope, "items": [{"type_id": k, **v} for k, v in data.items()]}


@router.get("/wip")
def inventory_wip(owner_scope: str = Query(...)):
    data = inventory_service.get_wip(owner_scope)
    return {"owner_scope": owner_scope, "items": [{"type_id": k, "qty": v} for k, v in data.items()]}

