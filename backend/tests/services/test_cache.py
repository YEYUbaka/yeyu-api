from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from redis.exceptions import RedisError

from app.services.cache import (
    CacheKey,
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

    def put_raw(self, key: str, value: dict[str, object]) -> None:
        self.values[key] = (json.dumps(value), float("inf"))


def _raw_entry(
    *,
    data_at: datetime,
    expires_at: datetime,
    stale_until: datetime,
) -> dict[str, object]:
    return {
        "payload": {"temperature": 20},
        "data_at": data_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "stale_until": stale_until.isoformat(),
    }


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
    assert isinstance(first, str)
    assert first.startswith("yeyu:cache:weather:")
    with pytest.raises(InvalidCacheKey):
        build_cache_key("https://attacker.example/data", {})


def test_cache_key_is_immutable_and_bound_to_its_service_factory() -> None:
    memory = MemoryRedis()
    owner = CacheService(client=memory)
    other = CacheService(client=memory)
    key = owner.key_for("weather", {"city": "city-a"})

    assert isinstance(key, CacheKey)
    for attribute in ("api_slug", "fingerprint", "_owner_token", "value"):
        with pytest.raises(AttributeError):
            setattr(key, attribute, object())

    owner.set(key, {"temperature": 20})
    assert owner.get(key) is not None
    with pytest.raises(InvalidCacheKey):
        other.get(key)
    with pytest.raises(InvalidCacheKey):
        other.set(key, {})
    with pytest.raises(InvalidCacheKey):
        other.stale_value(key)


def test_cache_low_level_operations_reject_handwritten_matching_key() -> None:
    cache = CacheService(client=MemoryRedis())
    handwritten = "yeyu:cache:weather:" + ("a" * 64)

    with pytest.raises(InvalidCacheKey):
        cache.get(handwritten)
    with pytest.raises(InvalidCacheKey):
        cache.set(handwritten, {})
    with pytest.raises(InvalidCacheKey):
        cache.stale_value(handwritten)


def test_cache_for_helpers_use_factory_generated_typed_handles() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    cache = CacheService(client=MemoryRedis(), default_ttl_seconds=60)

    cache.set_for(
        "weather",
        {"city": "city-a"},
        {"temperature": 20},
        now=now,
    )

    value = cache.get_for("weather", {"city": "city-a"}, now=now)

    assert value is not None
    assert value.payload == {"temperature": 20}


def test_stale_cache_is_explicit_and_includes_metadata() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    cache = CacheService(
        client=MemoryRedis(),
        default_ttl_seconds=60,
        max_stale_age_seconds=3600,
    )
    key = cache.key_for("weather", {"city": "city-a"})
    cache.set(
        key,
        {"temperature": 20},
        data_at=now - timedelta(seconds=120),
        now=now,
    )

    assert cache.get(key, now=now) is None
    value = cache.stale_value(key, now=now, stale_reason="upstream_error")

    assert value is not None
    assert value.payload == {"temperature": 20}
    assert value.meta.cache_hit is True
    assert value.meta.stale is True
    assert value.meta.stale_reason == "upstream_error"
    assert value.meta.data_at == now - timedelta(seconds=120)


def test_stale_cache_respects_maximum_age() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    cache = CacheService(
        client=MemoryRedis(),
        default_ttl_seconds=60,
        max_stale_age_seconds=60,
    )
    key = cache.key_for("weather", {"city": "city-a"})
    cache.set(
        key,
        {"temperature": 20},
        data_at=now - timedelta(hours=1),
        now=now,
    )

    assert cache.stale_value(key, now=now, stale_reason="upstream_error") is None


def test_cache_stale_window_is_after_expiry_and_capped_by_service_config() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    memory = MemoryRedis()
    cache = CacheService(
        client=memory,
        default_ttl_seconds=60,
        max_stale_age_seconds=60,
    )
    key = cache.key_for("weather", {"city": "city-a"})

    cache.set(
        key,
        {"temperature": 20},
        data_at=now,
        now=now,
        max_stale_age_seconds=2030,
    )

    entry = json.loads(memory.values[key.value][0])
    expires_at = datetime.fromisoformat(entry["expires_at"])
    stale_until = datetime.fromisoformat(entry["stale_until"])
    assert stale_until - expires_at == timedelta(seconds=60)


def test_cache_stale_age_zero_ends_at_expiry() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    memory = MemoryRedis()
    cache = CacheService(client=memory, default_ttl_seconds=60)
    key = cache.key_for("weather", {"city": "city-a"})

    cache.set(
        key,
        {"temperature": 20},
        data_at=now,
        now=now,
        max_stale_age_seconds=0,
    )

    entry = json.loads(memory.values[key.value][0])
    assert entry["stale_until"] == entry["expires_at"]
    assert (
        cache.stale_value(
            key,
            now=now + timedelta(seconds=60),
            stale_reason="upstream_error",
        )
        is None
    )


def test_cache_write_rejects_future_data_timestamp() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    cache = CacheService(client=MemoryRedis())
    key = cache.key_for("weather", {"city": "city-a"})

    with pytest.raises(ValueError, match="future"):
        cache.set(key, {}, data_at=now + timedelta(seconds=1), now=now)


def test_cache_read_rejects_future_data_timestamp() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    memory = MemoryRedis()
    cache = CacheService(client=memory, max_stale_age_seconds=3600)
    key = cache.key_for("weather", {"city": "city-a"})
    memory.put_raw(
        key.value,
        _raw_entry(
            data_at=now + timedelta(seconds=1),
            expires_at=now + timedelta(seconds=61),
            stale_until=now + timedelta(seconds=3661),
        ),
    )

    with pytest.raises(CacheUnavailable):
        cache.stale_value(key, now=now)


def test_cache_read_rejects_reversed_timestamp_order() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    memory = MemoryRedis()
    cache = CacheService(client=memory)
    key = cache.key_for("weather", {"city": "city-a"})
    memory.put_raw(
        key.value,
        _raw_entry(
            data_at=now,
            expires_at=now - timedelta(seconds=1),
            stale_until=now + timedelta(seconds=60),
        ),
    )

    with pytest.raises(CacheUnavailable):
        cache.get(key, now=now)


def test_cache_read_rejects_2030_stale_until_bypass() -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    memory = MemoryRedis()
    cache = CacheService(client=memory, max_stale_age_seconds=3600)
    key = cache.key_for("weather", {"city": "city-a"})
    memory.put_raw(
        key.value,
        _raw_entry(
            data_at=now - timedelta(seconds=60),
            expires_at=now - timedelta(seconds=1),
            stale_until=datetime(2030, 1, 1, tzinfo=UTC),
        ),
    )

    with pytest.raises(CacheUnavailable):
        cache.stale_value(key, now=now)


def test_cache_redis_failure_is_explicit() -> None:
    class BrokenRedis:
        def get(self, _key: str) -> None:
            raise RedisError("redis unavailable")

    cache = CacheService(client=BrokenRedis())
    key = cache.key_for("weather", {"city": "city-a"})

    with pytest.raises(CacheUnavailable):
        cache.get(key)
