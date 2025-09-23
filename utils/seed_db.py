"""Seed the database with public ESI cost indices and price snapshots.

Usage examples:
  IndyCalculator/bin/python utils/seed_db.py --provider adam4eve --region 10000002 --types 34,35,36 --cost-indices
  IndyCalculator/bin/python utils/seed_db.py --provider fuzzwork --region 10000002 --types 34,35 --dry-run

Notes:
- Uses public endpoints only; no ESI token required for cost indices.
- Respects rate limits via provider limiter defaults.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Sequence

import httpx
import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings
from app.rate_limit import limiter_for_provider
from app.providers.adam4eve import Adam4EVEProvider
from app.providers.fuzzwork import FuzzworkProvider
from app.providers.esi import ESIClient


def as_list(csv: str | None) -> list[int]:
    if not csv:
        return []
    return [int(x.strip()) for x in csv.split(",") if x.strip()]


def upsert_cost_indices(conn, indices: Sequence[dict]) -> None:
    for row in indices:
        conn.execute(
            text(
                """
                INSERT INTO cost_indices (system_id, activity, index_value)
                VALUES (:system_id, :activity, :index_value)
                ON CONFLICT (system_id, activity)
                DO UPDATE SET index_value = EXCLUDED.index_value
                """
            ),
            row,
        )


def insert_orderbook_snapshot(conn, snapshot: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO orderbook_snapshots
            (id, ts, region_id, type_id, side, best_px, best_qty, depth_qty_1pct, depth_qty_5pct, stdev_pct)
            VALUES (gen_random_uuid(), :ts, :region_id, :type_id, :side, :best_px, :best_qty, :d1, :d5, :stdev)
            ON CONFLICT (region_id, type_id, side, ts) DO NOTHING
            """
        ),
        snapshot,
    )


def seed_prices(conn, provider: str, region_id: int, type_ids: Sequence[int], dry_run: bool = False) -> None:
    settings = Settings()
    limiter = limiter_for_provider(provider, settings)
    client = httpx.Client(timeout=10.0)
    if provider == "adam4eve":
        base_url = settings.__dict__.get("adam4eve_base_url", "https://api.adam4eve.eu")
        p = Adam4EVEProvider(client=client, base_url=base_url, rate_limiter=limiter)
    elif provider == "fuzzwork":
        base_url = settings.__dict__.get("fuzzwork_base_url", "https://market.fuzzwork.co.uk")
        p = FuzzworkProvider(client=client, base_url=base_url, rate_limiter=limiter)
    else:
        raise SystemExit(f"Unknown provider: {provider}")

    for type_id in type_ids:
        quote = p.get(type_id=type_id, region_id=region_id)
        bid = {
            "ts": quote.ts,
            "region_id": quote.region_id,
            "type_id": quote.type_id,
            "side": "bid",
            "best_px": quote.bid,
            "best_qty": Decimal("0"),
            "d1": quote.depth_qty_1pct,
            "d5": quote.depth_qty_5pct,
            "stdev": quote.volatility,
        }
        ask = {**bid, "side": "ask", "best_px": quote.ask}
        if dry_run:
            print(f"DRY-RUN: would insert snapshots for {type_id}")
        else:
            insert_orderbook_snapshot(conn, bid)
            insert_orderbook_snapshot(conn, ask)


def seed_cost_indices(conn, dry_run: bool = False) -> None:
    settings = Settings()
    client = httpx.Client(timeout=15.0)
    esi = ESIClient(client=client, base_url="https://esi.evetech.net/latest", token_provider=None, rate_limiter=limiter_for_provider("esi", settings))
    # GET /industry/systems (public) returns list of systems with cost_indices
    data, _ = esi._request("/industry/systems/")  # use internal helper to avoid model mapping here
    rows: list[dict] = []
    for sys in data:
        sid = int(sys["system_id"])  # type: ignore[index]
        for idx in sys.get("cost_indices", []):  # type: ignore[index]
            rows.append({
                "system_id": sid,
                "activity": str(idx["activity"]),
                "index_value": Decimal(str(idx["cost_index"]))
            })
    if dry_run:
        print(f"DRY-RUN: would upsert {len(rows)} cost indices")
    else:
        upsert_cost_indices(conn, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database with public data")
    parser.add_argument("--provider", choices=["adam4eve", "fuzzwork"], help="Price provider")
    parser.add_argument("--region", type=int, default=10000002, help="Region id (default Jita: 10000002)")
    parser.add_argument("--types", type=str, default="34,35,36", help="Comma-separated type IDs to seed")
    parser.add_argument("--cost-indices", action="store_true", help="Also load ESI system cost indices")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = Settings()
    engine = sa.create_engine(settings.database_url)
    with engine.begin() as conn:
        if args.cost_indices:
            seed_cost_indices(conn, dry_run=args.dry_run)
        if args.provider:
            seed_prices(
                conn,
                provider=args.provider,
                region_id=args.region,
                type_ids=as_list(args.types),
                dry_run=args.dry_run,
            )
    print("Seeding complete")


if __name__ == "__main__":
    main()

