from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.redis import RedisStore, RedisUnavailable


class InvalidCacheKey(ValueError):
    """The cache key was not produced from a fixed API slug and parameters."""


class CacheUnavailable(RuntimeError):
    """The cache store could not be read or written safely."""


_SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,99}\Z")
_CACHE_KEY_PATTERN = re.compile(
    r"yeyu:cache:(?P<slug>[a-z0-9][a-z0-9._-]{0,99}):(?P<fingerprint>[0-9a-f]{64})\Z"
)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidCacheKey("cache parameter keys must be strings")
            normalized[key] = _normalize_value(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise InvalidCacheKey("cache parameters must be JSON-serializable")


def _validate_slug(api_slug: str) -> str:
    if not isinstance(api_slug, str) or _SLUG_PATTERN.fullmatch(api_slug) is None:
        raise InvalidCacheKey("cache API slug must be a fixed lowercase slug")
    return api_slug


def normalized_parameter_fingerprint(params: Mapping[str, Any]) -> str:
    if not isinstance(params, Mapping):
        raise InvalidCacheKey("cache parameters must be a mapping")
    normalized = _normalize_value(params)
    try:
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidCacheKey("cache parameters must be JSON-serializable") from exc
    return hashlib.sha256(encoded).hexdigest()


def build_cache_key(api_slug: str, params: Mapping[str, Any]) -> str:
    slug = _validate_slug(api_slug)
    return f"yeyu:cache:{slug}:{normalized_parameter_fingerprint(params)}"


def _validate_cache_key(cache_key: str) -> None:
    if not isinstance(cache_key, str) or _CACHE_KEY_PATTERN.fullmatch(cache_key) is None:
        raise InvalidCacheKey(
            "cache key must be generated as yeyu:cache:<slug>:<sha256>"
        )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class CacheMeta:
    cache_hit: bool
    stale: bool
    stale_reason: str | None
    data_at: datetime


@dataclass(frozen=True)
class CacheValue:
    payload: Any
    meta: CacheMeta

    @property
    def data(self) -> Any:
        return self.payload

    @property
    def metadata(self) -> CacheMeta:
        return self.meta


class CacheService:
    def __init__(
        self,
        client: Any | None = None,
        *,
        redis: Any | None = None,
        default_ttl_seconds: int = 60,
        max_stale_age_seconds: int = 3600,
    ) -> None:
        if client is not None and redis is not None:
            raise ValueError("provide either client or redis, not both")
        if default_ttl_seconds <= 0 or max_stale_age_seconds < 0:
            raise ValueError("cache TTL values are out of range")
        selected = redis if redis is not None else client
        self.store = selected if isinstance(selected, RedisStore) else RedisStore(selected)
        self.default_ttl_seconds = default_ttl_seconds
        self.max_stale_age_seconds = max_stale_age_seconds

    @staticmethod
    def key_for(api_slug: str, params: Mapping[str, Any]) -> str:
        return build_cache_key(api_slug, params)

    def _read_entry(self, cache_key: str) -> dict[str, Any] | None:
        _validate_cache_key(cache_key)
        try:
            raw = self.store.get(cache_key)
        except RedisUnavailable as exc:
            raise CacheUnavailable from exc
        if raw is None:
            return None
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise CacheUnavailable("cache entry is not valid UTF-8") from exc
        try:
            entry = json.loads(raw)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CacheUnavailable("cache entry is not valid JSON") from exc
        if not isinstance(entry, dict):
            raise CacheUnavailable("cache entry has an invalid shape")
        try:
            entry["data_at"] = _utc(datetime.fromisoformat(entry["data_at"]))
            entry["expires_at"] = _utc(datetime.fromisoformat(entry["expires_at"]))
            entry["stale_until"] = _utc(
                datetime.fromisoformat(entry["stale_until"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CacheUnavailable("cache entry has invalid timestamps") from exc
        if "payload" not in entry:
            raise CacheUnavailable("cache entry has no payload")
        return entry

    @staticmethod
    def _value(entry: dict[str, Any], *, stale: bool, reason: str | None) -> CacheValue:
        return CacheValue(
            payload=entry["payload"],
            meta=CacheMeta(
                cache_hit=True,
                stale=stale,
                stale_reason=reason,
                data_at=entry["data_at"],
            ),
        )

    def set(
        self,
        cache_key: str,
        payload: Any,
        *,
        data_at: datetime | None = None,
        now: datetime | None = None,
        ttl_seconds: int | None = None,
        max_stale_age_seconds: int | None = None,
    ) -> None:
        _validate_cache_key(cache_key)
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        stale_age = (
            self.max_stale_age_seconds
            if max_stale_age_seconds is None
            else max_stale_age_seconds
        )
        if ttl <= 0 or stale_age < 0:
            raise ValueError("cache TTL values are out of range")
        current = _utc(now or datetime.now(UTC))
        observed_at = _utc(data_at or current)
        expires_at = observed_at + timedelta(seconds=ttl)
        stale_until = min(
            expires_at + timedelta(seconds=stale_age),
            observed_at + timedelta(seconds=stale_age),
        )
        entry = {
            "payload": payload,
            "data_at": observed_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "stale_until": stale_until.isoformat(),
        }
        try:
            encoded = json.dumps(
                entry,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise InvalidCacheKey("cache payload must be JSON-serializable") from exc
        retention = max(1, math.ceil((stale_until - current).total_seconds()))
        try:
            if not self.store.set(cache_key, encoded, ttl_seconds=retention):
                raise CacheUnavailable("cache store rejected the write")
        except RedisUnavailable as exc:
            raise CacheUnavailable from exc

    def get(
        self,
        cache_key: str,
        *,
        now: datetime | None = None,
    ) -> CacheValue | None:
        entry = self._read_entry(cache_key)
        if entry is None:
            return None
        if _utc(now or datetime.now(UTC)) < entry["expires_at"]:
            return self._value(entry, stale=False, reason=None)
        return None

    def stale_value(
        self,
        cache_key: str,
        *,
        now: datetime | None = None,
        stale_reason: str = "upstream_error",
    ) -> CacheValue | None:
        if not stale_reason or not stale_reason.strip():
            raise ValueError("stale_reason must not be empty")
        entry = self._read_entry(cache_key)
        if entry is None:
            return None
        current = _utc(now or datetime.now(UTC))
        if current < entry["expires_at"] or current > entry["stale_until"]:
            return None
        return self._value(entry, stale=True, reason=stale_reason.strip())

    def get_for(
        self,
        api_slug: str,
        params: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> CacheValue | None:
        return self.get(build_cache_key(api_slug, params), now=now)

    def set_for(
        self,
        api_slug: str,
        params: Mapping[str, Any],
        payload: Any,
        **kwargs: Any,
    ) -> None:
        self.set(build_cache_key(api_slug, params), payload, **kwargs)

    def stale_value_for(
        self,
        api_slug: str,
        params: Mapping[str, Any],
        **kwargs: Any,
    ) -> CacheValue | None:
        return self.stale_value(build_cache_key(api_slug, params), **kwargs)
