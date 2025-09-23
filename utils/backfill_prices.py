"""Backfill orderbook snapshots for selected type_ids and region.

Usage:
  IndyCalculator/bin/python utils/backfill_prices.py --provider adam4eve --region 10000002 --types 34,35,36
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings
from app.providers.factory import make_price_provider


def insert_snapshot(conn, *, region_id: int, type_id: int, side: str, px: Decimal, depth1: Decimal, depth5: Decimal, vol: Decimal, ts: datetime) -> None:
    conn.execute(
        text(
            """
            INSERT INTO orderbook_snapshots
            (id, ts, region_id, type_id, side, best_px, best_qty, depth_qty_1pct, depth_qty_5pct, stdev_pct)
            VALUES (gen_random_uuid(), :ts, :region_id, :type_id, :side, :best_px, 0, :d1, :d5, :stdev)
            ON CONFLICT (region_id, type_id, side, ts) DO NOTHING
            """
        ),
        {
            "ts": ts,
            "region_id": region_id,
            "type_id": type_id,
            "side": side,
            "best_px": px,
            "d1": depth1,
            "d5": depth5,
            "stdev": vol,
        },
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill price snapshots")
    ap.add_argument("--provider", required=True, choices=["adam4eve", "fuzzwork"]) 
    ap.add_argument("--region", type=int, required=True)
    ap.add_argument("--types", type=str, required=True, help="Comma-separated type IDs")
    args = ap.parse_args()

    types = [int(x) for x in args.types.split(",") if x.strip()]
    settings = Settings()
    provider = make_price_provider(args.provider, settings)
    engine = sa.create_engine(settings.database_url)
    with engine.begin() as conn:
        for t in types:
            q = provider.get(type_id=t, region_id=args.region)  # type: ignore[attr-defined]
            insert_snapshot(conn, region_id=args.region, type_id=t, side="bid", px=q.bid, depth1=q.depth_qty_1pct, depth5=q.depth_qty_5pct, vol=q.volatility, ts=q.ts)
            insert_snapshot(conn, region_id=args.region, type_id=t, side="ask", px=q.ask, depth1=q.depth_qty_1pct, depth5=q.depth_qty_5pct, vol=q.volatility, ts=q.ts)
    print("Backfill complete")


if __name__ == "__main__":
    main()

