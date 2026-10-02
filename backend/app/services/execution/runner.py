from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Any, Protocol

from app.services.execution.models import (
    AdapterResult,
    AdapterTimeout,
    ApiAdapter,
    ApiResponse,
    ExecutionContext,
    ExecutionError,
    InvalidParameters,
    UpstreamError,
    finite_json_bytes,
    validate_finite_json_mapping,
)
from app.services.execution.registry import AdapterRegistry, UnknownApiSlug

DEFAULT_MAX_WORKERS = 8
MAX_WORKERS = 64


class CacheServiceLike(Protocol):
    def get_for(
        self,
        api_slug: str,
        params: Mapping[str, Any],
        *,
        now: datetime,
    ) -> Any | None: ...

    def set_for(
        self,
        api_slug: str,
        params: Mapping[str, Any],
        payload: Any,
        *,
        data_at: datetime,
        now: datetime,
    ) -> None: ...

    def stale_value_for(
        self,
        api_slug: str,
        params: Mapping[str, Any],
        *,
        now: datetime,
        stale_reason: str,
    ) -> Any | None: ...


class ApiRunner:
    def __init__(
        self,
        *,
        registry: AdapterRegistry | None = None,
        cache: CacheServiceLike | None = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ) -> None:
        if isinstance(max_workers, bool) or not isinstance(max_workers, int):
            raise ValueError("max_workers must be an integer")
        if not 1 <= max_workers <= MAX_WORKERS:
            raise ValueError("max_workers is outside the hard limit")
        self.registry = registry or AdapterRegistry()
        self.cache = cache
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="yeyu-execution",
        )
        self._slots = BoundedSemaphore(max_workers)
        self._state_lock = Lock()
        self._closed = False

    @staticmethod
    def _meta(
        context: ExecutionContext,
        *,
        cache_hit: bool,
        stale: bool,
        stale_reason: str | None,
        data_at: datetime | None,
    ) -> dict[str, Any]:
        return {
            "request_id": context.request_id,
            "cache_hit": cache_hit,
            "stale": stale,
            "stale_reason": stale_reason,
            "data_at": data_at,
        }

    @classmethod
    def _failure(
        cls,
        context: ExecutionContext,
        error: ExecutionError,
        *,
        stale_reason: str | None = "no_cache",
    ) -> ApiResponse:
        return ApiResponse(
            success=False,
            data=None,
            error={
                "code": error.code,
                "message": error.public_message,
                "request_id": context.request_id,
            },
            meta=cls._meta(
                context,
                cache_hit=False,
                stale=False,
                stale_reason=stale_reason,
                data_at=None,
            ),
        )

    @staticmethod
    def _cache_payload(value: Any) -> tuple[Any, datetime | None]:
        payload = getattr(value, "payload", value)
        if payload is value:
            payload = getattr(value, "data", value)
        metadata = getattr(value, "meta", None)
        if metadata is None:
            metadata = getattr(value, "metadata", None)
        data_at = getattr(metadata, "data_at", None)
        return payload, data_at if isinstance(data_at, datetime) else None

    def _release_slot(self, _future: Any) -> None:
        try:
            self._slots.release()
        except ValueError:
            pass

    def _run_adapter(
        self,
        adapter: ApiAdapter,
        context: ExecutionContext,
        params: Mapping[str, Any],
    ) -> AdapterResult:
        started = monotonic()
        timeout_seconds = context.timeout_ms / 1000
        if not self._slots.acquire(timeout=timeout_seconds):
            raise AdapterTimeout("adapter execution capacity is unavailable")

        with self._state_lock:
            if self._closed:
                self._slots.release()
                raise UpstreamError("adapter runner is closed")
            try:
                future = self._executor.submit(adapter.execute, context, params)
            except Exception as exc:
                self._slots.release()
                raise UpstreamError("adapter execution could not be scheduled") from exc
            future.add_done_callback(self._release_slot)

        remaining = timeout_seconds - (monotonic() - started)
        if remaining <= 0:
            future.cancel()
            raise AdapterTimeout("adapter exceeded the execution context timeout")
        try:
            return future.result(timeout=remaining)
        except FutureTimeout as exc:
            future.cancel()
            raise AdapterTimeout("adapter exceeded the execution context timeout") from exc

    def close(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            executor = self._executor
        executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.close(wait=wait, cancel_futures=cancel_futures)

    def _fresh_cache(
        self,
        adapter: ApiAdapter,
        context: ExecutionContext,
        params: Mapping[str, Any],
    ) -> tuple[Any, datetime] | None:
        if self.cache is None or not adapter.cacheable:
            return None
        try:
            cached = self.cache.get_for(context.api_slug, params, now=context.now)
        except Exception:
            return None
        if cached is None:
            return None
        payload, data_at = self._cache_payload(cached)
        try:
            finite_json_bytes(payload, max_bytes=adapter.max_response_bytes)
        except ExecutionError:
            return None
        return payload, data_at or context.now

    def _stale_cache(
        self,
        adapter: ApiAdapter,
        context: ExecutionContext,
        params: Mapping[str, Any],
        *,
        reason: str,
    ) -> tuple[Any, datetime] | None:
        if self.cache is None or not adapter.cacheable:
            return None
        try:
            cached = self.cache.stale_value_for(
                context.api_slug,
                params,
                now=context.now,
                stale_reason=reason,
            )
        except Exception:
            return None
        if cached is None:
            return None
        payload, data_at = self._cache_payload(cached)
        try:
            finite_json_bytes(payload, max_bytes=adapter.max_response_bytes)
        except ExecutionError:
            return None
        return payload, data_at or context.now

    def run(
        self,
        slug: str,
        context: ExecutionContext,
        params: Mapping[str, Any],
    ) -> ApiResponse:
        try:
            adapter = self.registry.get(slug)
        except UnknownApiSlug as exc:
            return self._failure(context, exc)

        if context.api_slug != slug:
            return self._failure(
                context,
                InvalidParameters("execution context does not match API slug"),
            )
        try:
            validated_params = adapter.validate_params(params)
            if not isinstance(validated_params, Mapping):
                raise InvalidParameters("adapter parameters are invalid")
            safe_params = validate_finite_json_mapping(validated_params)
        except ExecutionError as exc:
            return self._failure(context, exc)
        except Exception:
            return self._failure(context, InvalidParameters("parameters are invalid"))

        fresh = self._fresh_cache(adapter, context, safe_params)
        if fresh is not None:
            payload, data_at = fresh
            return ApiResponse(
                success=True,
                data=payload,
                error=None,
                meta=self._meta(
                    context,
                    cache_hit=True,
                    stale=False,
                    stale_reason=None,
                    data_at=data_at,
                ),
            )

        result: AdapterResult | None = None
        error: ExecutionError | None = None
        try:
            candidate = self._run_adapter(adapter, context, safe_params)
            if not isinstance(candidate, AdapterResult):
                raise UpstreamError("adapter returned an invalid result")
            finite_json_bytes(candidate.data, max_bytes=adapter.max_response_bytes)
            result = candidate
        except AdapterTimeout as exc:
            error = exc
        except ExecutionError as exc:
            error = exc
        except Exception as exc:
            error = UpstreamError("adapter execution failed")
            error.__cause__ = exc

        if result is None:
            assert error is not None
            fallback_reason = (
                "upstream_timeout" if error.code == "UPSTREAM_TIMEOUT" else "upstream_error"
            )
            if error.code in {"UPSTREAM_TIMEOUT", "UPSTREAM_ERROR"}:
                stale = self._stale_cache(
                    adapter,
                    context,
                    safe_params,
                    reason=fallback_reason,
                )
                if stale is not None:
                    payload, data_at = stale
                    return ApiResponse(
                        success=True,
                        data=payload,
                        error=None,
                        meta=self._meta(
                            context,
                            cache_hit=True,
                            stale=True,
                            stale_reason=fallback_reason,
                            data_at=data_at,
                        ),
                    )
            return self._failure(context, error)

        data_at = result.data_at or context.now
        stale_reason: str | None = "no_cache"
        if self.cache is not None and adapter.cacheable:
            try:
                self.cache.set_for(
                    context.api_slug,
                    safe_params,
                    result.data,
                    data_at=data_at,
                    now=context.now,
                )
            except Exception:
                stale_reason = "cache_unavailable"
        return ApiResponse(
            success=True,
            data=result.data,
            error=None,
            meta=self._meta(
                context,
                cache_hit=False,
                stale=False,
                stale_reason=stale_reason,
                data_at=data_at,
            ),
        )


__all__ = ["ApiRunner", "CacheServiceLike"]
