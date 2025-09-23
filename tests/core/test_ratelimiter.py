from __future__ import annotations

from typing import List

from core.ratelimiter import RateLimiter


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start
        self.sleeps: List[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


def test_ratelimiter_allows_within_capacity() -> None:
    clk = FakeClock()
    rl = RateLimiter(capacity=2, refill_rate_per_sec=1.0, now=clk.now, sleep=clk.sleep)
    key = "provider:endpoint"
    assert rl.try_acquire(key) is True
    assert rl.try_acquire(key) is True
    assert rl.try_acquire(key) is False  # exhausted
    m = rl.metrics(key)
    assert m["allowed"] == 2
    assert m["denied"] == 1


def test_ratelimiter_blocks_until_refilled() -> None:
    clk = FakeClock()
    rl = RateLimiter(capacity=1, refill_rate_per_sec=2.0, now=clk.now, sleep=clk.sleep)
    key = "esi:/industry/jobs"
    rl.block_until_allowed(key)
    # second call must wait 0.5s (needs 1 token; rate=2 tokens/s)
    rl.block_until_allowed(key)
    assert sum(clk.sleeps) >= 0.5
    m = rl.metrics(key)
    assert m["delayed"] >= 1

