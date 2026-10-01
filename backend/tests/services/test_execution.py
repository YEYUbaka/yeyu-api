from __future__ import annotations

import json
import math
import time as time_module
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from uuid import UUID

import pytest

from app.services.execution.adapters.content import AllowlistedHttpAdapter
from app.services.execution.models import (
    AdapterResult,
    AdapterTimeout,
    ApiAdapter,
    ExecutionContext,
    InvalidParameters,
    RedirectRejected,
    ResourceLimitExceeded,
    UnsafeTarget,
    UpstreamError,
)
from app.services.execution.registry import AdapterRegistry, UnknownApiSlug
from app.services.execution.runner import ApiRunner

NOW = datetime(2026, 10, 1, 12, 0, 0, 123456, tzinfo=UTC)


def _context(*, timeout_ms: int = 500) -> ExecutionContext:
    return ExecutionContext(
        request_id="req-test-001",
        api_slug="time",
        api_key_id="key-test-001",
        user_id="user-test-001",
        client_ip=ip_address("192.0.2.10"),
        timeout_ms=timeout_ms,
        now=NOW,
    )


class CacheDouble:
    def __init__(self) -> None:
        self.fresh: dict[str, object] = {}
        self.stale: dict[str, tuple[object, datetime, datetime]] = {}
        self.writes: list[tuple[str, Mapping[str, object], object]] = []

    def _key(self, api_slug: str, params: Mapping[str, object]) -> str:
        return json.dumps(
            [api_slug, dict(params)],
            sort_keys=True,
            separators=(",", ":"),
        )

    def get_for(
        self,
        api_slug: str,
        params: Mapping[str, object],
        *,
        now: datetime | None = None,
    ) -> object | None:
        return self.fresh.get(self._key(api_slug, params))

    def set_for(
        self,
        api_slug: str,
        params: Mapping[str, object],
        payload: object,
        **_: object,
    ) -> None:
        self.writes.append((api_slug, params, payload))
        self.fresh[self._key(api_slug, params)] = payload

    def stale_value_for(
        self,
        api_slug: str,
        params: Mapping[str, object],
        *,
        now: datetime | None = None,
        stale_reason: str = "upstream_error",
    ) -> object | None:
        current = now or NOW
        item = self.stale.get(self._key(api_slug, params))
        if item is None:
            return None
        payload, expires_at, stale_until = item
        if current < expires_at or current >= stale_until:
            return None
        return type(
            "FakeCacheValue",
            (),
            {
                "payload": payload,
                "data": payload,
                "meta": type(
                    "FakeCacheMeta",
                    (),
                    {
                        "cache_hit": True,
                        "stale": True,
                        "stale_reason": stale_reason,
                        "data_at": expires_at - timedelta(seconds=60),
                    },
                )(),
            },
        )()


class CountingAdapter(ApiAdapter):
    adapter_name = "builtin-tools"
    cacheable = True

    def __init__(
        self,
        payload: object | None = None,
        *,
        error: Exception | None = None,
        delay_seconds: float = 0,
    ) -> None:
        self.payload = payload if payload is not None else {"ok": True}
        self.error = error
        self.delay_seconds = delay_seconds
        self.calls = 0

    def execute(
        self,
        context: ExecutionContext,
        params: Mapping[str, object],
    ) -> AdapterResult:
        self.calls += 1
        if self.delay_seconds:
            time_module.sleep(self.delay_seconds)
        if self.error is not None:
            raise self.error
        return AdapterResult(data=self.payload, data_at=context.now)


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        body: bytes = b'{"ok":true}',
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = dict(headers or {"content-type": "application/json"})

    def iter_bytes(self):
        yield self._body


