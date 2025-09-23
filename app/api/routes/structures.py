from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query
from sqlalchemy import text

from app.db import get_engine


def _engine():
    """Return the shared engine (compatibility helper for tests)."""

    return get_engine()


router = APIRouter(prefix="/structures", tags=["structures"])
FALLBACK_RIGS = [
    {"rig_id": 1001, "name": "Manufacturing Material Efficiency I", "activity": "Manufacturing", "me_bonus": 0.02, "te_bonus": 0.0},
    {"rig_id": 1002, "name": "Manufacturing Time Efficiency I", "activity": "Manufacturing", "me_bonus": 0.0, "te_bonus": 0.02},
    {"rig_id": 1101, "name": "Reactions Material Efficiency I", "activity": "Reactions", "me_bonus": 0.02, "te_bonus": 0.0},
    {"rig_id": 1102, "name": "Reactions Time Efficiency I", "activity": "Reactions", "me_bonus": 0.0, "te_bonus": 0.02},
    {"rig_id": 1201, "name": "Refining Yield I", "activity": "Refining", "me_bonus": 0.0, "te_bonus": 0.0},
    {"rig_id": 1301, "name": "Science ME Research I", "activity": "Science", "me_bonus": 0.0, "te_bonus": 0.0},
]


@router.get("/rigs")
def list_rigs(activity: str | None = Query(default=None)) -> Dict[str, List[Dict[str, Any]]]:
    sql = text("select rig_id, name, activity, me_bonus, te_bonus from rigs")
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(sql).fetchall()
            rigs = [
                {
                    "rig_id": int(r[0]),
                    "name": r[1],
                    "activity": r[2],
                    "me_bonus": float(r[3]) if r[3] is not None else 0.0,
                    "te_bonus": float(r[4]) if r[4] is not None else 0.0,
                }
                for r in rows
            ]
    except Exception:
        rigs = FALLBACK_RIGS
    if activity:
        rigs = [r for r in rigs if str(r["activity"]).lower() == activity.lower()]
    return {"rigs": rigs}

