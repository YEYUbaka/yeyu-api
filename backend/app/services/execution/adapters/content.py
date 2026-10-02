from __future__ import annotations

import asyncio
import inspect
import json
import re
import socket
import threading
from collections.abc import Callable, Iterable, Mapping
from ipaddress import ip_address
from time import monotonic
from typing import Any
from urllib.parse import unquote, urlencode, urljoin, urlsplit, urlunsplit

from app.services.execution.models import (
    MAX_PARAMETER_BYTES,
    AdapterResult,
    AdapterTimeout,
    ApiAdapter,
    ExecutionContext,
    ExecutionError,
    InvalidParameters,
    RedirectRejected,
    ResourceLimitExceeded,
    UnsafeTarget,
    UpstreamError,
    finite_json_bytes,
    validate_finite_json_mapping,
)

DEFAULT_MAX_RESPONSE_BYTES = 64 * 1024
HARD_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_LOCATION_BYTES = 2048
MAX_RETRIES = 3
MAX_REDIRECTS = 3
_PROVIDER_REF_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}\Z")
_PARAMETER_NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_UNSAFE_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.google.internal.",
        "instance-data.ec2.internal",
    }
)
_UNSAFE_IPS = frozenset(
    {
        "100.100.100.200",
        "169.254.169.254",
        "169.254.170.2",
        "fd00:ec2::254",
    }
)


Resolver = Callable[[str, int], Iterable[str]]


def _normalize_host(host: str) -> str:
    value = host.strip().rstrip(".").lower()
    if not value or any(character.isspace() for character in value):
        raise UnsafeTarget("host is invalid")
    try:
        return value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UnsafeTarget("host is invalid") from exc


def _default_resolver(host: str, port: int) -> list[str]:
    try:
        results = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UpstreamError("upstream DNS resolution failed") from exc
    return [str(item[4][0]) for item in results]


def _header(headers: Mapping[str, Any], name: str) -> str | None:
    expected = name.lower()
    for key, value in headers.items():
        if str(key).lower() == expected:
            return str(value)
    return None


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value}")


def _is_timeout(error: BaseException) -> bool:
    return isinstance(error, TimeoutError) or "timeout" in type(error).__name__.lower()


