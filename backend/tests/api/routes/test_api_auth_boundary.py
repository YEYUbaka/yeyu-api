from __future__ import annotations

import secrets
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import get_api_key_principal, get_db
from app.core import security
from app.core.config import settings
from app.main import app
from app.models import User


@pytest.fixture()
def auth_boundary_environment() -> Iterator[tuple[TestClient, str, str, object]]:
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
        user = User(
            email=f"{secrets.token_hex(12)}@example.com",
            hashed_password=secrets.token_urlsafe(24),
            email_verified=True,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    probe_router = APIRouter(
        prefix="/task4-auth-probe", tags=["task4-auth-probe"]
    )

    @probe_router.get("")
    def probe(principal: object = Depends(get_api_key_principal)) -> dict[str, str]:
        return {"key_id": str(principal.key_id)}

    original_routes = list(app.router.routes)
    app.include_router(probe_router)

    from app.services.api_keys import ApiKeyService

    with Session(engine) as session:
        created = ApiKeyService(session).create(user_id, "probe")
        with TestClient(app) as client:
            yield client, created.secret, security.create_access_token(
                user_id, expires_delta=timedelta(minutes=15)
            ), session

    app.router.routes[:] = original_routes
    app.openapi_schema = None
    app.dependency_overrides.pop(get_db, None)


def test_management_cookie_cannot_authenticate_public_api(
    auth_boundary_environment: tuple[TestClient, str, str, object],
) -> None:
    client, _secret, management_token, _session = auth_boundary_environment
    response = client.get(
        "/task4-auth-probe",
        cookies={settings.AUTH_COOKIE_NAME: management_token},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "API_KEY_REQUIRED"


def test_x_api_key_authenticates_public_api_and_revocation_blocks_it(
    auth_boundary_environment: tuple[TestClient, str, str, object],
) -> None:
    client, secret, _management_token, session = auth_boundary_environment
    response = client.get("/task4-auth-probe", headers={"X-API-Key": secret})

    assert response.status_code == 200
    assert response.json()["key_id"]

    from app.services.api_keys import ApiKeyService

    principal = ApiKeyService(session).authenticate(secret)
    assert principal is not None
    ApiKeyService(session).revoke(principal.key_id, principal.user_id)

    revoked_response = client.get(
        "/task4-auth-probe",
        headers={"X-API-Key": secret},
    )
    assert revoked_response.status_code == 401
    assert revoked_response.json()["error"]["code"] == "API_KEY_REVOKED"


def test_missing_and_invalid_api_key_have_fixed_error_shape(
    auth_boundary_environment: tuple[TestClient, str, str, object],
) -> None:
    client, _secret, _management_token, _session = auth_boundary_environment

    for headers, code in (
        ({}, "API_KEY_REQUIRED"),
        ({"X-API-Key": secrets.token_urlsafe(32)}, "API_KEY_INVALID"),
    ):
        response = client.get("/task4-auth-probe", headers=headers)
        assert response.status_code == 401
        assert set(response.json()) == {"error"}
        assert set(response.json()["error"]) == {"code", "message", "request_id"}
        assert response.json()["error"]["code"] == code
