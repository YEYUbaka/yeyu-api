from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest
from redis.exceptions import RedisError

from app.services.cache import (
    CacheService,
    CacheUnavailable,
    InvalidCacheKey,
    build_cache_key,
)


class MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, tuple[str, float]] = {}

    def set(self, key: str, value: str, *, ex: int) -> bool:
        self.values[key] = (value, time.time() + ex)
        return True

    def get(self, key: str) -> str | None:
        entry = self.values.get(key)
        if entry is None:
            return None
        if entry[1] <= time.time():
            self.values.pop(key, None)
            return None
        return entry[0]

    def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)


def test_cache_key_is_slug_and_normalized_parameter_fingerprint() -> None:
    first = build_cache_key(
        "weather",
        {"city": "Shenzhen", "units": "metric"},
    )
    second = build_cache_key(
        "weather",
        {"units": "metric", "city": "Shenzhen"},
    )

    assert first == second
    assert first.startswith("yeyu:cache:weather:")
    with pytest.raises(InvalidCacheKey):
        build_cache_key("https://attacker.example/data", {})


def test_stale_cache_is_explicit_and_includes_metadata() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    cache = CacheService(
        client=MemoryRedis(),
        default_ttl_seconds=60,
        max_stale_age_seconds=3600,
    )
    key = build_cache_key("weather", {"city": "city-a"})
    cache.set(
        key,
        {"temperature": 20},
        data_at=now - timedelta(hours=1),
        now=now,
    )

    assert cache.get(key, now=now) is None
    value = cache.stale_value(key, now=now, stale_reason="upstream_error")

    assert value is not None
    assert value.payload == {"temperature": 20}
    assert value.meta.cache_hit is True
    assert value.meta.stale is True
    assert value.meta.stale_reason == "upstream_error"
    assert value.meta.data_at == now - timedelta(hours=1)


def test_stale_cache_respects_maximum_age() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    cache = CacheService(
        client=MemoryRedis(),
        default_ttl_seconds=60,
        max_stale_age_seconds=60,
    )
    key = build_cache_key("weather", {"city": "city-a"})
    cache.set(
        key,
        {"temperature": 20},
        data_at=now - timedelta(hours=1),
        now=now,
    )

    assert cache.stale_value(key, now=now, stale_reason="upstream_error") is None


def test_cache_redis_failure_is_explicit() -> None:
    class BrokenRedis:
        def get(self, _key: str) -> None:
            raise RedisError("redis unavailable")

    cache = CacheService(client=BrokenRedis())
    key = build_cache_key("weather", {"city": "city-a"})

    with pytest.raises(CacheUnavailable):
        cache.get(key)
