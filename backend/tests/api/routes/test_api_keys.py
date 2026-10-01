from __future__ import annotations

import secrets
from collections.abc import Iterator
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import get_current_user, get_db
from app.core import security
from app.core.config import settings
from app.main import app
from app.models import ApiDefinition, User
from app.services.api_keys import ApiKeyService

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
        inactive = User(
            email=f"{secrets.token_hex(12)}@example.com",
            hashed_password=secrets.token_urlsafe(24),
            email_verified=True,
            is_active=False,
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
        session.add_all([verified, unverified, inactive, admin, api])
        session.commit()
        session.refresh(verified)
        session.refresh(unverified)
        session.refresh(inactive)
        session.refresh(admin)
        ids = {
            "verified": verified.id,
            "unverified": unverified.id,
            "inactive": inactive.id,
            "admin": admin.id,
        }

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


def test_inactive_user_is_rejected_by_management_dependency(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    response = client.post(
        API_KEYS_PATH,
        cookies=_management_cookie(ids["inactive"]),
        json={"label": "blocked"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


def test_key_management_guard_rejects_an_inactive_user() -> None:
    from app.api.deps import ApiError
    from app.api.routes.api_keys import _ensure_user_can_manage_keys

    inactive = User(
        email="inactive-guard@example.com",
        hashed_password="inactive-guard-password",
        email_verified=True,
        is_active=False,
    )
    with pytest.raises(ApiError) as exc_info:
        _ensure_user_can_manage_keys(inactive)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCOUNT_SUSPENDED"


def test_management_dependency_rejects_malformed_and_unknown_users(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, _ids) = api_key_environment
    tokens = (
        None,
        "not-a-jwt",
        jwt.encode({}, settings.SECRET_KEY, algorithm=security.ALGORITHM),
        security.create_access_token(
            "not-a-uuid",
            expires_delta=__import__("datetime").timedelta(minutes=15),
        ),
        security.create_access_token(
            uuid4(),
            expires_delta=__import__("datetime").timedelta(minutes=15),
        ),
    )
    expected = (
        (403, "Could not validate credentials"),
        (403, "Could not validate credentials"),
        (403, "Could not validate credentials"),
        (403, "Could not validate credentials"),
        (404, "User not found"),
    )

    for token, (status_code, detail) in zip(tokens, expected, strict=True):
        cookies = {} if token is None else {settings.AUTH_COOKIE_NAME: token}
        response = client.get(API_KEYS_PATH, cookies=cookies)
        assert response.status_code == status_code
        assert response.json()["detail"] == detail


@pytest.mark.parametrize(
    ("changed_field", "error_code"),
    (("email_verified", "ACCOUNT_UNVERIFIED"), ("is_active", "ACCOUNT_SUSPENDED")),
)
def test_create_maps_service_eligibility_errors_after_management_check(
    api_key_environment: tuple[TestClient, object],
    monkeypatch: pytest.MonkeyPatch,
    changed_field: str,
    error_code: str,
) -> None:
    client, (engine, ids) = api_key_environment
    with Session(engine) as session:
        stored_user = session.get(User, ids["verified"])
        assert stored_user is not None
        setattr(stored_user, changed_field, False)
        session.add(stored_user)
        session.commit()

    stale_current_user = User(
        id=ids["verified"],
        email="stale-current-user@example.com",
        hashed_password="stale-current-user-password",
        email_verified=True,
        is_active=True,
    )
    monkeypatch.setitem(
        app.dependency_overrides,
        get_current_user,
        lambda: stale_current_user,
    )

    response = client.post(API_KEYS_PATH, json={"label": "race"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == error_code


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
    assert revoked.status_code == 204


@pytest.mark.parametrize("operation", ["revoke", "rotate"])
def test_key_routes_reject_missing_and_foreign_keys(
    api_key_environment: tuple[TestClient, object],
    operation: str,
) -> None:
    client, (_engine, ids) = api_key_environment
    owner_cookie = _management_cookie(ids["verified"])
    created = client.post(API_KEYS_PATH, cookies=owner_cookie, json={}).json()["data"]

    missing_response = client.post(
        f"{API_KEYS_PATH}/{uuid4()}/{operation}",
        cookies=owner_cookie,
    )
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "API key not found"

    foreign_response = client.post(
        f"{API_KEYS_PATH}/{created['id']}/{operation}",
        cookies=_management_cookie(ids["admin"]),
    )
    assert foreign_response.status_code == 403
    assert foreign_response.json()["detail"] == "API key is not owned by user"


def test_repeated_revoke_is_idempotent(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    cookie = _management_cookie(ids["verified"])
    created = client.post(API_KEYS_PATH, cookies=cookie, json={}).json()["data"]

    first_response = client.post(
        f"{API_KEYS_PATH}/{created['id']}/revoke",
        cookies=cookie,
    )
    assert first_response.status_code == 204

    repeated_response = client.post(
        f"{API_KEYS_PATH}/{created['id']}/revoke",
        cookies=cookie,
    )
    assert repeated_response.status_code == 204


def test_rotate_rejects_an_already_revoked_key(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    cookie = _management_cookie(ids["verified"])
    created = client.post(API_KEYS_PATH, cookies=cookie, json={}).json()["data"]
    revoked = client.post(
        f"{API_KEYS_PATH}/{created['id']}/revoke",
        cookies=cookie,
    )
    assert revoked.status_code == 204

    response = client.post(
        f"{API_KEYS_PATH}/{created['id']}/rotate",
        cookies=cookie,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "API_KEY_REVOKED"


def test_unmapped_key_lifecycle_errors_are_reraised() -> None:
    from app.api.routes.api_keys import _raise_lifecycle_error

    original = RuntimeError("unmapped lifecycle failure")
    with pytest.raises(RuntimeError) as exc_info:
        _raise_lifecycle_error(original)

    assert exc_info.value is original


def test_public_auth_check_accepts_an_active_api_key(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    with Session(_engine) as session:
        created = ApiKeyService(session).create(ids["verified"], "public-check")

    response = client.get(
        f"{settings.API_V1_STR}/api-keys/public-auth-check",
        headers={"X-API-Key": created.secret},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "key_id": str(created.id),
        "prefix": created.prefix,
    }


@pytest.mark.parametrize(
    ("changed_field", "error_code"),
    (("email_verified", "ACCOUNT_UNVERIFIED"), ("is_active", "ACCOUNT_SUSPENDED")),
)
def test_public_auth_check_rejects_ineligible_key_accounts(
    api_key_environment: tuple[TestClient, object],
    changed_field: str,
    error_code: str,
) -> None:
    client, (engine, ids) = api_key_environment
    with Session(engine) as session:
        created = ApiKeyService(session).create(ids["verified"], "eligibility")
        stored_user = session.get(User, ids["verified"])
        assert stored_user is not None
        setattr(stored_user, changed_field, False)
        session.add(stored_user)
        session.commit()

    response = client.get(
        f"{settings.API_V1_STR}/api-keys/public-auth-check",
        headers={"X-API-Key": created.secret},
    )

    assert response.status_code == 403
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == error_code


def test_normal_user_cannot_read_or_update_admin_policy(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    read_response = client.get(
        f"{POLICIES_PATH}/uuid",
        headers=_bearer(ids["unverified"]),
    )
    assert read_response.status_code == 403

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


def test_superuser_can_read_default_policy_and_unknown_policy_is_not_found(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    default_response = client.get(
        f"{POLICIES_PATH}/uuid",
        headers=_bearer(ids["admin"]),
    )

    assert default_response.status_code == 200
    assert default_response.json()["api_slug"] == "uuid"
    assert default_response.json()["allowed_ips"] == []

    missing_response = client.get(
        f"{POLICIES_PATH}/missing-api",
        headers=_bearer(ids["admin"]),
    )
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "API policy target not found"


def test_superuser_cannot_update_unknown_policy_target(
    api_key_environment: tuple[TestClient, object],
) -> None:
    client, (_engine, ids) = api_key_environment
    response = client.put(
        f"{POLICIES_PATH}/missing-api",
        headers=_bearer(ids["admin"]),
        json={"enabled": True},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "API policy target not found"


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
