from __future__ import annotations

from decimal import Decimal
from typing import List

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict

from app.services import inventory as inventory_service


router = APIRouter(prefix="/inventory", tags=["inventory"])


DECIMAL_CONFIG = ConfigDict(json_encoders={Decimal: lambda value: format(value, "f")})


class InventoryValuationItem(BaseModel):
    model_config = DECIMAL_CONFIG

    type_id: int
    qty: Decimal
    avg_cost: Decimal


class InventoryValuationResponse(BaseModel):
    model_config = DECIMAL_CONFIG

    owner_scope: str
    items: List[InventoryValuationItem]


class InventoryWipItem(BaseModel):
    model_config = DECIMAL_CONFIG

    type_id: int
    qty: Decimal


class InventoryWipResponse(BaseModel):
    model_config = DECIMAL_CONFIG

    owner_scope: str
    items: List[InventoryWipItem]


@router.get("/valuation")
def inventory_valuation(owner_scope: str = Query(...), type_id: List[int] | None = Query(default=None)):
    data = inventory_service.get_on_hand(owner_scope, type_id)
    items = [
        InventoryValuationItem(type_id=type_id, qty=vals["qty"], avg_cost=vals["avg_cost"])
        for type_id, vals in data.items()
    ]
    return InventoryValuationResponse(owner_scope=owner_scope, items=items)


@router.get("/wip")
def inventory_wip(owner_scope: str = Query(...)):
    data = inventory_service.get_wip(owner_scope)
    items = [InventoryWipItem(type_id=type_id, qty=qty) for type_id, qty in data.items()]
    return InventoryWipResponse(owner_scope=owner_scope, items=items)

