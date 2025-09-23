from __future__ import annotations

from app.config import Settings
from app.providers.factory import make_price_provider, make_esi


def test_make_price_providers() -> None:
    s = Settings()
    a4e = make_price_provider("adam4eve", s)
    fw = make_price_provider("fuzzwork", s)
    assert a4e is not None and fw is not None


def test_make_esi_public() -> None:
    s = Settings()
    esi = make_esi(s)
    assert esi is not None

