from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query

from app.services import market as market_service
from app.config import Settings

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/groups")
def get_groups(tech_level: int | None = Query(default=None)):
    groups = market_service.list_ship_groups()
    if tech_level is not None:
        groups = [g for g in groups if not g.tech_levels or tech_level in g.tech_levels]
    return {
        "items": [
            {
                "group_id": g.group_id,
                "label": g.label,
                "sample_names": g.sample_names,
                "tech_levels": g.tech_levels,
                "market_group_ids": g.market_group_ids,
                "type_count": g.type_count,
            }
            for g in groups
        ]
    }


@router.get("/regions")
def get_regions():
    try:
        default_region = int(getattr(Settings(), "default_region_id", 10000002))
    except (TypeError, ValueError):
        default_region = 10000002
    regions = market_service.list_regions()
    for r in regions:
        r["is_default"] = default_region is not None and r["region_id"] == default_region
    return {"items": regions}


@router.get("/ships")
def get_ships(
    tech_level: int | None = Query(default=None),
    group_id: List[int] | None = Query(default=None),
    q: str | None = Query(default=None, min_length=2),
    limit: int = Query(default=25, ge=1, le=100),
):
    ships = market_service.list_ships(
        tech_level=tech_level,
        group_ids=group_id,
        search=q,
        limit=limit,
    )
    return {
        "items": [
            {
                "type_id": s.type_id,
                "name": s.name,
                "group_id": s.group_id,
                "market_group_id": s.market_group_id,
                "tech_level": s.tech_level,
            }
            for s in ships
        ]
    }
