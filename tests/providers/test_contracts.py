from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from app.providers import (
    Adam4EVEProvider,
    CircuitBreakerOpen,
    ESIClient,
    FuzzworkProvider,
)
from app.providers.base import CircuitBreaker


def build_mock_client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_adam4eve_provider_success() -> None:
    payload = {
        "bid": "5.10",
        "ask": "5.90",
        "volatility": "0.12",
        "depth": {"qty_1pct": "1000", "qty_5pct": "3500"},
        "updated": "2024-04-01T00:00:00",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/market/type/34/region/10000002"
        return httpx.Response(200, json=payload)

    client = build_mock_client(httpx.MockTransport(handler))
    class TestLimiter:
        def __init__(self) -> None:
            self.called = 0

        def block_until_allowed(self, key: str) -> None:  # type: ignore[override]
            self.called += 1

    limiter = TestLimiter()
    provider = Adam4EVEProvider(client=client, base_url="https://example.com", rate_limiter=limiter)
    quote = provider.get(type_id=34, region_id=10000002)

    assert quote.provider == "adam4eve"
    assert quote.bid == Decimal("5.10")
    assert quote.mid == Decimal("5.50")
    assert quote.depth_qty_1pct == Decimal("1000")
    assert limiter.called >= 1


def test_adam4eve_provider_circuit_breaks_after_failures() -> None:
    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["value"] += 1
        return httpx.Response(503, json={"error": "unavailable"})

    client = build_mock_client(httpx.MockTransport(handler))
    breaker = CircuitBreaker(max_failures=1)
    provider = Adam4EVEProvider(client=client, base_url="https://example.com", breaker=breaker)

    with pytest.raises(httpx.HTTPStatusError):
        provider.get(34, 10000002)
    assert breaker.failure_count == 1

    with pytest.raises(CircuitBreakerOpen):
        provider.get(34, 10000002)
    assert call_count["value"] >= 1


def test_fuzzwork_provider_success() -> None:
    payload = {
        "buy": {"price": "4.95", "volume": "1200"},
        "sell": {"price": "5.40", "volume": "800"},
        "generated": "2024-04-01T00:00:00",
        "depth": {"qty_1pct": "600", "qty_5pct": "2500"},
        "volatility": "0.08",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/orders/type/34/region/10000002"
        return httpx.Response(200, json=payload)

    client = build_mock_client(httpx.MockTransport(handler))
    class TestLimiter:
        def __init__(self) -> None:
            self.called = 0

        def block_until_allowed(self, key: str) -> None:  # type: ignore[override]
            self.called += 1

    limiter = TestLimiter()
    provider = FuzzworkProvider(client=client, base_url="https://example.com", rate_limiter=limiter)
    quote = provider.get(34, 10000002)

    assert quote.provider == "fuzzwork"
    assert quote.ask == Decimal("5.40")
    assert quote.depth_qty_5pct == Decimal("2500")
    assert limiter.called >= 1


def test_esi_client_parses_headers_and_payloads() -> None:
    jobs_payload = [
        {
            "job_id": 1,
            "blueprint_type_id": 603,
            "runs": 2,
            "status": "active",
            "start_date": "2024-04-01T00:00:00Z",
            "end_date": "2024-04-01T12:00:00Z",
            "installer_id": 123,
            "location_id": 60003760,
        }
    ]

    expires = "Wed, 10 Apr 2024 12:00:00 GMT"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"].startswith("Bearer ")
        if request.url.path.endswith("/industry/jobs/corp"):
            return httpx.Response(200, json=jobs_payload, headers={"Expires": expires})
        if request.url.path.endswith("/assets/corp"):
            return httpx.Response(
                200,
                json=[
                    {
                        "item_id": 9001,
                        "type_id": 34,
                        "quantity": 100,
                        "location_id": 60003760,
                        "is_singleton": False,
                    }
                ],
                headers={"Expires": expires},
            )
        if request.url.path.endswith("/industry/systems/30000142"):
            return httpx.Response(
                200,
                json=[{"activity": "manufacturing", "cost_index": "0.05"}],
                headers={"Expires": expires},
            )
        if request.url.path.endswith("/skills/100"):
            return httpx.Response(
                200,
                json={
                    "character_id": 100,
                    "total_sp": 5000000,
                    "skills": [{"skill_id": 3380, "active_level": 5}],
                },
                headers={"Expires": expires},
            )
        raise AssertionError(f"Unexpected path {request.url.path}")

    client = build_mock_client(httpx.MockTransport(handler))
    token_provider = lambda: "token-value"
    esi = ESIClient(client=client, base_url="https://esi.test", token_provider=token_provider)

    jobs = esi.list_industry_jobs("corp")
    assert jobs.expires == datetime(2024, 4, 10, 12, 0, tzinfo=timezone.utc)
    assert jobs.data[0].job_id == 1

    assets = esi.list_assets("corp")
    assert assets.data[0].quantity == 100

    indices = esi.get_system_cost_indices(30000142)
    assert indices.data[0].activity == "manufacturing"

    skills = esi.get_character_skills(100)
    assert skills.data[0].character_id == 100
