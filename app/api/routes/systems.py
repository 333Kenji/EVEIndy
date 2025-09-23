from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.systems import list_systems

router = APIRouter(prefix="/systems", tags=["systems"])


@router.get("")
def systems_index(q: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=200), cursor: int | None = Query(default=None)):
    return list_systems(q=q, limit=limit, cursor=cursor)

