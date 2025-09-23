from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_settings
from app.services.analytics import indicators as svc_indicators, spp_plus as svc_spp_plus

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/indicators")
def get_indicators(
    type_id: int = Query(...),
    region_id: int = Query(...),
    window: int = Query(5, ge=2, le=365),
):
    res = svc_indicators(type_id=type_id, region_id=region_id, window=window)
    return {"ma": res.ma, "bollinger": res.bollinger.__dict__, "volatility": res.volatility, "depth": res.depth.__dict__}


@router.post("/spp_plus")
def post_spp_plus(payload: dict[str, Any]):
    try:
        type_id = int(payload["type_id"])  # noqa: F841  # reserved for future use
        region_id = int(payload["region_id"])  # noqa: F841
        lead = Decimal(str(payload["lead_time_days"]))
        horizon = Decimal(str(payload["horizon_days"]))
        batch_options = [int(x) for x in payload.get("batch_options", [1, 2, 3])]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payload") from exc
    result = svc_spp_plus(
        type_id=type_id,
        region_id=region_id,
        lead_time_days=lead,
        horizon_days=horizon,
        batch_options=batch_options,
    )
    return result
