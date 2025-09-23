"""Redis-backed cache helpers with last-good fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from redis import Redis


@dataclass(frozen=True)
class CachePolicy:
    price_ttl: int = 900
    index_ttl: int = 86_400
    indicator_ttl: int = 3_600
    spp_ttl: int = 1_800
    last_good_ttl: int = 86_400


@dataclass(frozen=True)
class CacheRecord:
    value: Mapping[str, Any]
    stale: bool
    age_seconds: int


class CacheClient:
    def __init__(
        self,
        redis_client: Redis,
        policy: CachePolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._redis = redis_client
        self._policy = policy or CachePolicy()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # Price -----------------------------------------------------------------
    def set_price(self, provider: str, region_id: int, type_id: int, payload: Mapping[str, Any]) -> None:
        key = f"price:{provider}:{region_id}:{type_id}"
        self._set_value(key, payload, self._policy.price_ttl)

    def get_price(self, provider: str, region_id: int, type_id: int) -> CacheRecord | None:
        key = f"price:{provider}:{region_id}:{type_id}"
        return self._get_value(key)

    # Indices ---------------------------------------------------------------
    def set_index(self, system_id: int, activity: str, payload: Mapping[str, Any]) -> None:
        key = f"index:{system_id}:{activity}"
        self._set_value(key, payload, self._policy.index_ttl)

    def get_index(self, system_id: int, activity: str) -> CacheRecord | None:
        key = f"index:{system_id}:{activity}"
        return self._get_value(key)

    # Indicators ------------------------------------------------------------
    def set_indicator(self, region_id: int, type_id: int, payload: Mapping[str, Any]) -> None:
        key = f"indicator:{region_id}:{type_id}"
        self._set_value(key, payload, self._policy.indicator_ttl)

    def get_indicator(self, region_id: int, type_id: int) -> CacheRecord | None:
        key = f"indicator:{region_id}:{type_id}"
        return self._get_value(key)

    # SPP -------------------------------------------------------------------
    def set_spp(self, type_id: int, region_id: int, params_hash: str, payload: Mapping[str, Any]) -> None:
        key = f"spp:{type_id}:{region_id}:{params_hash}"
        self._set_value(key, payload, self._policy.spp_ttl)

    def get_spp(self, type_id: int, region_id: int, params_hash: str) -> CacheRecord | None:
        key = f"spp:{type_id}:{region_id}:{params_hash}"
        return self._get_value(key)

    # Internal helpers ------------------------------------------------------
    def _set_value(self, key: str, payload: Mapping[str, Any], ttl: int) -> None:
        now = self._clock()
        envelope = {
            "stored_at": now.isoformat(),
            "ttl": ttl,
            "value": payload,
        }
        serialized = json.dumps(envelope, default=str)
        self._redis.setex(name=key, time=ttl, value=serialized)
        self._redis.setex(name=f"{key}:last_good", time=self._policy.last_good_ttl, value=serialized)

    def _get_value(self, key: str) -> CacheRecord | None:
        raw = self._redis.get(key)
        source_key = key
        if raw is None:
            raw = self._redis.get(f"{key}:last_good")
            source_key = f"{key}:last_good"
            if raw is None:
                return None
        envelope = json.loads(raw)
        stored_at = datetime.fromisoformat(envelope["stored_at"])
        ttl = envelope["ttl"]
        age = int((self._clock() - stored_at).total_seconds())
        stale = age > ttl or source_key.endswith(":last_good")
        return CacheRecord(value=envelope["value"], stale=stale, age_seconds=age)
