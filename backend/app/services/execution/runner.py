from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime
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
    ) -> None:
        self.registry = registry or AdapterRegistry()
        self.cache = cache

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
            error={"code": error.code, "message": error.public_message},
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

    @staticmethod
    def _run_adapter(
        adapter: ApiAdapter,
        context: ExecutionContext,
        params: Mapping[str, Any],
    ) -> AdapterResult:
        executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="yeyu-execution",
        )
        future = executor.submit(adapter.execute, context, params)
        try:
            return future.result(timeout=context.timeout_ms / 1000)
        except FutureTimeout as exc:
            future.cancel()
            raise AdapterTimeout("adapter exceeded the execution context timeout") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

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
            safe_params = validate_finite_json_mapping(params)
        except ExecutionError as exc:
            return self._failure(context, exc)

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
            result = self._run_adapter(adapter, context, safe_params)
            if not isinstance(result, AdapterResult):
                raise UpstreamError("adapter returned an invalid result")
            finite_json_bytes(result.data, max_bytes=adapter.max_response_bytes)
        except FutureTimeout as exc:
            error: ExecutionError = AdapterTimeout("adapter exceeded the execution context timeout")
            error.__cause__ = exc
        except AdapterTimeout as exc:
            error = exc
        except TimeoutError as exc:
            error = AdapterTimeout("adapter timed out")
            error.__cause__ = exc
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
