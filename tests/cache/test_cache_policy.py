from datetime import datetime, timedelta, timezone

import fakeredis

from app.cache import CacheClient, CachePolicy


def fixed_clock(start: datetime):
    def _inner() -> datetime:
        return start

    return _inner


def advance_clock(start: datetime, seconds: int):
    def _inner() -> datetime:
        return start + timedelta(seconds=seconds)

    return _inner


def test_cache_returns_fresh_payload() -> None:
    redis_client = fakeredis.FakeRedis(decode_responses=True)
    now = datetime(2024, 4, 15, 12, 0, tzinfo=timezone.utc)
    cache = CacheClient(redis_client, clock=fixed_clock(now))

    cache.set_price("adam4eve", 10000002, 34, {"bid": 5})
    record = cache.get_price("adam4eve", 10000002, 34)

    assert record is not None
    assert record.stale is False
    assert record.value["bid"] == 5


def test_cache_uses_last_good_fallback() -> None:
    redis_client = fakeredis.FakeRedis(decode_responses=True)
    now = datetime(2024, 4, 15, 12, 0, tzinfo=timezone.utc)
    cache = CacheClient(redis_client, clock=fixed_clock(now))

    cache.set_price("adam4eve", 10000002, 34, {"bid": 5})
    redis_client.delete("price:adam4eve:10000002:34")

    cache = CacheClient(redis_client, clock=advance_clock(now, 2000))
    record = cache.get_price("adam4eve", 10000002, 34)
    assert record is not None
    assert record.stale is True
    assert record.value["bid"] == 5
    assert record.age_seconds >= 2000


def test_cache_ttl_configuration() -> None:
    redis_client = fakeredis.FakeRedis(decode_responses=True)
    policy = CachePolicy(price_ttl=60, last_good_ttl=300)
    now = datetime(2024, 4, 15, 12, 0, tzinfo=timezone.utc)
    cache = CacheClient(redis_client, policy=policy, clock=fixed_clock(now))

    cache.set_indicator(10000002, 34, {"ma": 101})
    ttl = redis_client.ttl("indicator:10000002:34")
    last_good_ttl = redis_client.ttl("indicator:10000002:34:last_good")

    assert 0 < ttl <= policy.indicator_ttl
    assert 0 < last_good_ttl <= policy.last_good_ttl
