"""ESI client wrapper with retry, validation, and circuit breaker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Generic, List, Mapping, Sequence, Tuple, TypeVar

import httpx
from pydantic import BaseModel, Field
from tenacity import Retrying, stop_after_attempt, wait_random_exponential

from .base import CircuitBreaker
from core.ratelimiter import RateLimiter

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ESIResponse(Generic[T]):
    data: Sequence[T]
    expires: datetime | None


class IndustryJob(BaseModel):
    job_id: int
    blueprint_type_id: int
    runs: int
    status: str
    start_date: datetime
    end_date: datetime | None = None
    completed_date: datetime | None = None
    installer_id: int = Field(alias="installer_id")
    location_id: int


class Asset(BaseModel):
    item_id: int
    type_id: int
    quantity: int
    location_id: int
    is_singleton: bool


class CostIndex(BaseModel):
    activity: str
    cost_index: Decimal


class CharacterSkills(BaseModel):
    character_id: int
    total_sp: int
    skills: Sequence[Mapping[str, int]]


class ESIClient:
    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        token_provider: Callable[[], str] | None,
        breaker: CircuitBreaker | None = None,
        timeout: float = 15.0,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._token_provider = token_provider
        self._breaker = breaker or CircuitBreaker(max_failures=5)
        self._timeout = timeout
        self._rl = rate_limiter

    def list_industry_jobs(self, owner_scope: str) -> ESIResponse[IndustryJob]:
        data, expires = self._request(
            f"/industry/jobs/{owner_scope}",
            params={"include_completed": "true"},
        )
        return ESIResponse(data=[IndustryJob.model_validate(item) for item in data], expires=expires)

    def list_assets(self, owner_scope: str) -> ESIResponse[Asset]:
        data, expires = self._request(f"/assets/{owner_scope}")
        return ESIResponse(data=[Asset.model_validate(item) for item in data], expires=expires)

    def get_system_cost_indices(self, system_id: int) -> ESIResponse[CostIndex]:
        data, expires = self._request(f"/industry/systems/{system_id}")
        return ESIResponse(data=[CostIndex.model_validate(item) for item in data], expires=expires)

    def get_character_skills(self, character_id: int) -> ESIResponse[CharacterSkills]:
        data, expires = self._request(f"/skills/{character_id}")
        payload = CharacterSkills.model_validate(data)
        return ESIResponse(data=[payload], expires=expires)

    def _auth_header(self) -> Mapping[str, str]:
        if not self._token_provider:
            return {}
        token = self._token_provider()
        return {"Authorization": f"Bearer {token}"}

    def _request(
        self,
        path: str,
        params: Mapping[str, str] | None = None,
    ) -> Tuple[Sequence[Mapping[str, object]], datetime | None]:
        self._breaker.check()

        def _call() -> Tuple[Sequence[Mapping[str, object]], datetime | None]:
            if self._rl:
                self._rl.block_until_allowed(f"esi:{path}")
            response = self._client.get(
                f"{self._base_url}{path}",
                headers=self._auth_header(),
                params=params,
                timeout=self._timeout,
            )
            response.raise_for_status()
            expires = response.headers.get("Expires")
            expires_at = None
            if expires:
                expires_at = datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
            payload = response.json()
            if isinstance(payload, dict):
                return [payload], expires_at
            if isinstance(payload, list):
                return payload, expires_at
            raise ValueError("Unexpected payload type from ESI")

        retry = Retrying(
            stop=stop_after_attempt(5),
            wait=wait_random_exponential(min=1, max=6),
            reraise=True,
        )

        try:
            for attempt in retry:
                with attempt:
                    result = _call()
                    self._breaker.success()
                    return result
        except Exception:  # noqa: BLE001
            self._breaker.failure()
            raise

        raise RuntimeError("Retry loop exhausted")
