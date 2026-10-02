from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.main import app
from app.models import ApiDefinition, User

CATALOG_PATH = f"{settings.API_V1_STR}/catalog"
ADMIN_CATALOG_PATH = f"{settings.API_V1_STR}/admin/catalog"
ADMIN_EMAIL = "catalog-admin@example.com"
ADMIN_PASSWORD = "CatalogAdminPassword123!"
USER_EMAIL = "catalog-user@example.com"
USER_PASSWORD = "CatalogUserPassword123!"


@pytest.fixture()
def catalog_environment() -> Iterator[tuple[TestClient, object]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_db() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with Session(engine) as session:
        session.add_all(
            [
                User(
                    email=ADMIN_EMAIL,
                    hashed_password=get_password_hash(ADMIN_PASSWORD),
                    is_active=True,
                    is_superuser=True,
                    email_verified=True,
                ),
                User(
                    email=USER_EMAIL,
                    hashed_password=get_password_hash(USER_PASSWORD),
                    is_active=True,
                    is_superuser=False,
                    email_verified=True,
                ),
            ]
        )
        session.commit()

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.pop(get_db, None)


def add_catalog(engine: object, **overrides: object) -> ApiDefinition:
    data: dict[str, object] = {
        "slug": "time",
        "name": "Time API",
        "summary": "Get the current time",
        "category": "tools",
        "method": "GET",
        "path": "/v1/tools/time",
        "auth_type": "api_key",
        "parameters": [],
        "response_schema": {"type": "object"},
        "error_codes": [],
        "examples": [],
        "visibility": "public",
        "status": "healthy",
        "is_free": True,
        "source_label": "Yeyu API",
        "adapter_name": "builtin-tools",
        "provider_ref": "provider:internal-tools",
        "cache_rules": {"ttl_seconds": 60},
    }
    data.update(overrides)
    definition = ApiDefinition(**data)
    with Session(engine) as session:  # type: ignore[arg-type]
        session.add(definition)
        session.commit()
    return definition


def access_token(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_public_catalog_hides_draft_and_disabled(
    catalog_environment: tuple[TestClient, object],
) -> None:
    client, engine = catalog_environment
    add_catalog(engine, slug="uuid", name="UUID API")
    add_catalog(
        engine,
        slug="draft-api",
        name="Draft API",
        visibility="draft",
        status="trial",
    )
    add_catalog(
        engine,
        slug="disabled-api",
        name="Disabled API",
        status="disabled",
    )

    response = client.get(
        CATALOG_PATH,
        params={"query": "api", "page": 1, "page_size": 20},
    )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["data"]] == [
        "uuid"
    ]


def test_public_catalog_search_matches_api_path(
    catalog_environment: tuple[TestClient, object],
) -> None:
    client, engine = catalog_environment
    add_catalog(
        engine,
        slug="time",
        name="Clock API",
        summary="Returns the current clock value",
        path="/v1/tools/time",
    )

    response = client.get(
        CATALOG_PATH,
        params={"query": "/v1/tools/time", "page": 1, "page_size": 20},
    )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["data"]] == ["time"]


def test_catalog_detail_contains_api_key_requirement(
    catalog_environment: tuple[TestClient, object],
) -> None:
    client, engine = catalog_environment
    add_catalog(
        engine,
        slug="time",
        parameters=[{"name": "safe", "description": "ok", "secret": "do-not-show"}],
        response_schema={"type": "object", "token": "do-not-show"},
        cache_rules={"ttl_seconds": 60, "api_key": "do-not-show"},
    )

    response = client.get(f"{CATALOG_PATH}/time")

    assert response.status_code == 200
    assert response.json()["auth"]["type"] == "api_key"
    assert response.json()["path"] == "/v1/tools/time"
    assert "provider_ref" not in response.json()
    assert "do-not-show" not in response.text


def test_catalog_slug_is_canonicalized_by_route_constraints(
    catalog_environment: tuple[TestClient, object],
) -> None:
    client, _ = catalog_environment
    response = client.get(f"{CATALOG_PATH}/Not-A-Slug")

    assert response.status_code == 422


def test_admin_catalog_requires_superuser_and_supports_lifecycle(
    catalog_environment: tuple[TestClient, object],
) -> None:
    client, _ = catalog_environment
    admin_headers = access_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_headers = access_token(client, USER_EMAIL, USER_PASSWORD)
    payload = {
        "name": "Time API",
        "summary": "Get the current time",
        "category": "tools",
        "method": "GET",
        "path": "/v1/tools/time",
        "auth_type": "api_key",
        "status": "healthy",
        "visibility": "public",
        "is_free": True,
        "source": "Yeyu API",
        "adapter_name": "builtin-tools",
        "provider_ref": "provider:internal-tools",
    }

    assert client.post(f"{ADMIN_CATALOG_PATH}/time", json=payload).status_code == 403
    response = client.post(
        f"{ADMIN_CATALOG_PATH}/time", headers=admin_headers, json=payload
    )
    assert response.status_code == 201
    assert response.json()["slug"] == "time"

    response = client.patch(
        f"{ADMIN_CATALOG_PATH}/time",
        headers=admin_headers,
        json={"summary": "Updated time documentation"},
    )
    assert response.status_code == 200
    assert response.json()["summary"] == "Updated time documentation"

    assert (
        client.delete(f"{ADMIN_CATALOG_PATH}/time", headers=user_headers).status_code
        == 403
    )
    assert (
        client.delete(f"{ADMIN_CATALOG_PATH}/time", headers=admin_headers).status_code
        == 204
    )
    assert client.get(f"{CATALOG_PATH}/time").status_code == 404


def test_admin_catalog_rejects_user_supplied_upstream_url(
    catalog_environment: tuple[TestClient, object],
) -> None:
    client, _ = catalog_environment
    admin_headers = access_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = client.post(
        f"{ADMIN_CATALOG_PATH}/unsafe",
        headers=admin_headers,
        json={
            "name": "Unsafe API",
            "category": "tools",
            "method": "GET",
            "path": "/v1/tools/unsafe",
            "adapter_name": "builtin-tools",
            "upstream_url": "https://attacker.example/forward",
        },
    )

    assert response.status_code == 422
