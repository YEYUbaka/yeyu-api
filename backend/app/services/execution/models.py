from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Any, ClassVar
from uuid import UUID

MAX_PARAMETER_BYTES = 4 * 1024
MAX_ADAPTER_RESPONSE_BYTES = 64 * 1024
MAX_TIMEOUT_MS = 120_000
MAX_JSON_DEPTH = 12
MAX_JSON_ITEMS = 256

_SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,99}\Z")
_UNSAFE_PARAMETER_KEYS = frozenset(
    {
        "base_url",
        "callback",
        "command",
        "directory",
        "endpoint",
        "file",
        "filename",
        "host",
        "hostname",
        "path",
        "port",
        "redirect",
        "scheme",
        "target",
        "uri",
        "url",
    }
)


class ExecutionError(RuntimeError):
    """Base class for errors that can be safely converted to API errors."""

    code: ClassVar[str] = "EXECUTION_ERROR"
    public_message: ClassVar[str] = "execution failed"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.public_message
        super().__init__(self.detail)


class InvalidParameters(ExecutionError):
    code = "INVALID_PARAMETERS"
    public_message = "parameters are invalid"


class ResourceLimitExceeded(InvalidParameters):
    code = "RESOURCE_LIMIT"
    public_message = "resource limit exceeded"


class AdapterTimeout(ExecutionError, TimeoutError):
    code = "UPSTREAM_TIMEOUT"
    public_message = "upstream request timed out"


class UpstreamError(ExecutionError):
    code = "UPSTREAM_ERROR"
    public_message = "upstream request failed"


class UnsafeTarget(UpstreamError):
    code = "SSRF_BLOCKED"
    public_message = "upstream target is not allowed"


class RedirectRejected(UnsafeTarget):
    code = "REDIRECT_REJECTED"
    public_message = "upstream redirect is not allowed"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)


def _validate_json_value(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ResourceLimitExceeded("JSON nesting is too deep")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidParameters("JSON numbers must be finite")
        return
    if isinstance(value, Mapping):
        if len(value) > MAX_JSON_ITEMS:
            raise ResourceLimitExceeded("JSON object is too large")
        for key, nested in value.items():
            if not isinstance(key, str):
                raise InvalidParameters("JSON object keys must be strings")
            if "\x00" in key:
                raise InvalidParameters("JSON object keys contain an invalid character")
            _validate_json_value(nested, depth=depth + 1)
        return
    if isinstance(value, list):
        if len(value) > MAX_JSON_ITEMS:
            raise ResourceLimitExceeded("JSON array is too large")
        for nested in value:
            _validate_json_value(nested, depth=depth + 1)
        return
    raise InvalidParameters("value is not JSON-compatible")


def _looks_like_untrusted_target(value: str) -> bool:
    stripped = value.strip()
    if not stripped or "\x00" in stripped:
        return True
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", stripped):
        return True
    if stripped.startswith(("/", "\\", "~/", "~\\")):
        return True
    if re.match(r"^[A-Za-z]:[\\/]", stripped):
        return True
    return any(part in {".", ".."} for part in re.split(r"[\\/]", stripped))


def _validate_parameter_targets(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key.lower() in _UNSAFE_PARAMETER_KEYS:
                raise InvalidParameters("URL and path parameters are not accepted")
            _validate_parameter_targets(nested)
    elif isinstance(value, list):
        for nested in value:
            _validate_parameter_targets(nested)
    elif isinstance(value, str) and _looks_like_untrusted_target(value):
        raise InvalidParameters("URL and path values are not accepted")


def validate_finite_json_mapping(
    params: Mapping[str, Any],
    *,
    max_bytes: int = MAX_PARAMETER_BYTES,
) -> dict[str, Any]:
    """Validate and copy a bounded parameter object at an untrusted boundary."""

    if not isinstance(params, Mapping):
        raise InvalidParameters("parameters must be a JSON object")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    copied: dict[str, Any] = {}
    for key, value in params.items():
        if not isinstance(key, str) or not key.strip():
            raise InvalidParameters("parameter names must be non-empty strings")
        normalized_key = key.strip()
        if normalized_key.lower() in _UNSAFE_PARAMETER_KEYS:
            raise InvalidParameters("URL and path parameters are not accepted")
        _validate_json_value(value)
        _validate_parameter_targets(value)
        copied[normalized_key] = value

    try:
        encoded = json.dumps(
            copied,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidParameters("parameters must be finite JSON") from exc
    if len(encoded) > max_bytes:
        raise ResourceLimitExceeded("parameter payload is too large")
    return copied


def finite_json_bytes(value: Any, *, max_bytes: int) -> bytes:
    """Serialize a response only after enforcing finite JSON and a byte cap."""

    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    _validate_json_value(value)
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise UpstreamError("adapter returned a non-JSON result") from exc
    if len(encoded) > max_bytes:
        raise ResourceLimitExceeded("adapter response is too large")
    return encoded


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    request_id: str
    api_slug: str
    api_key_id: UUID | str
    user_id: UUID | str
    client_ip: IPv4Address | IPv6Address | str
    timeout_ms: int
    now: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        if not isinstance(self.api_slug, str) or _SLUG_PATTERN.fullmatch(self.api_slug) is None:
            raise ValueError("api_slug must be a fixed lowercase slug")
        for name, value in (("api_key_id", self.api_key_id), ("user_id", self.user_id)):
            if not isinstance(value, (UUID, str)) or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"{name} must be a non-empty identifier")
        try:
            normalized_ip = ip_address(self.client_ip)
        except ValueError as exc:
            raise ValueError("client_ip must be a valid IP address") from exc
        if isinstance(self.timeout_ms, bool) or not isinstance(self.timeout_ms, int):
            raise ValueError("timeout_ms must be an integer")
        if not 1 <= self.timeout_ms <= MAX_TIMEOUT_MS:
            raise ValueError("timeout_ms is outside the allowed range")
        if not isinstance(self.now, datetime):
            raise ValueError("now must be a datetime")
        object.__setattr__(self, "client_ip", normalized_ip)
        object.__setattr__(self, "now", _utc(self.now))


class ApiAdapter:
    """Synchronous fixed adapter protocol used by the execution runner."""

    adapter_name: ClassVar[str] = ""
    cacheable: ClassVar[bool] = False
    max_response_bytes: ClassVar[int] = MAX_ADAPTER_RESPONSE_BYTES

    def execute(
        self,
        context: ExecutionContext,
        params: Mapping[str, Any],
    ) -> AdapterResult:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class AdapterResult:
    data: Any
    data_at: datetime | None = None
    meta: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        finite_json_bytes(self.data, max_bytes=MAX_ADAPTER_RESPONSE_BYTES)
        if not isinstance(self.meta, Mapping):
            raise InvalidParameters("adapter metadata must be a JSON object")
        finite_json_bytes(dict(self.meta), max_bytes=MAX_ADAPTER_RESPONSE_BYTES)
        if self.data_at is not None:
            object.__setattr__(self, "data_at", _utc(self.data_at))
        object.__setattr__(self, "meta", dict(self.meta))


@dataclass(frozen=True, slots=True)
class ApiResponse:
    success: bool
    data: Any | None
    error: dict[str, Any] | None
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "meta": dict(self.meta),
        }

    def model_dump(self) -> dict[str, Any]:
        return self.to_dict()

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)
