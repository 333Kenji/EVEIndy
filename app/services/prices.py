from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Sequence

import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings


@dataclass(frozen=True)
class Quote:
    type_id: int
    region_id: int
    bid: Decimal
    ask: Decimal
    mid: Decimal
    ts: datetime


def _engine():
    return sa.create_engine(Settings().database_url)


def latest_quotes(region_id: int, type_ids: Sequence[int]) -> list[Quote]:
    if not type_ids:
        return []
    sql = text(
        """
        with latest as (
            select distinct on (type_id, side)
                type_id, side, ts, best_px
            from orderbook_snapshots
            where region_id = :region_id and type_id = any(:type_ids)
            order by type_id, side, ts desc
        )
        select b.type_id as type_id,
               :region_id as region_id,
               b.best_px as bid,
               a.best_px as ask,
               (b.best_px + a.best_px)/2 as mid,
               greatest(b.ts, a.ts) as ts
        from latest b
        join latest a on a.type_id = b.type_id and a.side = 'ask'
        where b.side = 'bid'
        order by b.type_id
        """
    )
    # sqlalchemy passes arrays differently per dialect; for psycopg2 we can pass list
    params = {"region_id": region_id, "type_ids": list(type_ids)}
    out: list[Quote] = []
    with _engine().connect() as conn:
        for row in conn.execute(sql, params):
            out.append(
                Quote(
                    type_id=int(row.type_id),
                    region_id=int(region_id),
                    bid=Decimal(row.bid),
                    ask=Decimal(row.ask),
                    mid=Decimal(row.mid),
                    ts=row.ts,
                )
            )
    return out

