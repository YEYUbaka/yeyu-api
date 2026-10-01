from __future__ import annotations

import secrets
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import get_db
from app.core import security
from app.core.config import settings
from app.main import app
from app.models import ApiDefinition, User

API_KEYS_PATH = f"{settings.API_V1_STR}/api-keys"
POLICIES_PATH = f"{settings.API_V1_STR}/admin/policies"


@pytest.fixture()
def api_key_environment() -> Iterator[tuple[TestClient, object]]:
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
        verified = User(
            email=f"{secrets.token_hex(12)}@example.com",
            hashed_password=secrets.token_urlsafe(24),
            email_verified=True,
            is_active=True,
        )
        unverified = User(
            email=f"{secrets.token_hex(12)}@example.com",
            hashed_password=secrets.token_urlsafe(24),
            email_verified=False,
            is_active=True,
        )
        admin = User(
            email=f"{secrets.token_hex(12)}@example.com",
            hashed_password=secrets.token_urlsafe(24),
            email_verified=True,
            is_active=True,
            is_superuser=True,
        )
        api = ApiDefinition(
            slug="uuid",
            name="UUID",
            summary="UUID",
            category="tools",
            method="GET",
            path="/v1/tools/uuid",
            adapter_name="builtin-tools",
        )
        session.add_all([verified, unverified, admin, api])
        session.commit()
        session.refresh(verified)
        session.refresh(unverified)
        session.refresh(admin)
        ids = {"verified": verified.id, "unverified": unverified.id, "admin": admin.id}

    with TestClient(app) as client:
        yield client, (engine, ids)

    app.dependency_overrides.pop(get_db, None)


def _management_cookie(user_id: object) -> dict[str, str]:
    token = security.create_access_token(
        user_id,
        expires_delta=__import__("datetime").timedelta(minutes=15),
    )
    return {settings.AUTH_COOKIE_NAME: token}


def _bearer(user_id: object) -> dict[str, str]:
    token = security.create_access_token(
        user_id,
        expires_delta=__import__("datetime").timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}


def test_created_secret_is_not_returned_by_list(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    cookie = _management_cookie(ids["verified"])

    created_response = client.post(
        API_KEYS_PATH,
        cookies=cookie,
        json={"label": "local"},
    )
    assert created_response.status_code == 201
    created = created_response.json()["data"]
    assert created["secret"]
    assert created["prefix"]

    listed_response = client.get(API_KEYS_PATH, cookies=cookie)
    assert listed_response.status_code == 200
    listed = listed_response.json()["data"]
    assert listed
    assert all("secret" not in item for item in listed)
    assert created["secret"] not in listed_response.text


def test_unverified_user_cannot_create_api_key_with_structured_error(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    response = client.post(
        API_KEYS_PATH,
        cookies=_management_cookie(ids["unverified"]),
        json={"label": "blocked"},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "ACCOUNT_UNVERIFIED"
    assert body["error"]["request_id"]


def test_key_revoke_and_rotate_are_user_owned(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    cookie = _management_cookie(ids["verified"])
    created = client.post(API_KEYS_PATH, cookies=cookie, json={}).json()["data"]

    rotated = client.post(
        f"{API_KEYS_PATH}/{created['id']}/rotate",
        cookies=cookie,
    )
    assert rotated.status_code == 201
    replacement = rotated.json()["data"]
    assert replacement["id"] != created["id"]
    assert replacement["secret"] != created["secret"]

    revoked = client.post(
        f"{API_KEYS_PATH}/{replacement['id']}/revoke",
        cookies=cookie,
    )
    assert revoked.status_code in {200, 204}


def test_normal_user_cannot_read_or_update_admin_policy(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    response = client.put(
        f"{POLICIES_PATH}/uuid",
        headers=_bearer(ids["unverified"]),
        json={"enabled": True},
    )

    assert response.status_code == 403


def test_superuser_can_update_api_policy(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    response = client.put(
        f"{POLICIES_PATH}/uuid",
        headers=_bearer(ids["admin"]),
        json={"minute_limit": 5, "allowed_ips": ["192.0.2.0/24"]},
    )

    assert response.status_code == 200
    assert response.json()["api_slug"] == "uuid"
    assert response.json()["minute_limit"] == 5


def test_policy_allowed_ips_are_normalized_at_input_boundary(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    response = client.put(
        f"{POLICIES_PATH}/uuid",
        headers=_bearer(ids["admin"]),
        json={"allowed_ips": [" 192.0.2.10/24 ", "2001:db8::1"]},
    )

    assert response.status_code == 200
    assert response.json()["allowed_ips"] == ["192.0.2.0/24", "2001:db8::1/128"]


@pytest.mark.parametrize("allowed_ips", [["not-an-ip"], ["192.0.2.999"], [""]])
def test_policy_allowed_ips_reject_invalid_values(
    api_key_environment: tuple[TestClient, object],
    allowed_ips: list[str],
) -> None:
    client, (_engine, ids) = api_key_environment
    response = client.put(
        f"{POLICIES_PATH}/uuid",
        headers=_bearer(ids["admin"]),
        json={"allowed_ips": allowed_ips},
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_api_key_routes_do_not_accept_cookie_as_x_api_key(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    response = client.get(
        f"{settings.API_V1_STR}/api-keys/public-auth-check",
        cookies=_management_cookie(ids["verified"]),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "API_KEY_REQUIRED"
