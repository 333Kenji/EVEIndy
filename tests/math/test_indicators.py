from decimal import Decimal

import pytest

from indy_math.indicators import (
    BollingerBands,
    DepthPoint,
    DepthSummary,
    bollinger_bands,
    moving_average,
    shallow_depth_metrics,
    simple_volatility,
)


@pytest.fixture
def price_series() -> list[Decimal]:
    return [Decimal(str(value)) for value in [100, 102, 101, 103, 104]]


def test_moving_average(price_series: list[Decimal]) -> None:
    assert moving_average(price_series, 3) == Decimal("102.6667")


def test_simple_volatility(price_series: list[Decimal]) -> None:
    assert simple_volatility(price_series, 5) > Decimal("1.0000")


def test_bollinger_bands(price_series: list[Decimal]) -> None:
    bands = bollinger_bands(price_series, 5, Decimal("2"))
    assert isinstance(bands, BollingerBands)
    assert bands.upper > bands.middle > bands.lower


def test_shallow_depth_metrics() -> None:
    summary = shallow_depth_metrics(
        [
            DepthPoint(price=Decimal("100"), quantity=Decimal("5")),
            DepthPoint(price=Decimal("101"), quantity=Decimal("3")),
        ]
    )
    assert isinstance(summary, DepthSummary)
    assert summary.total_quantity == Decimal("8.0000")
    assert summary.volume_weighted_price == Decimal("100.3750")


def test_indicator_validation_errors(price_series: list[Decimal]) -> None:
    with pytest.raises(ValueError):
        moving_average(price_series[:2], 5)
    with pytest.raises(ValueError):
        shallow_depth_metrics([])
    with pytest.raises(ValueError):
        simple_volatility(price_series[:2], 5)
