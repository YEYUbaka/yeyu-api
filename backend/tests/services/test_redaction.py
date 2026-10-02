from __future__ import annotations

from app.services.redaction import RedactionService


def test_sensitive_headers_are_redacted() -> None:
    safe = RedactionService.sanitize_headers(
        {
            "Authorization": "Bearer <NON_SECRET_AUTH_VALUE>",
            "X-API-Key": "<NON_SECRET_API_KEY>",
            "Cookie": "session=<NON_SECRET_COOKIE_VALUE>",
            "X-Request-ID": "req-test-001",
        }
    )

    assert safe["Authorization"] == "[REDACTED]"
    assert safe["X-API-Key"] == "[REDACTED]"
    assert safe["Cookie"] == "[REDACTED]"
    assert safe["X-Request-ID"] == "req-test-001"


def test_nested_metadata_is_redacted_and_bounded() -> None:
    safe = RedactionService.sanitize_metadata(
        {
            "safe": "kept",
            "password": "<NON_SECRET_PASSWORD_VALUE>",
            "credential": "<NON_SECRET_CREDENTIAL_VALUE>",
            "private_key": "<NON_SECRET_PRIVATE_KEY_VALUE>",
            "nested": {
                "access_token": "<NON_SECRET_ACCESS_VALUE>",
                "items": ["ok", "<NON_SECRET_LIST_VALUE>"],
            },
            "long": "x" * 20_000,
        }
    )

    assert safe["safe"] == "kept"
    assert safe["password"] == "[REDACTED]"
    assert safe["credential"] == "[REDACTED]"
    assert safe["private_key"] == "[REDACTED]"
    assert safe["nested"]["access_token"] == "[REDACTED]"  # type: ignore[index]
    assert safe["long"] == "[TRUNCATED]"


def test_oversized_mapping_is_bounded_before_recursive_walk() -> None:
    safe = RedactionService.sanitize_metadata(
        {f"key-{index}": {"nested": "value"} for index in range(10_000)}
    )

    assert safe == {"[TRUNCATED]": "[TRUNCATED]"}


def test_unknown_objects_are_not_stringified() -> None:
    class SensitiveObject:
        def __repr__(self) -> str:
            raise AssertionError("repr must not be called")

    safe = RedactionService.sanitize_metadata({"value": SensitiveObject()})

    assert safe["value"] == "[UNSUPPORTED_TYPE]"
