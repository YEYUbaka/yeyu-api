from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class RedisUnavailable(RuntimeError):
    """Redis could not perform a required atomic operation."""


@dataclass(frozen=True)
class LimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int | None = None
    failed_index: int | None = None
    remaining_by_limit: tuple[int, ...] = ()


@dataclass(frozen=True)
class LeaseResult:
    allowed: bool
    active: int
    retry_after_seconds: int | None = None


class RedisStore:
    """Small fail-closed Redis primitive layer used by quota and cache services."""

    counter_limit_script = """
local counts = {}
local remaining = {}
local failed_index = 0
local failed_current = 0
local failed_ttl = 0
local minimum_remaining = nil
local window_seconds = tonumber(ARGV[#KEYS + 1])
for i, key in ipairs(KEYS) do
    local current = redis.call('INCRBY', key, 1)
    if current == 1 then
        redis.call('EXPIRE', key, window_seconds)
    end
    local limit = tonumber(ARGV[i])
    local ttl = redis.call('TTL', key)
    counts[i] = current
    remaining[i] = limit - current
    if minimum_remaining == nil or remaining[i] < minimum_remaining then
        minimum_remaining = remaining[i]
    end
    if current > limit and failed_index == 0 then
        failed_index = i
        failed_current = current
        failed_ttl = ttl
    end
end
if failed_index ~= 0 then
    local remaining_after = {}
    for index, key in ipairs(KEYS) do
        local left = redis.call('DECRBY', key, 1)
        if left <= 0 then
            redis.call('DEL', key)
        end
        remaining_after[index] = tonumber(ARGV[index]) - math.max(0, left)
    end
    local result = {0, failed_index, failed_current - 1, failed_ttl}
    for i = 1, #KEYS do
        table.insert(result, remaining_after[i])
    end
    return result
end
local result = {1, minimum_remaining, 0, 0}
for i = 1, #KEYS do
    table.insert(result, remaining[i])
end
return result
"""

    lease_acquire_script = """
local now = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local token = ARGV[4]
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
local active = redis.call('ZCARD', KEYS[1])
if active >= limit then
    local first = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    local retry = ttl
    if #first >= 2 then
        retry = math.max(1, tonumber(first[2]) - now)
    end
    return {0, active, retry}
end
redis.call('ZADD', KEYS[1], now + ttl, token)
local latest = redis.call('ZREVRANGE', KEYS[1], 0, 0, 'WITHSCORES')
local key_ttl = ttl
if #latest >= 2 then
    key_ttl = math.max(1, math.ceil(tonumber(latest[2]) - now))
end
redis.call('EXPIRE', KEYS[1], key_ttl)
return {1, active + 1, ttl}
"""

    lease_release_script = """
local removed = redis.call('ZREM', KEYS[1], ARGV[1])
if removed == 1 and redis.call('ZCARD', KEYS[1]) == 0 then
    redis.call('DEL', KEYS[1])
end
return removed
"""

    def __init__(self, client: Any | None = None, *, url: str | None = None) -> None:
        if client is not None:
            self.client = client
            return
        try:
            self.client = Redis.from_url(
                url or settings.REDIS_URL,
                socket_connect_timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS,
                socket_timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS,
                decode_responses=True,
            )
        except (RedisError, OSError, TypeError, ValueError) as exc:
            raise RedisUnavailable from exc

    @staticmethod
    def _parse_values(value: Any) -> list[Any]:
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]

    def _eval(self, script: str, numkeys: int, *args: Any) -> Any:
        try:
            return self.client.eval(script, numkeys, *args)
        except Exception as exc:
            raise RedisUnavailable from exc

    def ping(self) -> bool:
        try:
            return self.client.ping() is True
        except Exception:
            return False

    def check_limits(
        self,
        *,
        keys: Sequence[str],
        limits: Sequence[int],
        window_seconds: int,
    ) -> LimitResult:
        if not keys or len(keys) != len(limits):
            raise ValueError("keys and limits must have the same non-zero length")
        if window_seconds <= 0 or any(limit < 0 for limit in limits):
            raise ValueError("limits and window_seconds must be non-negative/positive")

        raw = self._eval(
            self.counter_limit_script,
            len(keys),
            *keys,
            *(str(limit) for limit in limits),
            str(window_seconds),
        )
        values = self._parse_values(raw)
        try:
            status = int(values[0])
        except (IndexError, TypeError, ValueError) as exc:
            raise RedisUnavailable("Redis returned an invalid limit result") from exc

        if len(values) == 1:
            # This compatibility path keeps simple deterministic test doubles
            # useful while the real Redis path always returns the Lua tuple.
            current = int(values[0])
            allowed = current <= min(limits)
            return LimitResult(
                allowed=allowed,
                remaining=max(0, min(limits) - current),
                retry_after_seconds=(window_seconds if not allowed else None),
            )

        if status == 0:
            try:
                failed_index = int(values[1])
                current = int(values[2])
                ttl = int(values[3])
            except (IndexError, TypeError, ValueError) as exc:
                raise RedisUnavailable("Redis returned an invalid limit result") from exc
            if not 1 <= failed_index <= len(limits):
                raise RedisUnavailable("Redis returned an invalid limit scope")
            try:
                raw_remaining = values[4:]
                per_limit = (
                    tuple(max(0, int(value)) for value in raw_remaining)
                    if raw_remaining
                    else ()
                )
            except (TypeError, ValueError) as exc:
                raise RedisUnavailable("Redis returned an invalid limit result") from exc
            if per_limit and len(per_limit) != len(limits):
                raise RedisUnavailable("Redis returned incomplete limit remaining")
            failed_remaining = (
                per_limit[failed_index - 1]
                if per_limit
                else max(0, limits[failed_index - 1] - current)
            )
            return LimitResult(
                allowed=False,
                remaining=failed_remaining,
                retry_after_seconds=max(1, ttl),
                failed_index=failed_index,
                remaining_by_limit=per_limit,
            )

        if status != 1:
            raise RedisUnavailable("Redis returned an invalid limit status")
        try:
            remaining = int(values[1])
            per_limit = tuple(int(value) for value in values[4:])
        except (IndexError, TypeError, ValueError) as exc:
            raise RedisUnavailable("Redis returned an invalid limit result") from exc
        return LimitResult(
            allowed=True,
            remaining=max(0, remaining),
            remaining_by_limit=per_limit,
        )

    def acquire_lease(
        self,
        *,
        key: str,
        token: str,
        limit: int,
        ttl_seconds: int,
        now_seconds: int | None = None,
    ) -> LeaseResult:
        if limit <= 0 or ttl_seconds <= 0:
            raise ValueError("limit and ttl_seconds must be positive")
        raw = self._eval(
            self.lease_acquire_script,
            1,
            key,
            str(int(time.time()) if now_seconds is None else now_seconds),
            str(limit),
            str(ttl_seconds),
            token,
        )
        values = self._parse_values(raw)
        try:
            status, active, retry_after = (int(values[0]), int(values[1]), int(values[2]))
        except (IndexError, TypeError, ValueError) as exc:
            raise RedisUnavailable("Redis returned an invalid lease result") from exc
        if status not in {0, 1}:
            raise RedisUnavailable("Redis returned an invalid lease status")
        return LeaseResult(
            allowed=status == 1,
            active=active,
            retry_after_seconds=max(1, retry_after),
        )

    def release_lease(self, *, key: str, token: str) -> bool:
        raw = self._eval(self.lease_release_script, 1, key, token)
        try:
            return int(raw) == 1
        except (TypeError, ValueError) as exc:
            raise RedisUnavailable("Redis returned an invalid release result") from exc

    def get(self, key: str) -> str | bytes | None:
        try:
            return self.client.get(key)
        except Exception as exc:
            raise RedisUnavailable from exc

    def set(self, key: str, value: str, *, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        try:
            result = self.client.set(key, value, ex=ttl_seconds)
        except Exception as exc:
            raise RedisUnavailable from exc
        return bool(result)

    def delete(self, key: str) -> bool:
        try:
            return bool(self.client.delete(key))
        except Exception as exc:
            raise RedisUnavailable from exc


RedisClient = RedisStore
