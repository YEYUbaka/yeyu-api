from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models import ApiDefinition
from app.schemas.catalog import ApiDefinitionCreate


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Synthetic candidate",
        "summary": "Synthetic candidate for boundary testing",
        "category": "tools",
        "path": "/v1/tools/time",
        "adapter_name": "builtin-tools",
        "provider_ref": "builtin-tools:time",
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


@pytest.mark.parametrize(
    "path",
    [
        "https://example.invalid/path",
        "//example.invalid/path",
        "/\\evil",
        "/%2f%2fevil",
        "/v1/tools/time?next=evil",
        "/v1/../admin",
    ],
)
def test_catalog_rejects_unsafe_internal_path(path: str) -> None:
    with pytest.raises(ValidationError):
        ApiDefinitionCreate(**_payload(path=path))


@pytest.mark.parametrize("status", ["unknown", "deprecated", ""])
def test_catalog_rejects_unknown_status(status: str) -> None:
    with pytest.raises(ValidationError):
        ApiDefinitionCreate(**_payload(status=status))


def _definition(**overrides: object) -> ApiDefinition:
    values: dict[str, object] = {
        "slug": "boundary-test",
        "name": "Boundary test",
        "summary": "Database boundary test",
        "category": "tools",
        "method": "GET",
        "path": "/v1/tools/time",
        "adapter_name": "builtin-tools",
        "provider_ref": "builtin-tools:time",
        "status": "trial",
    }
    values.update(overrides)
    return ApiDefinition(**values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"path": "https://example.invalid/path"},
        {"path": "//example.invalid/path"},
        {"path": "/\\evil"},
        {"path": "/%2f%2fevil"},
        {"status": "unknown"},
        {"adapter_name": "unknown-adapter"},
        {"provider_ref": "provider:unknown"},
    ],
)
def test_sqlite_equivalent_constraints_reject_unsafe_catalog_values(
    overrides: dict[str, object],
) -> None:
    engine = create_engine("sqlite://")
    ApiDefinition.__table__.create(engine)

    with Session(engine) as session:
        session.add(_definition(**overrides))
        with pytest.raises(IntegrityError):
            session.commit()
