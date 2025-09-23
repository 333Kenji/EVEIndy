from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings


@dataclass(frozen=True)
class ShipGroup:
    group_id: int
    sample_names: List[str]
    tech_levels: List[int]
    market_group_ids: List[int]
    label: str
    type_count: int


@dataclass(frozen=True)
class ShipRecord:
    type_id: int
    name: str
    group_id: Optional[int]
    market_group_id: Optional[int]
    tech_level: Optional[int]


def _engine() -> sa.Engine:
    return sa.create_engine(Settings().database_url)


def _tech_level_from_meta(meta: Dict[str, Any] | None, name: str) -> Optional[int]:
    if not meta:
        return 2 if " ii" in name.lower() else 1
    for key in ("metaGroupID", "metaGroupId", "meta_group_id"):
        val = meta.get(key) if isinstance(meta, dict) else None
        if val is None:
            continue
        try:
            iv = int(val)
        except (TypeError, ValueError):
            continue
        if iv in {1, 2, 3, 4, 5, 6, 7, 8, 9}:
            if iv == 1:
                return 1
            if iv == 2:
                return 2
            # Treat other meta groups as tech level 1 for filtering unless explicitly handled
            return 1
    low = name.lower()
    if " ii" in low or low.endswith(" ii") or low.endswith(" mark ii"):
        return 2
    return 1


def _market_group_from_meta(meta: Dict[str, Any] | None) -> Optional[int]:
    if not meta or not isinstance(meta, dict):
        return None
    for key in ("marketGroupID", "marketGroupId", "market_group_id"):
        val = meta.get(key)
        if val is None:
            continue
        try:
            return int(val)
        except (TypeError, ValueError):
            continue
    return None


def _group_label(group_id: int, metas: Iterable[Dict[str, Any] | None], sample_names: List[str]) -> str:
    for meta in metas:
        if not meta or not isinstance(meta, dict):
            continue
        for key in ("groupName", "marketGroupName", "metaGroupName"):
            val = meta.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    if sample_names:
        preview = ", ".join(sample_names[:3])
        return f"Group {group_id} ({preview})"
    return f"Group {group_id}"


def list_ship_groups() -> List[ShipGroup]:
    sql = text(
        """
        SELECT type_id, name, group_id, meta
        FROM type_ids
        WHERE category_id = 6
        ORDER BY name
        """
    )
    with _engine().connect() as conn:
        rows = conn.execute(sql).fetchall()
    grouped: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
        "metas": [],
        "sample_names": [],
        "tech_levels": set(),
        "market_group_ids": set(),
        "count": 0,
    })
    for row in rows:
        type_id = int(row[0])
        name = str(row[1])
        group_id = row[2]
        meta = row[3] or {}
        if group_id is None:
            # Skip ungrouped entries
            continue
        bucket = grouped[group_id]
        bucket["count"] += 1
        if len(bucket["sample_names"]) < 4:
            bucket["sample_names"].append(name)
        bucket["metas"].append(meta)
        tl = _tech_level_from_meta(meta, name)
        if tl:
            bucket["tech_levels"].add(tl)
        mg = _market_group_from_meta(meta)
        if mg is not None:
            bucket["market_group_ids"].add(mg)
    result: List[ShipGroup] = []
    for group_id, info in grouped.items():
        label = _group_label(group_id, info["metas"], info["sample_names"])
        result.append(
            ShipGroup(
                group_id=group_id,
                sample_names=info["sample_names"],
                tech_levels=sorted(info["tech_levels"]),
                market_group_ids=sorted(info["market_group_ids"]),
                label=label,
                type_count=info["count"],
            )
        )
    result.sort(key=lambda g: g.label.lower())
    return result


def list_regions() -> List[Dict[str, Any]]:
    sql = text(
        """
        SELECT id, name
        FROM universe_ids
        WHERE kind = 'region'
        ORDER BY name
        """
    )
    with _engine().connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [{"region_id": int(r[0]), "name": r[1] or "Unknown"} for r in rows]


def list_ships(
    *,
    tech_level: Optional[int] = None,
    group_ids: Optional[Iterable[int]] = None,
    search: Optional[str] = None,
    limit: int = 50,
) -> List[ShipRecord]:
    sql = text(
        """
        SELECT type_id, name, group_id, meta
        FROM type_ids
        WHERE category_id = 6
        ORDER BY name
        """
    )
    with _engine().connect() as conn:
        rows = conn.execute(sql).fetchall()
    allowed_groups = {int(g) for g in group_ids or []}
    normalized_query = search.lower() if search else None
    output: List[ShipRecord] = []
    for row in rows:
        type_id = int(row[0])
        name = str(row[1])
        group_id = row[2]
        meta = row[3] or {}
        if normalized_query and normalized_query not in name.lower():
            continue
        if allowed_groups and (group_id not in allowed_groups):
            continue
        tl = _tech_level_from_meta(meta, name)
        if tech_level is not None and tl is not None and tl != tech_level:
            continue
        mg = _market_group_from_meta(meta)
        output.append(
            ShipRecord(
                type_id=type_id,
                name=name,
                group_id=group_id,
                market_group_id=mg,
                tech_level=tl,
            )
        )
        if limit and len(output) >= limit:
            break
    return output
