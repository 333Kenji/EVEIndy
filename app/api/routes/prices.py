from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.services import prices as prices_service
from sqlalchemy import text
import sqlalchemy as sa
from app.config import Settings

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/quotes")
def post_quotes(payload: dict[str, Any]):
    try:
        region_id = int(payload["region_id"])  # required
        type_ids = [int(x) for x in payload.get("type_ids", [])]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payload") from exc

    quotes = prices_service.latest_quotes(region_id=region_id, type_ids=type_ids)
    return {
        "quotes": [
            {
                "type_id": q.type_id,
                "region_id": q.region_id,
                "bid": str(q.bid),
                "ask": str(q.ask),
                "mid": str(q.mid),
                "ts": q.ts.isoformat(),
            }
            for q in quotes
        ]
    }


@router.get("/history")
def get_history(type_id: int, region_id: int, days: int = 7):
    engine = sa.create_engine(Settings().database_url)
    sql = text(
        """
        with latest as (
            select ts, type_id, region_id,
                max(case when side='bid' then best_px end) over (partition by ts,type_id,region_id) as bid,
                max(case when side='ask' then best_px end) over (partition by ts,type_id,region_id) as ask
            from orderbook_snapshots
            where type_id=:t and region_id=:r and ts >= now() - (:d || ' days')::interval
        )
        select distinct on (ts) ts, coalesce(bid,0) as bid, coalesce(ask,0) as ask,
            case when bid is not null and ask is not null then (bid+ask)/2 else null end as mid
        from latest
        order by ts
        """
    )
    rows = []
    with engine.connect() as conn:
        rows = conn.execute(sql, {"t": type_id, "r": region_id, "d": days}).fetchall()
    return {
        "points": [
            {"ts": r[0].isoformat(), "bid": str(r[1]), "ask": str(r[2]), "mid": str(r[3]) if r[3] is not None else None}
            for r in rows
        ]
    }