class FakeHttpClient:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _public_resolver(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def _approved_http_adapter(
    client: FakeHttpClient,
    *,
    resolver=_public_resolver,
    max_response_bytes: int = 4096,
) -> AllowlistedHttpAdapter:
    return AllowlistedHttpAdapter(
        endpoint="https://approved.example/data",
        allowed_hosts={"approved.example"},
        provider_ref="test-provider",
        allowed_params={"q": str},
        http_client=client,
        resolver=resolver,
        max_response_bytes=max_response_bytes,
    )


def test_registry_rejects_unknown_url_and_path_slugs() -> None:
    registry = AdapterRegistry()

    for slug in (
        "unknown",
        "https://evil.example/steal",
        "../time",
        "/v1/tools/time",
        "time/../uuid",
    ):
        with pytest.raises(UnknownApiSlug):
            registry.get(slug)


def test_fixed_time_tool_has_explicit_utc_unix_and_timezone_semantics() -> None:
    adapter = AdapterRegistry().get("time")

    result = adapter.execute(
        _context(),
        {"timezone": "Asia/Shanghai"},
    )

    assert result.data["utc"] == "2026-10-01T12:00:00.123456Z"
    assert result.data["unix_timestamp"] == NOW.timestamp()
    assert result.data["timezone"] == "Asia/Shanghai"
    assert result.data["local"].endswith("+08:00")


def test_fixed_uuid_tool_returns_a_new_uuid_without_user_input() -> None:
    adapter = AdapterRegistry().get("uuid")

    first = adapter.execute(_context(), {}).data["uuid"]
    second = adapter.execute(_context(), {}).data["uuid"]

    assert UUID(first).version == 4
    assert UUID(second).version == 4
    assert first != second


def test_tool_parameters_are_finite_bounded_and_not_urls_or_paths() -> None:
    adapter = AdapterRegistry().get("time")

    with pytest.raises(InvalidParameters):
        adapter.execute(_context(), {"url": "https://evil.example"})
    with pytest.raises(InvalidParameters):
        adapter.execute(_context(), {"timezone": math.nan})
    with pytest.raises(InvalidParameters):
        adapter.execute(_context(), {"timezone": "A" * 5000})


def test_runner_success_has_explicit_no_cache_metadata() -> None:
    response = ApiRunner().run("time", _context(), {})

    assert response.success is True
    assert response.error is None
    assert response.meta == {
        "request_id": "req-test-001",
        "cache_hit": False,
        "stale": False,
        "stale_reason": "no_cache",
        "data_at": NOW,
    }


def test_runner_rejects_bad_parameters_and_does_not_execute() -> None:
    adapter = CountingAdapter()
    runner = ApiRunner(registry=AdapterRegistry(overrides={"time": adapter}))

    response = runner.run("time", _context(), {"url": "https://evil.example"})

    assert response.success is False
    assert response.error["code"] == "INVALID_PARAMETERS"
    assert adapter.calls == 0


def test_runner_enforces_context_timeout() -> None:
    adapter = CountingAdapter(delay_seconds=0.05)
    runner = ApiRunner(registry=AdapterRegistry(overrides={"time": adapter}))

    response = runner.run("time", _context(timeout_ms=5), {})

    assert response.success is False
    assert response.error["code"] == "UPSTREAM_TIMEOUT"
    assert response.meta["stale"] is False


def test_runner_uses_fresh_cache_and_writes_successful_results() -> None:
    cache = CacheDouble()
    adapter = CountingAdapter(payload={"value": 42})
    registry = AdapterRegistry(overrides={"time": adapter})
    runner = ApiRunner(registry=registry, cache=cache)

    first = runner.run("time", _context(), {})
    second = runner.run("time", _context(), {})

    assert first.success is True
    assert first.meta["cache_hit"] is False
    assert second.success is True
    assert second.data == {"value": 42}
    assert second.meta["cache_hit"] is True
    assert adapter.calls == 1


def test_runner_returns_stale_fallback_only_inside_allowed_window() -> None:
    cache = CacheDouble()
    cache.stale[cache._key("time", {})] = (
        {"cached": True},
        NOW - timedelta(seconds=1),
        NOW + timedelta(seconds=30),
    )
    adapter = CountingAdapter(error=TimeoutError("provider timed out"))
    runner = ApiRunner(
        registry=AdapterRegistry(overrides={"time": adapter}),
        cache=cache,
    )

    response = runner.run("time", _context(), {})

    assert response.success is True
    assert response.data == {"cached": True}
    assert response.meta["cache_hit"] is True
    assert response.meta["stale"] is True
    assert response.meta["stale_reason"] == "upstream_timeout"

    cache.stale[cache._key("time", {})] = (
        {"cached": True},
        NOW - timedelta(seconds=90),
        NOW - timedelta(seconds=1),
    )
    no_fallback = runner.run("time", _context(), {})
    assert no_fallback.success is False
    assert no_fallback.error["code"] == "UPSTREAM_TIMEOUT"
    assert no_fallback.meta["stale"] is False
    assert no_fallback.meta["stale_reason"] == "no_cache"


def test_fixed_https_endpoint_rejects_arbitrary_url_and_path_parameters() -> None:
    client = FakeHttpClient([FakeResponse()])
    adapter = _approved_http_adapter(client)

    with pytest.raises(InvalidParameters):
        adapter.execute(_context(), {"url": "https://evil.example"})
    with pytest.raises(InvalidParameters):
        adapter.execute(_context(), {"path": "../../etc/passwd"})

    result = adapter.execute(_context(), {"q": "safe"})
    assert result.data == {"ok": True}
    assert client.calls[0]["url"] == "https://approved.example/data?q=safe"


def test_endpoint_and_redirect_are_revalidated_against_https_host_allowlist() -> None:
    with pytest.raises(UnsafeTarget):
        _approved_http_adapter(
            FakeHttpClient([]),
            resolver=lambda _host, _port: ["127.0.0.1"],
        ).execute(_context(), {})

    redirect = FakeResponse(
        status_code=302,
        headers={"location": "http://evil.example/next"},
        body=b"",
    )
    adapter = _approved_http_adapter(FakeHttpClient([redirect]))
    with pytest.raises(RedirectRejected):
        adapter.execute(_context(), {})

    private_redirect = FakeResponse(
        status_code=302,
        headers={"location": "https://approved.example/private"},
        body=b"",
    )
    adapter = _approved_http_adapter(
        FakeHttpClient([private_redirect, FakeResponse()]),
        resolver=lambda host, port: [
            "127.0.0.1" if host == "approved.example" and port == 443 else "93.184.216.34"
        ],
    )
    with pytest.raises(UnsafeTarget):
        adapter.execute(_context(), {})


def test_http_adapter_rejects_oversized_non_json_and_error_responses() -> None:
    oversized = FakeHttpClient([FakeResponse(body=b"x" * 33)])
    with pytest.raises(ResourceLimitExceeded):
        _approved_http_adapter(oversized, max_response_bytes=32).execute(
            _context(), {}
        )

    non_json = FakeHttpClient(
        [FakeResponse(body=b"not-json", headers={"content-type": "text/plain"})]
    )
    with pytest.raises(UpstreamError):
        _approved_http_adapter(non_json).execute(_context(), {})

    upstream_error = FakeHttpClient([FakeResponse(status_code=503, body=b"{}")])
    with pytest.raises(RuntimeError, match="upstream"):
        _approved_http_adapter(upstream_error).execute(_context(), {})


def test_http_adapter_converts_upstream_timeout_without_public_network() -> None:
    client = FakeHttpClient([TimeoutError("fake timeout"), TimeoutError("fake timeout")])
    adapter = _approved_http_adapter(client)

    with pytest.raises(AdapterTimeout):
        adapter.execute(_context(timeout_ms=50), {})
    assert len(client.calls) <= 2
