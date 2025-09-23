from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Optional

import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings


def _engine():
    return sa.create_engine(Settings().database_url)


def _to_decimal(value: object, *, default: Decimal | None = None) -> Decimal:
    if value is None:
        if default is not None:
            return default
        raise ValueError("Expected numeric value, received None")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_on_hand(owner_scope: str, type_ids: Optional[Iterable[int]] = None) -> Mapping[int, Dict[str, Decimal]]:
    """Return on-hand qty and rolling-average cost per type_id from `inventory`.

    Constitution policy: rolling-average (avg_cost) is updated only on acquisitions; consumption reduces qty only.
    """
    sql = text(
        """
        select type_id, qty_on_hand, avg_cost from inventory
        where owner_scope = :owner
        {filter}
        """.replace(
            "{filter}", "and type_id = any(:ids)" if type_ids else ""
        )
    )
    params = {"owner": owner_scope}
    if type_ids:
        params["ids"] = list(type_ids)
    out: Dict[int, Dict[str, Decimal]] = {}
    with _engine().connect() as conn:
        for t_id, qty, avg in conn.execute(sql, params):
            out[int(t_id)] = {
                "qty": _to_decimal(qty, default=Decimal("0")),
                "avg_cost": _to_decimal(avg, default=Decimal("0")),
            }
    return out


def get_wip(owner_scope: str) -> Mapping[int, Decimal]:
    """Sum outputs of queued/active jobs for WIP by product type.

    Uses `industry_jobs` runs * output_qty (default 1 if null), constrained to statuses queued/active.
    """
    sql = text(
        """
        select type_id, sum(coalesce(runs,0) * coalesce(output_qty,1)) as wip
        from industry_jobs
        where owner_scope = :owner and status in ('queued','active')
        group by type_id
        """
    )
    out: Dict[int, Decimal] = {}
    with _engine().connect() as conn:
        for t_id, w in conn.execute(sql, {"owner": owner_scope}):
            out[int(t_id)] = _to_decimal(w, default=Decimal("0"))
    return out

