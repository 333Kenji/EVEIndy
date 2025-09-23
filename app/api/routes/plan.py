from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/next-window")
def post_next_window(payload: dict[str, Any]):
    try:
        start = datetime.fromisoformat(payload["start"])  # noqa: F841 (placeholder)
        duration_hours = int(payload["duration_hours"])  # noqa: F841
        owner_scope = str(payload.get("owner_scope", "corp"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payload") from exc
    # Placeholder: return empty suggestions for now.
    return {"characters": [], "assumptions": {"owner_scope": owner_scope}}

