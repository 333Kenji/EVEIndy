"""Shared provider utilities and interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Mapping, Protocol

from pydantic import BaseModel, Field
from tenacity import Retrying, RetryError, stop_after_attempt, wait_random_exponential


class CircuitBreakerOpen(RuntimeError):
    """Raised when the provider circuit is open and calls should be skipped."""


@dataclass
class CircuitBreaker:
    max_failures: int = 3
    failure_count: int = 0

    def check(self) -> None:
        if self.failure_count >= self.max_failures:
            raise CircuitBreakerOpen("provider circuit open; skip call")

    def success(self) -> None:
        self.failure_count = 0

    def failure(self) -> None:
        self.failure_count += 1


class PriceQuote(BaseModel):
    type_id: int
    region_id: int
    bid: Decimal
    ask: Decimal
    mid: Decimal
    depth_qty_1pct: Decimal
    depth_qty_5pct: Decimal
    volatility: Decimal
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider: str


class PriceProvider(Protocol):
    """Protocol all price providers must satisfy."""

    def get(self, type_id: int, region_id: int) -> PriceQuote:
        ...


RetryCallable = Callable[[], PriceQuote]


def execute_with_retry(callable_: RetryCallable, max_attempts: int = 5) -> PriceQuote:
    retry = Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(min=1, max=5),
        reraise=True,
    )
    for attempt in retry:
        with attempt:
            return callable_()
    raise RuntimeError("Retry loop exhausted")


def parse_decimal(value: Any, *, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid decimal for field {field}") from exc
