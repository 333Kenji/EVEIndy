"""Token-bucket rate limiter with metrics and pluggable clock/sleep.

Usage:
    rl = RateLimiter(capacity=10, refill_rate_per_sec=1.0)
    rl.register_key("esi:/industry/jobs")
    rl.block_until_allowed("esi:/industry/jobs")

Keep pure behavior by injecting time providers in tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import sleep as _sleep
from typing import Callable, Dict


NowFunc = Callable[[], float]
SleepFunc = Callable[[float], None]


@dataclass
class Bucket:
    capacity: float
    tokens: float
    refill_rate_per_sec: float
    last_refill_ts: float
    # Metrics
    allowed: int = 0
    denied: int = 0
    delayed: int = 0

    def refill(self, now_ts: float) -> None:
        if now_ts <= self.last_refill_ts:
            return
        delta = now_ts - self.last_refill_ts
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate_per_sec)
        self.last_refill_ts = now_ts


@dataclass
class RateLimiter:
    capacity: float
    refill_rate_per_sec: float
    now: NowFunc
    sleep: SleepFunc = _sleep
    buckets: Dict[str, Bucket] = field(default_factory=dict)

    def register_key(self, key: str) -> None:
        ts = self.now()
        if key not in self.buckets:
            self.buckets[key] = Bucket(
                capacity=self.capacity,
                tokens=self.capacity,
                refill_rate_per_sec=self.refill_rate_per_sec,
                last_refill_ts=ts,
            )

    def try_acquire(self, key: str) -> bool:
        self.register_key(key)
        bucket = self.buckets[key]
        bucket.refill(self.now())
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            bucket.allowed += 1
            return True
        bucket.denied += 1
        return False

    def block_until_allowed(self, key: str) -> None:
        self.register_key(key)
        bucket = self.buckets[key]
        while True:
            bucket.refill(self.now())
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                bucket.allowed += 1
                return
            needed = 1.0 - bucket.tokens
            # seconds = tokens_needed / refill_rate
            wait_s = max(0.0, needed / bucket.refill_rate_per_sec)
            bucket.delayed += 1
            self.sleep(wait_s)

    def metrics(self, key: str) -> dict:
        b = self.buckets.get(key)
        if not b:
            return {"allowed": 0, "denied": 0, "delayed": 0}
        return {"allowed": b.allowed, "denied": b.denied, "delayed": b.delayed}

