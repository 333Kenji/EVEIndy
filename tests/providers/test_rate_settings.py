from __future__ import annotations

from app.config import Settings
from app.rate_limit import limiter_for_provider


def test_limiter_configuration_from_settings(monkeypatch) -> None:
    s = Settings(
        esi_capacity=5.0,
        esi_refill_rate=1.0,
        adam4eve_capacity=1.0,
        adam4eve_refill_rate=0.2,
        fuzzwork_capacity=2.0,
        fuzzwork_refill_rate=0.5,
    )
    esi = limiter_for_provider("esi", s)
    a4e = limiter_for_provider("adam4eve", s)
    fw = limiter_for_provider("fuzzwork", s)

    # Access internal fields by probing metrics after registration
    key = "k"
    esi.register_key(key)
    a4e.register_key(key)
    fw.register_key(key)

    # try_acquire consumes one token; we cannot directly inspect capacity, but we can ensure it allows at least one
    assert esi.try_acquire(key) is True
    assert a4e.try_acquire(key) is True
    assert fw.try_acquire(key) is True