def _close_response(response: Any) -> None:
    """Close sync or async response objects without exposing close failures."""

    close = getattr(response, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass
        return

    aclose = getattr(response, "aclose", None)
    if not callable(aclose):
        return
    try:
        awaitable = aclose()
    except Exception:
        return
    if not inspect.isawaitable(awaitable):
        return

    def run_awaitable() -> None:
        try:
            async def await_close() -> None:
                await awaitable

            asyncio.run(await_close())
        except Exception:
            pass

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        run_awaitable()
        return

    thread = threading.Thread(target=run_awaitable, daemon=True)
    thread.start()
    thread.join()


def _safe_address(value: str) -> bool:
    try:
        address = ip_address(value)
    except ValueError:
        return False
    if str(address) in _UNSAFE_IPS:
        return False
    return bool(
        address.is_global
        and not address.is_loopback
        and not address.is_private
        and not address.is_link_local
        and not address.is_reserved
        and not address.is_multicast
        and not address.is_unspecified
    )


def _path_is_safe(path: str) -> bool:
    decoded = unquote(path)
    if "\\" in decoded or "\x00" in decoded:
        return False
    return all(part not in {".", ".."} for part in re.split(r"/", decoded))


class AllowlistedHttpAdapter(ApiAdapter):
    """A non-registered provider adapter with fixed target and bounded I/O."""

    adapter_name = "allowlisted-http"
    cacheable = True

    def __init__(
        self,
        endpoint: str,
        allowed_hosts: Iterable[str],
        provider_ref: str,
        *,
        allowed_params: Mapping[str, type[Any] | tuple[type[Any], ...]]
        | Iterable[str]
        | None = None,
        http_client: Any | None = None,
        client: Any | None = None,
        resolver: Resolver | None = None,
        dns_resolver: Resolver | None = None,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_retries: int = 1,
        allow_redirects: bool = False,
        max_redirects: int = MAX_REDIRECTS,
    ) -> None:
        if http_client is not None and client is not None:
            raise ValueError("provide either http_client or client, not both")
        if resolver is not None and dns_resolver is not None:
            raise ValueError("provide either resolver or dns_resolver, not both")
        if not isinstance(provider_ref, str) or _PROVIDER_REF_PATTERN.fullmatch(provider_ref) is None:
            raise ValueError("provider_ref must be a fixed internal reference")
        if isinstance(allowed_hosts, str):
            raise ValueError("allowed_hosts must be a finite collection")
        normalized_hosts = frozenset(_normalize_host(host) for host in allowed_hosts)
        if not normalized_hosts:
            raise ValueError("allowed_hosts must not be empty")
        parsed = self._parse_endpoint(endpoint)
        host = _normalize_host(parsed.hostname or "")
        if host not in normalized_hosts:
            raise UnsafeTarget("endpoint host is not allowlisted")
        try:
            explicit_port = parsed.port
        except ValueError as exc:
            raise UnsafeTarget("endpoint port is invalid") from exc
        port = 443 if explicit_port is None else explicit_port
        if not 1 <= port <= 65535:
            raise UnsafeTarget("endpoint port is invalid")
        path = parsed.path or "/"
        if not _path_is_safe(path) or "%" in path:
            raise UnsafeTarget("endpoint path is invalid")
        if explicit_port is None and port == 443:
            netloc = f"[{host}]" if ":" in host else host
        else:
            netloc = self._format_netloc(host, port)
        self.endpoint = urlunsplit(("https", netloc, path, "", ""))
        self._fixed_host = host
        self._fixed_port = port
        self._fixed_path = path
        self._allowed_hosts = normalized_hosts
        self.provider_ref = provider_ref
        self._http_client = http_client if http_client is not None else client
        self._resolver = resolver or dns_resolver or _default_resolver
        if not 1 <= max_response_bytes <= HARD_MAX_RESPONSE_BYTES:
            raise ValueError("max_response_bytes is outside the hard limit")
        if not isinstance(max_retries, int) or isinstance(max_retries, bool):
            raise ValueError("max_retries must be an integer")
        if not 0 <= max_retries <= MAX_RETRIES:
            raise ValueError("max_retries is outside the hard limit")
        if not isinstance(max_redirects, int) or isinstance(max_redirects, bool):
            raise ValueError("max_redirects must be an integer")
        if not 0 <= max_redirects <= MAX_REDIRECTS:
            raise ValueError("max_redirects is outside the hard limit")
        self.max_response_bytes = max_response_bytes
        self._max_retries = max_retries
        self._allow_redirects = allow_redirects
        self._max_redirects = max_redirects
        self._parameter_schema = self._normalize_parameter_schema(allowed_params)

    @staticmethod
    def _parse_endpoint(endpoint: str):
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("endpoint must be a fixed URL")
        try:
            parsed = urlsplit(endpoint)
        except ValueError as exc:
            raise UnsafeTarget("endpoint is invalid") from exc
        if parsed.scheme.lower() != "https":
            raise UnsafeTarget("endpoint must use HTTPS")
        if parsed.username is not None or parsed.password is not None:
            raise UnsafeTarget("endpoint credentials are not allowed")
        if parsed.hostname is None or parsed.fragment or parsed.query:
            raise UnsafeTarget("endpoint must have a fixed host and path")
        return parsed

    @staticmethod
    def _format_netloc(host: str, port: int) -> str:
        return f"[{host}]:{port}" if ":" in host else f"{host}:{port}"

    @staticmethod
    def _normalize_parameter_schema(
        allowed_params: Mapping[str, type[Any] | tuple[type[Any], ...]]
        | Iterable[str]
        | None,
    ) -> dict[str, type[Any] | tuple[type[Any], ...]]:
        if allowed_params is None:
            return {}
        if isinstance(allowed_params, Mapping):
            entries = allowed_params.items()
        else:
            entries = ((name, (str, int, float, bool)) for name in allowed_params)
        schema: dict[str, type[Any] | tuple[type[Any], ...]] = {}
        for name, expected in entries:
            if (
                not isinstance(name, str)
                or _PARAMETER_NAME_PATTERN.fullmatch(name) is None
                or name.lower() in {"url", "uri", "endpoint", "host", "port", "path"}
            ):
                raise ValueError("allowed parameter names must be fixed safe names")
            if not isinstance(expected, (type, tuple)):
                raise ValueError("allowed parameter types must be Python types")
            schema[name] = expected
        if len(schema) > 32:
            raise ValueError("too many allowed parameters")
        return schema

    def validate_params(self, params: Mapping[str, Any]) -> dict[str, Any]:
        values = validate_finite_json_mapping(params, max_bytes=MAX_PARAMETER_BYTES)
        if set(values) - set(self._parameter_schema):
            raise InvalidParameters("parameter is not declared by the provider adapter")
        for name, value in values.items():
            expected = self._parameter_schema[name]
            if not isinstance(value, expected) or (
                isinstance(value, bool)
                and expected not in (bool, (bool,))
            ):
                raise InvalidParameters(f"parameter {name} has the wrong type")
            if isinstance(value, (dict, list)):
                raise InvalidParameters("provider parameters must be scalar values")
        return values

    def _validate_target(self, target: str, *, initial: bool) -> tuple[str, ...]:
        def reject_redirect(message: str) -> None:
            if initial:
                raise UnsafeTarget(message)
            raise RedirectRejected(message)

        try:
            parsed = urlsplit(target)
            host = _normalize_host(parsed.hostname or "")
            explicit_port = parsed.port
            port = 443 if explicit_port is None else explicit_port
        except (ValueError, UnsafeTarget) as exc:
            if initial:
                raise UnsafeTarget("upstream target is invalid") from exc
            raise RedirectRejected("upstream redirect target is invalid") from exc
        if parsed.scheme.lower() != "https":
            reject_redirect("upstream target must use HTTPS")
        if parsed.username is not None or parsed.password is not None:
            reject_redirect("upstream target credentials are not allowed")
        if parsed.fragment or not _path_is_safe(parsed.path or "/"):
            reject_redirect("upstream target path is invalid")
        path = parsed.path or "/"
        if host not in self._allowed_hosts or host != self._fixed_host or port != self._fixed_port:
            reject_redirect("upstream target is not allowlisted")
        if path != self._fixed_path:
            reject_redirect("upstream target changed the fixed endpoint")
        try:
            literal_host = ip_address(host)
        except ValueError:
            literal_host = None
        if literal_host is not None and not _safe_address(str(literal_host)):
            raise UnsafeTarget("upstream literal address is not allowed")
        if host in _UNSAFE_HOSTS:
            if initial:
                raise UnsafeTarget("upstream hostname is not allowed")
            raise RedirectRejected("upstream redirect hostname is not allowed")
        try:
            addresses = list(self._resolver(host, port))
        except UnsafeTarget:
            raise
        except Exception as exc:
            raise UpstreamError("upstream DNS resolution failed") from exc
        if not addresses:
            raise UpstreamError("upstream DNS resolution returned no address")
        validated: list[str] = []
        for address in addresses:
            try:
                normalized_address = str(ip_address(address))
            except (TypeError, ValueError) as exc:
                raise UnsafeTarget("upstream address is invalid") from exc
            if not _safe_address(normalized_address):
                raise UnsafeTarget("upstream address is not allowed")
            if normalized_address not in validated:
                validated.append(normalized_address)
        return tuple(validated)

    def _request(
        self,
        url: str,
        *,
        resolved_addresses: tuple[str, ...],
        timeout_seconds: float,
    ) -> Any:
        if self._http_client is None:
            raise UpstreamError("HTTP client is not configured")
        request_pinned = getattr(self._http_client, "request_pinned", None)
        if callable(request_pinned):
            return request_pinned(
                "GET",
                url,
                resolved_addresses=resolved_addresses,
                timeout=timeout_seconds,
                stream=True,
                follow_redirects=False,
            )
        raise UpstreamError("HTTP client does not support pinned requests")

    def _read_body(self, response: Any) -> bytes:
        headers = getattr(response, "headers", {})
        if not isinstance(headers, Mapping):
            headers = {}
        content_length = _header(headers, "content-length")
        if content_length is not None:
            try:
                parsed_length = int(content_length)
                if parsed_length < 0 or parsed_length > self.max_response_bytes:
                    raise ResourceLimitExceeded("upstream response is too large")
            except ValueError as exc:
                raise UpstreamError("upstream response length is invalid") from exc

        iterator = getattr(response, "iter_bytes", None)
        if not callable(iterator):
            raise UpstreamError("upstream response does not support bounded streaming")
        chunks: list[bytes] = []
        total = 0
        source = iterator()
        for chunk in source:
            if not isinstance(chunk, (bytes, bytearray)):
                raise UpstreamError("upstream response body is invalid")
            total += len(chunk)
            if total > self.max_response_bytes:
                raise ResourceLimitExceeded("upstream response is too large")
            chunks.append(bytes(chunk))
        return b"".join(chunks)

    def _decode_json(self, headers: Mapping[str, Any], body: bytes) -> Any:
        if not isinstance(headers, Mapping):
            headers = {}
        content_type = _header(headers, "content-type")
        if content_type is not None and "json" not in content_type.lower():
            raise UpstreamError("upstream response is not JSON")
        try:
            value = json.loads(body.decode("utf-8"), parse_constant=_reject_json_constant)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise UpstreamError("upstream response is not valid JSON") from exc
        finite_json_bytes(value, max_bytes=self.max_response_bytes)
        return value

    def execute(
        self,
        context: ExecutionContext,
        params: Mapping[str, Any],
    ) -> AdapterResult:
        values = self.validate_params(params)
        query = urlencode(sorted(values.items()), doseq=False)
        target = self.endpoint if not query else f"{self.endpoint}?{query}"
        deadline = monotonic() + context.timeout_ms / 1000
        redirects = 0
        attempts = 0
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise AdapterTimeout("upstream request exceeded the execution context timeout")
            resolved_addresses = self._validate_target(target, initial=redirects == 0)
            try:
                response = self._request(
                    target,
                    resolved_addresses=resolved_addresses,
                    timeout_seconds=max(0.001, remaining),
                )
            except Exception as exc:
                if _is_timeout(exc):
                    if attempts < self._max_retries and monotonic() < deadline:
                        attempts += 1
                        continue
                    raise AdapterTimeout("upstream request timed out") from exc
                if isinstance(exc, UpstreamError):
                    raise
                if isinstance(exc, OSError) and attempts < self._max_retries:
                    attempts += 1
                    continue
                raise UpstreamError("upstream request failed") from exc

            try:
                status_code = getattr(response, "status_code", None)
                headers = getattr(response, "headers", {})
                body = self._read_body(response)
                if not isinstance(status_code, int):
                    raise UpstreamError("upstream response status is invalid")
                if 300 <= status_code < 400:
                    if not self._allow_redirects:
                        raise RedirectRejected("upstream redirects are disabled")
                    if redirects >= self._max_redirects:
                        raise RedirectRejected("upstream redirect limit exceeded")
                    location = _header(headers, "location") if isinstance(headers, Mapping) else None
                    if not location:
                        raise RedirectRejected("upstream redirect has no location")
                    if (
                        len(location.encode("utf-8")) > MAX_LOCATION_BYTES
                        or any(character in location for character in "\x00\r\n")
                    ):
                        raise RedirectRejected("upstream redirect location is too large")
                    target = urljoin(target, location)
                    redirects += 1
                    attempts = 0
                    continue
                if status_code < 200 or status_code >= 300:
                    if status_code >= 500 and attempts < self._max_retries and monotonic() < deadline:
                        attempts += 1
                        continue
                    raise UpstreamError("upstream returned an error status")
                data = self._decode_json(headers, body)
            except Exception as exc:
                if _is_timeout(exc):
                    if attempts < self._max_retries and monotonic() < deadline:
                        attempts += 1
                        continue
                    raise AdapterTimeout("upstream response timed out") from exc
                if isinstance(exc, ExecutionError):
                    raise
                raise UpstreamError("upstream response could not be read") from exc
            finally:
                _close_response(response)
            return AdapterResult(data=data, data_at=context.now)


__all__ = [
    "AllowlistedHttpAdapter",
    "DEFAULT_MAX_RESPONSE_BYTES",
    "HARD_MAX_RESPONSE_BYTES",
]
