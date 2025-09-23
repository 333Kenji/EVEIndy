from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db import get_engine

router = APIRouter(prefix="/state", tags=["ui"])


@router.get("/ui")
def get_ui_state(id: str = "default"):
    row = None
    with get_engine().connect() as conn:
        row = conn.execute(text("select state from ui_state where id=:id"), {"id": id}).fetchone()
    return row[0] if row else {"panes": []}


@router.post("/ui")
def post_ui_state(payload: dict, id: str = "default"):
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO ui_state(id, state) VALUES (:id, :state)
            ON CONFLICT (id) DO UPDATE SET state=EXCLUDED.state, updated_at=timezone('utc', now())
        """), {"id": id, "state": payload})
    return {"ok": True}

