from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.execution.models import (
    MAX_PARAMETER_BYTES,
    AdapterResult,
    ApiAdapter,
    ExecutionContext,
    InvalidParameters,
    validate_finite_json_mapping,
)

_TIMEZONE_PATTERN = re.compile(
    r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*\Z"
)


class TimeAdapter(ApiAdapter):
    adapter_name = "builtin-tools"
    cacheable = False
    max_response_bytes = 1024

    def execute(
        self,
        context: ExecutionContext,
        params: Mapping[str, Any],
    ) -> AdapterResult:
        values = validate_finite_json_mapping(params, max_bytes=MAX_PARAMETER_BYTES)
        unknown = set(values) - {"timezone"}
        if unknown:
            raise InvalidParameters("time only accepts the timezone parameter")
        timezone_name = values.get("timezone", "UTC")
        if (
            not isinstance(timezone_name, str)
            or len(timezone_name) > 64
            or _TIMEZONE_PATTERN.fullmatch(timezone_name) is None
            or ".." in timezone_name
        ):
            raise InvalidParameters("timezone must be a valid IANA timezone name")
        try:
            timezone = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise InvalidParameters("timezone is not available") from exc

        utc_time = context.now.astimezone(UTC)
        local_time = utc_time.astimezone(timezone)
        return AdapterResult(
            data={
                "utc": utc_time.isoformat().replace("+00:00", "Z"),
                "unix_timestamp": utc_time.timestamp(),
                "timezone": timezone_name,
                "local": local_time.isoformat(),
            },
            data_at=utc_time,
        )


class UuidAdapter(ApiAdapter):
    adapter_name = "builtin-tools"
    cacheable = False
    max_response_bytes = 256

    def execute(
        self,
        context: ExecutionContext,
        params: Mapping[str, Any],
    ) -> AdapterResult:
        values = validate_finite_json_mapping(params, max_bytes=MAX_PARAMETER_BYTES)
        if values:
            raise InvalidParameters("uuid does not accept parameters")
        value = str(uuid4())
        return AdapterResult(
            data={"uuid": value, "version": 4},
            data_at=context.now,
        )


__all__ = ["TimeAdapter", "UuidAdapter"]
