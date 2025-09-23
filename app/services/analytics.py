from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

import redis
import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings
from app.cache import CacheClient, CachePolicy
from app.math import BollingerBands, DepthPoint, DepthSummary, bollinger_bands, moving_average, shallow_depth_metrics, simple_volatility, spp_lead_time_aware, PricePolicy


@dataclass(frozen=True)
class IndicatorResult:
    ma: Decimal
    bollinger: BollingerBands
    volatility: Decimal
    depth: DepthSummary


def _get_engine(settings: Settings) -> sa.Engine:
    return sa.create_engine(settings.database_url)


def _get_redis(settings: Settings) -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def _fetch_price_series(conn, region_id: int, type_id: int, limit: int) -> Sequence[Decimal]:
    rows = conn.execute(
        text(
            """
            SELECT best_px
            FROM orderbook_snapshots
            WHERE region_id = :r AND type_id = :t AND side = 'ask'
            ORDER BY ts DESC
            LIMIT :lim
            """
        ),
        {"r": region_id, "t": type_id, "lim": limit},
    ).fetchall()
    # reverse chronological to chronological
    return [Decimal(str(r[0])) for r in reversed(rows)]


def indicators(type_id: int, region_id: int, window: int) -> IndicatorResult:
    settings = Settings()
    rc = _get_redis(settings)
    cache = CacheClient(rc)
    # Try cache first
    cached = cache.get_indicator(region_id, type_id)
    if cached and not cached.stale:
        v = cached.value
        return IndicatorResult(
            ma=Decimal(str(v["ma"])),
            bollinger=BollingerBands(
                middle=Decimal(str(v["bollinger"]["middle"])),
                upper=Decimal(str(v["bollinger"]["upper"])),
                lower=Decimal(str(v["bollinger"]["lower"])),
            ),
            volatility=Decimal(str(v["volatility"])),
            depth=DepthSummary(
                total_quantity=Decimal(str(v["depth"]["total_quantity"])),
                volume_weighted_price=Decimal(str(v["depth"]["volume_weighted_price"])),
            ),
        )

    try:
        engine = _get_engine(settings)
        with engine.connect() as conn:
            series = _fetch_price_series(conn, region_id, type_id, max(5, window))
    except Exception:
        series = []

    if not series:
        # Fallback: synthetic
        series = [Decimal("100"), Decimal("101"), Decimal("102"), Decimal("101"), Decimal("103")]
    w = min(window, len(series))
    ma = moving_average(series, w)
    vol = simple_volatility(series, w)
    bands = bollinger_bands(series, w, k=Decimal("2"))
    depth = shallow_depth_metrics(
        [DepthPoint(price=series[-1], quantity=Decimal("10")), DepthPoint(price=series[-1] * Decimal("1.005"), quantity=Decimal("5"))]
    )
    # Write to cache
    cache.set_indicator(
        region_id,
        type_id,
        {
            "ma": str(ma),
            "bollinger": {"middle": str(bands.middle), "upper": str(bands.upper), "lower": str(bands.lower)},
            "volatility": str(vol),
            "depth": {
                "total_quantity": str(depth.total_quantity),
                "volume_weighted_price": str(depth.volume_weighted_price),
            },
        },
    )
    return IndicatorResult(ma=ma, bollinger=bands, volatility=vol, depth=depth)


def spp_plus(
    type_id: int,
    region_id: int,
    lead_time_days: Decimal,
    horizon_days: Decimal,
) -> dict:
    settings = Settings()
    rc = _get_redis(settings)
    cache = CacheClient(rc)
    # Key params hash (simple)
    key_hash = f"{type_id}:{region_id}:{lead_time_days}:{horizon_days}"
    cached = cache.get_spp(type_id, region_id, key_hash)
    if cached and not cached.stale:
        return cached.value  # already JSON-serializable strings

    series: list[Decimal] = []
    try:
        engine = _get_engine(settings)
        with engine.connect() as conn:
            series = _fetch_price_series(conn, region_id, type_id, 14)
    except Exception:
        series = []
    if not series:
        series = [Decimal("100"), Decimal("101"), Decimal("102"), Decimal("101"), Decimal("103")]

    def dv_forecast_fn(_now):
        from indy_math.spp import DepthForecast

        # crude deterministic placeholders
        return DepthForecast(expected_daily_demand=Decimal("10"), expected_new_listings=Decimal("2"))

    result = spp_lead_time_aware(
        depth_ahead_now=0,
        dv_forecast_fn=dv_forecast_fn,
        lead_time_days=lead_time_days,
        horizon_days=horizon_days,
        price_best_now=series[-1],
        drift_rate=Decimal("0"),
        price_policy=PricePolicy(listing_markup=Decimal("0.02"), minimum_spread=Decimal("0.03")),
        spread_at_list=Decimal("0.03"),
        vol_stdev_at_list=Decimal("0.05"),
        batch_options=[1, 2, 3],
    )
    out = {"spp": str(result.spp), "recommended_batch": result.recommended_batch, "diagnostics": result.diagnostics.__dict__}
    cache.set_spp(type_id, region_id, key_hash, out)
    return out
