from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import ClassVar

_REDACTED = "[REDACTED]"
_TRUNCATED = "[TRUNCATED]"
_UNSUPPORTED_TYPE = "[UNSUPPORTED_TYPE]"
_UNSUPPORTED_KEY = "[UNSUPPORTED_KEY]"


class RedactionService:
    """Copy untrusted metadata into a small, JSON-safe representation."""

    MAX_DEPTH: ClassVar[int] = 8
    MAX_MAPPING_ITEMS: ClassVar[int] = 128
    MAX_STRING_LENGTH: ClassVar[int] = 4 * 1024
    MAX_LIST_ITEMS: ClassVar[int] = 100
    MAX_JSON_BYTES: ClassVar[int] = 16 * 1024

    _SENSITIVE_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "authorization",
            "xapikey",
            "apikey",
            "cookie",
            "setcookie",
            "password",
            "secret",
            "credential",
            "privatekey",
            "clientcredential",
            "keyhash",
            "clientsecret",
            "accesstoken",
            "refreshtoken",
            "oauthtoken",
        }
    )
    _KEY_SEPARATOR_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"[-_]")

    @classmethod
    def sanitize_headers(cls, headers: Mapping[str, str]) -> dict[str, str]:
        """Return headers without credentials or unbounded values."""

        if not isinstance(headers, Mapping):
            raise TypeError("headers must be a mapping")

        sanitized = cls._sanitize_value(headers, depth=0, active_ids=set())
        if not isinstance(sanitized, dict):
            return {}

        header_values = {
            key: value if isinstance(value, str) else _UNSUPPORTED_TYPE
            for key, value in sanitized.items()
        }
        bounded = cls._fit_json_limit(header_values)
        if not isinstance(bounded, dict):
            return {}
        return {
            key: value if isinstance(value, str) else _UNSUPPORTED_TYPE
            for key, value in bounded.items()
        }

    @classmethod
    def sanitize_metadata(
        cls, metadata: Mapping[str, object]
    ) -> dict[str, object]:
        """Recursively redact and bound metadata before it reaches JSON storage."""

        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        sanitized = cls._sanitize_value(metadata, depth=0, active_ids=set())
        if not isinstance(sanitized, dict):
            return {_TRUNCATED: _TRUNCATED}

        bounded = cls._fit_json_limit(sanitized)
        if not isinstance(bounded, dict):
            return {_TRUNCATED: _TRUNCATED}
        return bounded

    @classmethod
    def _sanitize_value(
        cls,
        value: object,
        *,
        depth: int,
        active_ids: set[int],
    ) -> object:
        if value is None or isinstance(value, (bool, int)):
            return value
        if isinstance(value, float):
            return value if math.isfinite(value) else _UNSUPPORTED_TYPE
        if isinstance(value, str):
            return value if len(value) <= cls.MAX_STRING_LENGTH else _TRUNCATED

        if isinstance(value, Mapping):
            if depth >= cls.MAX_DEPTH:
                return _TRUNCATED
            try:
                if len(value) > cls.MAX_MAPPING_ITEMS:
                    return _TRUNCATED
            except Exception:
                return _UNSUPPORTED_TYPE
            value_id = id(value)
            if value_id in active_ids:
                return _TRUNCATED
            active_ids.add(value_id)
            try:
                result: dict[str, object] = {}
                try:
                    items = value.items()
                    for raw_key, raw_value in items:
                        safe_key = cls._safe_key(raw_key)
                        if cls._is_sensitive_key(raw_key):
                            result[safe_key] = _REDACTED
                        else:
                            result[safe_key] = cls._sanitize_value(
                                raw_value,
                                depth=depth + 1,
                                active_ids=active_ids,
                            )
                except Exception:
                    return _UNSUPPORTED_TYPE
                return result
            finally:
                active_ids.remove(value_id)

        if isinstance(value, list):
            if depth >= cls.MAX_DEPTH:
                return _TRUNCATED
            try:
                if len(value) > cls.MAX_LIST_ITEMS:
                    return _TRUNCATED
            except Exception:
                return _UNSUPPORTED_TYPE

            value_id = id(value)
            if value_id in active_ids:
                return _TRUNCATED
            active_ids.add(value_id)
            try:
                return [
                    cls._sanitize_value(
                        item,
                        depth=depth + 1,
                        active_ids=active_ids,
                    )
                    for item in value
                ]
            except Exception:
                return _UNSUPPORTED_TYPE
            finally:
                active_ids.remove(value_id)

        return _UNSUPPORTED_TYPE

    @classmethod
    def _safe_key(cls, key: object) -> str:
        if not isinstance(key, str):
            return _UNSUPPORTED_KEY
        return key if len(key) <= cls.MAX_STRING_LENGTH else _TRUNCATED

    @classmethod
    def _is_sensitive_key(cls, key: object) -> bool:
        if not isinstance(key, str):
            return False
        normalized = cls._KEY_SEPARATOR_PATTERN.sub("", key.casefold())
        return normalized in cls._SENSITIVE_KEYS or any(
            marker in normalized
            for marker in (
                "authorization",
                "apikey",
                "cookie",
                "password",
                "secret",
                "token",
            )
        )

    @classmethod
    def _fit_json_limit(cls, value: object) -> object:
        if cls._fits_json_limit(value):
            return value
        return cls._shrink_for_json(value)

    @classmethod
    def _shrink_for_json(cls, value: object) -> object:
        if cls._fits_json_limit(value):
            return value

        if isinstance(value, Mapping):
            result: dict[str, object] = {}
            for key, nested in value.items():
                candidate = dict(result)
                candidate[key] = cls._shrink_for_json(nested)
                if cls._fits_json_limit(candidate):
                    result[key] = candidate[key]
                    continue

                marker_candidate = dict(result)
                marker_candidate[_TRUNCATED] = _TRUNCATED
                if cls._fits_json_limit(marker_candidate):
                    return marker_candidate
                return {_TRUNCATED: _TRUNCATED}
            return result if cls._fits_json_limit(result) else {_TRUNCATED: _TRUNCATED}

        if isinstance(value, list):
            result: list[object] = []
            for nested in value:
                candidate = [*result, cls._shrink_for_json(nested)]
                if cls._fits_json_limit(candidate):
                    result.append(candidate[-1])
                    continue

                marker_candidate = [*result, _TRUNCATED]
                if cls._fits_json_limit(marker_candidate):
                    return marker_candidate
                return [_TRUNCATED]
            return result if cls._fits_json_limit(result) else [_TRUNCATED]

        return _TRUNCATED

    @classmethod
    def _fits_json_limit(cls, value: object) -> bool:
        try:
            encoded = json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError, OverflowError):
            return False
        return len(encoded) <= cls.MAX_JSON_BYTES
