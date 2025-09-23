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


def list_systems(
    q: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[int] = None,
    region_id: Optional[int] = None,
    constellation_id: Optional[int] = None,
) -> Dict[str, Any]:
    key = f"systems:list:{q or ''}:{limit}:{cursor or 0}:{region_id or 0}:{constellation_id or 0}"
    cache = CacheClient(_redis())
    cached = cache._get_value(key)  # use internal to reuse envelope
    if cached and not cached.stale:
        return cached.value

    sql = text(
        """
        with systems as (
            select
                sys.id as system_id,
                sys.name as system_name,
                sys.parent_id as constellation_id,
                const.name as constellation_name,
                const.parent_id as region_id,
                region.name as region_name
            from universe_ids sys
            left join universe_ids const on const.id = sys.parent_id
            left join universe_ids region on region.id = const.parent_id
            where sys.kind = 'system'
        ),
        idx as (
            select system_id, activity, index_value from cost_indices
        )
        select
            s.system_id,
            s.system_name,
            s.constellation_id,
            s.constellation_name,
            s.region_id,
            s.region_name,
            i.activity,
            i.index_value
        from systems s
        left join idx i on i.system_id = s.system_id
        where (:q is null or lower(s.system_name) like :q)
          and (:cursor is null or s.system_id > :cursor)
          and (:region is null or s.region_id = :region)
          and (:constellation is null or s.constellation_id = :constellation)
        order by s.system_id
        limit :lim
        """
    )
    params = {
        "q": f"%{q.lower()}%" if q else None,
        "cursor": cursor,
        "lim": limit,
        "region": region_id,
        "constellation": constellation_id,
    }
    rows = []
    out: Dict[int, Dict[str, Any]] = {}
    with _engine().connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    for system_id, name, const_id, const_name, reg_id, reg_name, activity, index_value in rows:
        d = out.setdefault(
            int(system_id),
            {
                "system_id": int(system_id),
                "name": name,
                "constellation_id": int(const_id) if const_id is not None else None,
                "constellation_name": const_name,
                "region_id": int(reg_id) if reg_id is not None else None,
                "region_name": reg_name,
                "indices": {},
            },
        )
        if activity:
            d["indices"][activity] = float(index_value)
    systems = list(out.values())
    next_cursor = systems[-1]["system_id"] if systems else None
    payload = {"items": systems, "next_cursor": next_cursor, "has_more": len(rows) == limit}
    cache._set_value(key, payload, 3600)
    return payload

