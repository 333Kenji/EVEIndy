"""Market indicator utilities used by the math core."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean as stat_mean
from typing import Sequence

ZERO = Decimal("0")


@dataclass(frozen=True)
class BollingerBands:
    middle: Decimal
    upper: Decimal
    lower: Decimal


@dataclass(frozen=True)
class DepthPoint:
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True)
class DepthSummary:
    total_quantity: Decimal
    volume_weighted_price: Decimal


def _to_decimal_sequence(series: Sequence[float | Decimal]) -> list[Decimal]:
    if len(series) == 0:
        raise ValueError("series must not be empty")
    return [Decimal(str(value)) if not isinstance(value, Decimal) else value for value in series]


def moving_average(series: Sequence[float | Decimal], window: int) -> Decimal:
    if window <= 0:
        raise ValueError("window must be greater than zero")
    values = _to_decimal_sequence(series)
    if len(values) < window:
        raise ValueError("series length must be at least window size")
    window_slice = values[-window:]
    avg = sum(window_slice) / Decimal(window)
    return avg.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def simple_volatility(series: Sequence[float | Decimal], window: int) -> Decimal:
    if window <= 1:
        raise ValueError("window must be greater than one")
    values = _to_decimal_sequence(series)
    if len(values) < window:
        raise ValueError("series length must be at least window size")
    window_slice = values[-window:]
    mean_value = sum(window_slice) / Decimal(window)
    variance = sum((value - mean_value) ** 2 for value in window_slice) / Decimal(window)
    return variance.sqrt().quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def bollinger_bands(series: Sequence[float | Decimal], window: int, k: Decimal) -> BollingerBands:
    if k <= ZERO:
        raise ValueError("k must be greater than zero")
    middle = moving_average(series, window)
    std_dev = simple_volatility(series, window)
    upper = (middle + (std_dev * k)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    lower = (middle - (std_dev * k)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return BollingerBands(middle=middle, upper=upper, lower=lower)


def shallow_depth_metrics(points: Sequence[DepthPoint]) -> DepthSummary:
    if not points:
        raise ValueError("points must contain at least one depth entry")
    total_qty = sum(point.quantity for point in points)
    if total_qty <= ZERO:
        raise ValueError("total quantity must be positive")
    weighted_price = sum(point.price * point.quantity for point in points) / total_qty
    return DepthSummary(
        total_quantity=total_qty.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        volume_weighted_price=weighted_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
    )
