from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from ipaddress import ip_address
from typing import Any

import pytest

from app.services.execution.adapters.content import AllowlistedHttpAdapter
from app.services.execution.models import ExecutionContext, RedirectRejected

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _context() -> ExecutionContext:
    return ExecutionContext(
        request_id="security-request-1",
        api_slug="time",
        api_key_id="security-key-1",
        user_id="security-user-1",
        client_ip=ip_address("192.0.2.10"),
        timeout_ms=500,
        now=NOW,
    )


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
        self.closed = False

    def iter_bytes(self):
        yield self._body

    def close(self) -> None:
        self.closed = True


class AddressRecordingClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.connected_addresses: list[tuple[str, ...]] = []

    def request_pinned(
        self,
        method: str,
        url: str,
        *,
        resolved_addresses: tuple[str, ...],
        **kwargs: Any,
    ) -> FakeResponse:
        del method, url, kwargs
        self.connected_addresses.append(resolved_addresses)
        return self.responses.pop(0)


def _approved_http_adapter(
    client: AddressRecordingClient,
    *,
    allow_redirects: bool = False,
    max_redirects: int = 3,
) -> AllowlistedHttpAdapter:
    return AllowlistedHttpAdapter(
        endpoint="https://approved.example/data",
        allowed_hosts={"approved.example"},
        provider_ref="security-test-provider",
        allowed_params={"q": str},
        http_client=client,
        resolver=lambda _host, _port: ["93.184.216.34"],
        max_response_bytes=4096,
        allow_redirects=allow_redirects,
        max_redirects=max_redirects,
    )


def test_redirect_chain_pins_each_connection_and_closes_last_response() -> None:
    responses = [
        FakeResponse(
            status_code=302,
            headers={"location": "/data?hop=1"},
            body=b"redirect-1",
        ),
        FakeResponse(
            status_code=302,
            headers={"location": "https://approved.example/data?hop=2"},
            body=b"redirect-2",
        ),
        FakeResponse(
            status_code=302,
            headers={"location": "/data?hop=3"},
            body=b"redirect-3",
        ),
    ]
    client = AddressRecordingClient(responses)
    adapter = _approved_http_adapter(
        client,
        allow_redirects=True,
        max_redirects=2,
    )

    with pytest.raises(RedirectRejected):
        adapter.execute(_context(), {})

    assert client.connected_addresses == [
        ("93.184.216.34",),
        ("93.184.216.34",),
        ("93.184.216.34",),
    ]
    assert all(response.closed for response in responses)


@pytest.mark.parametrize(
    "location",
    [
        "https://approved.example/data#fragment",
        None,
    ],
)
def test_redirect_location_boundary_is_checked_across_hops(
    location: str | None,
) -> None:
    response = FakeResponse(
        status_code=302,
        headers={"location": location} if location is not None else {},
        body=b"redirect",
    )
    client = AddressRecordingClient([response])
    adapter = _approved_http_adapter(client, allow_redirects=True)

    with pytest.raises(RedirectRejected):
        adapter.execute(_context(), {})

    assert response.closed is True
