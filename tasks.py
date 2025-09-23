from __future__ import annotations

import os
from typing import List

from celery import shared_task

from app.providers.factory import make_price_provider
from utils.backfill_prices import insert_snapshot
from app.config import Settings
import sqlalchemy as sa


def _get_type_ids() -> List[int]:
    raw = os.getenv("PRICE_TYPE_IDS", "")
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


@shared_task(name="tasks.price_refresh")
def price_refresh() -> str:
    settings = Settings()
    provider_name = os.getenv("PRICE_PROVIDER", "adam4eve")
    region_id = int(os.getenv("REGION_ID", "10000002"))
    type_ids = _get_type_ids()
    if not type_ids:
        return "No TYPE_IDS configured; skipping"
    provider = make_price_provider(provider_name, settings)
    engine = sa.create_engine(settings.database_url)
    count = 0
    with engine.begin() as conn:
        for t in type_ids:
            q = provider.get(type_id=t, region_id=region_id)  # type: ignore[attr-defined]
            insert_snapshot(conn, region_id=region_id, type_id=t, side="bid", px=q.bid, depth1=q.depth_qty_1pct, depth5=q.depth_qty_5pct, vol=q.volatility, ts=q.ts)
            insert_snapshot(conn, region_id=region_id, type_id=t, side="ask", px=q.ask, depth1=q.depth_qty_1pct, depth5=q.depth_qty_5pct, vol=q.volatility, ts=q.ts)
            count += 2
            # Also store into market_snapshots for history charts
            mid = (q.bid + q.ask) / 2
            conn.execute(sa.text(
                """
                INSERT INTO market_snapshots(id, ts, region_id, type_id, bid, ask, mid, depth_qty_1pct, depth_qty_5pct)
                VALUES (gen_random_uuid(), :ts, :r, :t, :bid, :ask, :mid, :d1, :d5)
                """
            ), {"ts": q.ts, "r": region_id, "t": t, "bid": q.bid, "ask": q.ask, "mid": mid, "d1": q.depth_qty_1pct, "d5": q.depth_qty_5pct})
    return f"Inserted {count} snapshots"


@shared_task(name="tasks.indicators")
def indicators_recompute() -> str:
    # Placeholder: real implementation would aggregate distinct (type_id, region_id) and recompute indicators into cache.
    return "Indicators recompute scheduled"
