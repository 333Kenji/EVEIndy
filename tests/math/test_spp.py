from datetime import datetime
from decimal import Decimal

import pytest

from indy_math.spp import (
    DepthForecast,
    PricePolicy,
    recommend_batch_size,
    spp_lead_time_aware,
)


def deterministic_forecast(_: datetime) -> DepthForecast:
    return DepthForecast(
        expected_daily_demand=Decimal("10"),
        expected_new_listings=Decimal("2"),
    )


def test_spp_zero_depth_high_probability() -> None:
    policy = PricePolicy(listing_markup=Decimal("0.02"), minimum_spread=Decimal("0.03"))
    result = spp_lead_time_aware(
        depth_ahead_now=0,
        dv_forecast_fn=deterministic_forecast,
        lead_time_days=Decimal("1"),
        horizon_days=Decimal("3"),
        price_best_now=Decimal("100"),
        drift_rate=Decimal("0"),
        price_policy=policy,
        spread_at_list=Decimal("0.03"),
        vol_stdev_at_list=Decimal("0.05"),
        batch_options=[1, 2, 3],
        clock=lambda: datetime(2024, 1, 1, 0, 0, 0),
    )
    assert result.spp >= Decimal("0.8000")
    assert result.recommended_batch == 3
    assert result.diagnostics.queue_at_listing == Decimal("0.0000")


def test_spp_depth_reduces_probability() -> None:
    policy = PricePolicy(listing_markup=Decimal("0.02"), minimum_spread=Decimal("0.03"))
    shallow = spp_lead_time_aware(
        depth_ahead_now=2,
        dv_forecast_fn=deterministic_forecast,
        lead_time_days=Decimal("1"),
        horizon_days=Decimal("2"),
        price_best_now=Decimal("100"),
        drift_rate=Decimal("0.01"),
        price_policy=policy,
        spread_at_list=Decimal("0.04"),
        vol_stdev_at_list=Decimal("0.10"),
        batch_options=[1, 2, 3],
        clock=lambda: datetime(2024, 1, 1, 0, 0, 0),
    )
    deep = spp_lead_time_aware(
        depth_ahead_now=20,
        dv_forecast_fn=deterministic_forecast,
        lead_time_days=Decimal("1"),
        horizon_days=Decimal("2"),
        price_best_now=Decimal("100"),
        drift_rate=Decimal("0.01"),
        price_policy=policy,
        spread_at_list=Decimal("0.04"),
        vol_stdev_at_list=Decimal("0.10"),
        batch_options=[1, 2, 3],
        clock=lambda: datetime(2024, 1, 1, 0, 0, 0),
    )
    assert deep.spp < shallow.spp


def test_recommend_batch_size_respects_expected_fills() -> None:
    spp_value = Decimal("0.5")
    demand = Decimal("10")
    assert recommend_batch_size([1, 5, 12], spp_value, demand) == 12


def test_spp_deterministic_results() -> None:
    policy = PricePolicy(listing_markup=Decimal("0.02"), minimum_spread=Decimal("0.03"))
    calc = lambda depth: spp_lead_time_aware(
        depth_ahead_now=depth,
        dv_forecast_fn=deterministic_forecast,
        lead_time_days=Decimal("1"),
        horizon_days=Decimal("2"),
        price_best_now=Decimal("100"),
        drift_rate=Decimal("0"),
        price_policy=policy,
        spread_at_list=Decimal("0.03"),
        vol_stdev_at_list=Decimal("0.05"),
        batch_options=[1, 2, 3],
        clock=lambda: datetime(2024, 1, 1, 0, 0, 0),
    )
    assert calc(5) == calc(5)


def test_recommend_batch_requires_options() -> None:
    with pytest.raises(ValueError):
        recommend_batch_size([], Decimal("0.5"), Decimal("5"))
