"""Lead-time aware sell probability scoring (SPP⁺)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Mapping, Sequence

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True)
class DepthForecast:
    expected_daily_demand: Decimal
    expected_new_listings: Decimal


@dataclass(frozen=True)
class PricePolicy:
    listing_markup: Decimal
    minimum_spread: Decimal


@dataclass(frozen=True)
class SPPDiagnostics:
    queue_at_listing: Decimal
    demand_over_horizon: Decimal
    drift_adjustment: Decimal
    spread_adjustment: Decimal
    volatility_adjustment: Decimal


@dataclass(frozen=True)
class SPPResult:
    spp: Decimal
    recommended_batch: int
    diagnostics: SPPDiagnostics


BatchOptions = Sequence[int]
ForecastFunc = Callable[[datetime], DepthForecast]


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _clamp(value: Decimal, lower: Decimal = ZERO, upper: Decimal = ONE) -> Decimal:
    return max(lower, min(value, upper))


def spp_lead_time_aware(
    depth_ahead_now: int,
    dv_forecast_fn: ForecastFunc,
    lead_time_days: Decimal,
    horizon_days: Decimal,
    price_best_now: Decimal,
    drift_rate: Decimal,
    price_policy: PricePolicy,
    spread_at_list: Decimal,
    vol_stdev_at_list: Decimal,
    batch_options: BatchOptions,
    clock: Callable[[], datetime] | None = None,
) -> SPPResult:
    """Project queue depth and compute sell probability plus batch recommendation."""

    now = clock() if clock else datetime.utcnow()
    forecast = dv_forecast_fn(now + timedelta(days=float(lead_time_days)))

    depth_now = Decimal(depth_ahead_now)
    demand_until_listing = forecast.expected_daily_demand * lead_time_days
    projected_new_listings = forecast.expected_new_listings * lead_time_days
    queue_at_listing = depth_now + projected_new_listings - demand_until_listing
    if queue_at_listing < ZERO:
        queue_at_listing = ZERO

    demand_over_horizon = forecast.expected_daily_demand * horizon_days
    if demand_over_horizon <= ZERO:
        base_probability = ONE
    else:
        base_probability = demand_over_horizon / (demand_over_horizon + queue_at_listing)

    drift_adjustment = ONE + (drift_rate * horizon_days)
    if drift_adjustment < Decimal("0.1"):
        drift_adjustment = Decimal("0.1")

    spread_delta = spread_at_list - price_policy.minimum_spread
    spread_adjustment = _clamp(ONE - (spread_delta * Decimal("0.5")), Decimal("0.1"), ONE)
    if spread_adjustment > ONE:
        spread_adjustment = ONE

    volatility_adjustment = _clamp(ONE - (vol_stdev_at_list * Decimal("0.3")), Decimal("0.2"), ONE)

    spp_value = _clamp(base_probability * drift_adjustment * spread_adjustment * volatility_adjustment)
    spp_value = _quantize(spp_value)

    batch = recommend_batch_size(batch_options, spp_value, demand_over_horizon)

    diagnostics = SPPDiagnostics(
        queue_at_listing=_quantize(queue_at_listing),
        demand_over_horizon=_quantize(demand_over_horizon),
        drift_adjustment=_quantize(drift_adjustment),
        spread_adjustment=_quantize(spread_adjustment),
        volatility_adjustment=_quantize(volatility_adjustment),
    )

    return SPPResult(spp=spp_value, recommended_batch=batch, diagnostics=diagnostics)


def recommend_batch_size(
    batch_options: BatchOptions,
    spp_value: Decimal,
    demand_over_horizon: Decimal,
) -> int:
    if not batch_options:
        raise ValueError("batch_options must contain at least one value")
    best_batch = batch_options[0]
    best_score = ZERO
    for option in batch_options:
        option_qty = Decimal(option)
        expected_fills = min(option_qty, demand_over_horizon) * spp_value
        if expected_fills > best_score:
            best_score = expected_fills
            best_batch = option
    return best_batch
