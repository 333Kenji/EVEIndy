"""Provider factory utilities.

Constructs HTTP clients, rate limiters, and provider instances using Settings.
"""

from __future__ import annotations

import httpx

from app.config import Settings
from app.rate_limit import limiter_for_provider
from .adam4eve import Adam4EVEProvider
from .fuzzwork import FuzzworkProvider
from .esi import ESIClient


def build_http_client(timeout: float = 10.0) -> httpx.Client:
    return httpx.Client(timeout=timeout)


def make_price_provider(name: str, settings: Settings) -> object:
    client = build_http_client()
    lname = name.lower()
    if lname == "adam4eve":
        return Adam4EVEProvider(
            client=client,
            base_url=getattr(settings, "adam4eve_base_url", "https://api.adam4eve.eu"),
            rate_limiter=limiter_for_provider("adam4eve", settings),
        )
    if lname == "fuzzwork":
        return FuzzworkProvider(
            client=client,
            base_url=getattr(settings, "fuzzwork_base_url", "https://market.fuzzwork.co.uk"),
            rate_limiter=limiter_for_provider("fuzzwork", settings),
        )
    raise ValueError(f"Unknown provider: {name}")


def make_esi(settings: Settings, token_provider=None) -> ESIClient:
    return ESIClient(
        client=build_http_client(timeout=15.0),
        base_url="https://esi.evetech.net/latest",
        token_provider=token_provider,
        rate_limiter=limiter_for_provider("esi", settings),
    )

