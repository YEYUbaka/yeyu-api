from __future__ import annotations

from collections.abc import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models import ApiDefinition
from app.schemas.catalog import ApiDefinitionCreate
from app.services.catalog import ApiCatalogService, CatalogNotFoundError


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def catalog_factory(
    *,
    slug: str,
    visibility: str = "public",
    status: str = "healthy",
    category: str = "tools",
) -> ApiDefinition:
    return ApiDefinition(
        slug=slug,
        name=f"{slug} API",
        summary=f"Documentation for {slug}",
        category=category,
        method="GET",
        path=f"/v1/tools/{slug}",
        auth_type="api_key",
        parameters=[{"name": "format", "in": "query", "required": False}],
        response_schema={"type": "object"},
        error_codes=[{"status": 401, "code": "invalid_api_key"}],
        examples=[{"language": "curl", "code": f"curl /v1/tools/{slug}"}],
        visibility=visibility,
        status=status,
        is_free=True,
        source_label="Yeyu API",
        adapter_name="builtin-tools",
        provider_ref="provider:internal-tools",
        cache_rules={"ttl_seconds": 60, "stale_if_error": False},
    )


def test_search_returns_only_public_published_or_healthy_metadata(
    session: Session,
) -> None:
    session.add_all(
        [
            catalog_factory(slug="uuid", status="healthy"),
            catalog_factory(slug="published", status="published"),
            catalog_factory(slug="draft-api", visibility="draft", status="trial"),
            catalog_factory(slug="disabled-api", status="disabled"),
        ]
    )
    session.commit()

    page = ApiCatalogService(session).search(
        query="api", category=None, status=None, page=1, page_size=20
    )

    assert {item.slug for item in page.data} == {"uuid", "published"}
    assert {item.status for item in page.data} == {"healthy", "published"}
    assert page.count == 2


def test_search_supports_category_status_and_offset_pagination(
    session: Session,
) -> None:
    session.add_all(
        [
            catalog_factory(slug="time", category="tools", status="healthy"),
            catalog_factory(slug="uuid", category="tools", status="healthy"),
            catalog_factory(slug="weather", category="content", status="healthy"),
        ]
    )
    session.commit()

    page = ApiCatalogService(session).search(
        query=None, category="tools", status="healthy", page=2, page_size=1
    )

    assert page.count == 2
    assert page.page == 2
    assert page.page_size == 1
    assert [item.slug for item in page.data] == ["uuid"]


def test_get_public_returns_documentation_and_hides_provider_reference(
    session: Session,
) -> None:
    session.add(catalog_factory(slug="time"))
    session.commit()

    detail = ApiCatalogService(session).get_public("time")

    assert detail.auth.type == "api_key"
    assert detail.auth.header == "X-API-Key"
    assert detail.path == "/v1/tools/time"
    assert detail.parameters[0]["name"] == "format"
    assert detail.response_schema["type"] == "object"
    assert detail.errors[0]["code"] == "invalid_api_key"
    assert detail.examples[0]["language"] == "curl"
    assert detail.source == "Yeyu API"
    assert detail.cache_rules["ttl_seconds"] == 60
    assert "provider_ref" not in detail.model_dump()


def test_get_public_does_not_return_unpublished_definition(session: Session) -> None:
    session.add(catalog_factory(slug="draft-api", visibility="draft", status="trial"))
    session.commit()

    with pytest.raises(CatalogNotFoundError):
        ApiCatalogService(session).get_public("draft-api")


def test_catalog_schema_rejects_arbitrary_upstream_url() -> None:
    with pytest.raises(ValidationError):
        ApiDefinitionCreate(
            name="Unsafe API",
            category="tools",
            method="GET",
            path="https://attacker.example/forward",
            adapter_name="builtin-tools",
        )

    with pytest.raises(ValidationError):
        ApiDefinitionCreate(
            name="Unsafe API",
            category="tools",
            method="GET",
            path="/v1/tools/unsafe",
            adapter_name="builtin-tools",
            provider_ref="https://attacker.example/target",
        )

    with pytest.raises(ValidationError):
        ApiDefinitionCreate(
            name="Cookie API",
            category="tools",
            method="GET",
            path="/v1/tools/cookie",
            auth_type="cookie",
            adapter_name="builtin-tools",
        )

    with pytest.raises(ValidationError):
        ApiDefinitionCreate(
            name="Proxy API",
            category="tools",
            method="GET",
            path="/v1/tools/proxy",
            adapter_name="allowlisted-proxy",
        )

    for unsafe_path in ("//internal.example", "/v1/%2e%2e/admin"):
        with pytest.raises(ValidationError):
            ApiDefinitionCreate(
                name="Unsafe path API",
                category="tools",
                method="GET",
                path=unsafe_path,
                adapter_name="builtin-tools",
            )
