"""Provider rate limit factories based on Settings."""

from __future__ import annotations

import time
from typing import Callable

from core.ratelimiter import RateLimiter

# Simple registry for limiter instances by provider name
_REGISTRY: dict[str, RateLimiter] = {}


def build_limiter(capacity: float, refill_rate: float, now: Callable[[], float] | None = None) -> RateLimiter:
    return RateLimiter(capacity=capacity, refill_rate_per_sec=refill_rate, now=now or time.time)


def limiter_for_provider(provider: str, settings) -> RateLimiter:
    p = provider.lower()
    if p == "esi":
        lim = build_limiter(settings.esi_capacity, settings.esi_refill_rate)
        _REGISTRY.setdefault("esi", lim)
        return lim
    if p == "adam4eve":
        lim = build_limiter(settings.adam4eve_capacity, settings.adam4eve_refill_rate)
        _REGISTRY.setdefault("adam4eve", lim)
        return lim
    if p == "fuzzwork":
        lim = build_limiter(settings.fuzzwork_capacity, settings.fuzzwork_refill_rate)
        _REGISTRY.setdefault("fuzzwork", lim)
        return lim
    # Default conservative limiter
    lim = build_limiter(1.0, 0.1)
    _REGISTRY.setdefault(p, lim)
    return lim


def limiter_metrics() -> dict:
    out: dict[str, dict] = {}
    for name, lim in _REGISTRY.items():
        per_key = {}
        for key, b in lim.buckets.items():  # type: ignore[attr-defined]
            per_key[key] = {"allowed": b.allowed, "denied": b.denied, "delayed": b.delayed}
        out[name] = per_key
    return out
