"""Fuzzwork price provider implementation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx
from pydantic import BaseModel, Field

from .base import CircuitBreaker, PriceProvider, PriceQuote, execute_with_retry
from core.ratelimiter import RateLimiter


class _Edge(BaseModel):
    price: Decimal
    volume: Decimal


class _Depth(BaseModel):
    qty_1pct: Decimal = Field(alias="qty_1pct")
    qty_5pct: Decimal = Field(alias="qty_5pct")


class _Payload(BaseModel):
    buy: _Edge
    sell: _Edge
    generated: datetime
    depth: _Depth
    volatility: Decimal = Field(default=Decimal("0.1"))


class FuzzworkProvider(PriceProvider):
    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        breaker: CircuitBreaker | None = None,
        timeout: float = 10.0,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._breaker = breaker or CircuitBreaker()
        self._timeout = timeout
        self._rl = rate_limiter

    def get(self, type_id: int, region_id: int) -> PriceQuote:
        self._breaker.check()

        def _call() -> PriceQuote:
            if self._rl:
                self._rl.block_until_allowed("fuzzwork:/orders/type")
            response = self._client.get(
                f"{self._base_url}/orders/type/{type_id}/region/{region_id}",
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = _Payload.model_validate(response.json())
            ts = (
                payload.generated.replace(tzinfo=timezone.utc)
                if payload.generated.tzinfo is None
                else payload.generated.astimezone(timezone.utc)
            )
            bid = payload.buy.price
            ask = payload.sell.price
            mid = (bid + ask) / Decimal("2")
            return PriceQuote(
                type_id=type_id,
                region_id=region_id,
                bid=bid,
                ask=ask,
                mid=mid,
                depth_qty_1pct=payload.depth.qty_1pct,
                depth_qty_5pct=payload.depth.qty_5pct,
                volatility=payload.volatility,
                ts=ts,
                provider="fuzzwork",
            )

        try:
            quote = execute_with_retry(_call)
        except Exception:  # noqa: BLE001
            self._breaker.failure()
            raise
        else:
            self._breaker.success()
            return quote
