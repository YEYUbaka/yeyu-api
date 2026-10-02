from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.catalog import ApiDefinitionCreate


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Synthetic candidate",
        "summary": "Synthetic candidate for boundary testing",
        "category": "tools",
        "path": "/v1/tools/time",
        "adapter_name": "builtin-tools",
        "provider_ref": "builtin.time",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "provider_ref",
    ["https://example.invalid", "//example.invalid/path", "example.invalid:443"],
)
def test_catalog_rejects_external_provider_reference(provider_ref: str) -> None:
    with pytest.raises(ValidationError):
        ApiDefinitionCreate(**_payload(provider_ref=provider_ref))


def test_catalog_rejects_unknown_adapter() -> None:
    with pytest.raises(ValidationError):
        ApiDefinitionCreate(**_payload(adapter_name="unknown-adapter"))
