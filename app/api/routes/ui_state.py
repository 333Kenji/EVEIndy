from __future__ import annotations

from fastapi import APIRouter, HTTPException
import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings

router = APIRouter(prefix="/state", tags=["ui"])


@router.get("/ui")
def get_ui_state(id: str = "default"):
    engine = sa.create_engine(Settings().database_url)
    row = None
    with engine.connect() as conn:
        row = conn.execute(text("select state from ui_state where id=:id"), {"id": id}).fetchone()
    return row[0] if row else {"panes": []}


@router.post("/ui")
def post_ui_state(payload: dict, id: str = "default"):
    engine = sa.create_engine(Settings().database_url)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO ui_state(id, state) VALUES (:id, :state)
            ON CONFLICT (id) DO UPDATE SET state=EXCLUDED.state, updated_at=timezone('utc', now())
        """), {"id": id, "state": payload})
    return {"ok": True}

