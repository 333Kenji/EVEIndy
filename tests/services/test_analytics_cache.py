from __future__ import annotations

from decimal import Decimal

import fakeredis

from app.services import analytics as svc


def test_indicators_cache_fallback(monkeypatch) -> None:
    # Use fake redis
    r = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(svc, "_get_redis", lambda *_: r)
    # Fake DB series
    monkeypatch.setattr(svc, "_get_engine", lambda *_: None)

    # Monkeypatch _fetch_price_series to return data once, then raise
    series = [Decimal("100"), Decimal("101"), Decimal("102"), Decimal("101"), Decimal("103")]
    called = {"n": 0}

    def fake_fetch(conn, region_id, type_id, limit):  # noqa: ARG001
        called["n"] += 1
        if called["n"] == 1:
            return series
        raise RuntimeError("DB unavailable")

    monkeypatch.setattr(svc, "_fetch_price_series", fake_fetch)

    # First call populates cache
    res1 = svc.indicators(type_id=34, region_id=10000002, window=5)
    # Second call should use cache despite DB unavailable
    res2 = svc.indicators(type_id=34, region_id=10000002, window=5)
    assert str(res1.ma) == str(res2.ma)


def test_spp_plus_batch_options_affect_recommendation(monkeypatch) -> None:
    r = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(svc, "_get_redis", lambda *_: r)
    monkeypatch.setattr(svc, "_get_engine", lambda *_: None)

    base_kwargs = {
        "type_id": 603,
        "region_id": 10000002,
        "lead_time_days": Decimal("1"),
        "horizon_days": Decimal("3"),
    }

    res_default = svc.spp_plus(batch_options=[1, 2, 3], **base_kwargs)
    res_alt = svc.spp_plus(batch_options=[5, 10], **base_kwargs)

    assert res_default["recommended_batch"] == 3
    assert res_alt["recommended_batch"] == 10
    assert res_default["recommended_batch"] != res_alt["recommended_batch"]

