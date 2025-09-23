from __future__ import annotations

from fastapi import APIRouter

from app.rate_limit import limiter_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def get_metrics():
    return {"rate_limiter": limiter_metrics()}

