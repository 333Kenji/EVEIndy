from __future__ import annotations

from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy import text

from app.cache import CacheClient
from app.config import Settings
import redis


def _engine():
    return sa.create_engine(Settings().database_url)


def _redis():
    return redis.from_url(Settings().redis_url, decode_responses=True)


def list_systems(q: Optional[str] = None, limit: int = 50, cursor: Optional[int] = None) -> Dict[str, Any]:
    key = f"systems:list:{q or ''}:{limit}:{cursor or 0}"
    cache = CacheClient(_redis())
    cached = cache._get_value(key)  # use internal to reuse envelope
    if cached and not cached.stale:
        return cached.value

    sql = text(
        """
        with systems as (
            select id as system_id, name from universe_ids where kind='system'
        ),
        idx as (
            select system_id, activity, index_value from cost_indices
        )
        select s.system_id, s.name, i.activity, i.index_value
        from systems s
        left join idx i on i.system_id = s.system_id
        where (:q is null or lower(s.name) like :q)
        and (:cursor is null or s.system_id > :cursor)
        order by s.system_id
        limit :lim
        """
    )
    rows = []
    out: Dict[int, Dict[str, Any]] = {}
    with _engine().connect() as conn:
        rows = conn.execute(sql, {"q": f"%{q.lower()}%" if q else None, "cursor": cursor, "lim": limit}).fetchall()
    for system_id, name, activity, index_value in rows:
        d = out.setdefault(int(system_id), {"system_id": int(system_id), "name": name, "indices": {}})
        if activity:
            d["indices"][activity] = float(index_value)
    systems = list(out.values())
    next_cursor = systems[-1]["system_id"] if systems else None
    payload = {"items": systems, "next_cursor": next_cursor}
    cache._set_value(key, payload, 3600)
    return payload

