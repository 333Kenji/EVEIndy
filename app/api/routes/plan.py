from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.services import plan as plan_service
from indy_math.planner import PlanningError

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/next-window")
def post_next_window(payload: dict[str, Any]):
    try:
        return plan_service.schedule_window(payload)
    except PlanningError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/recommend")
def post_recommend(payload: dict[str, Any]):
    try:
        return plan_service.recommend(payload)
    except PlanningError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

