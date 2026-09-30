from __future__ import annotations

import secrets
from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import User


@pytest.fixture
def identity_client() -> Generator[tuple[TestClient, Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    def override_get_db() -> Generator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, session
    app.dependency_overrides.pop(get_db, None)
    session.close()


def test_signup_creates_unverified_user(
    identity_client: tuple[TestClient, Session],
) -> None:
    client, session = identity_client
    email = f"{secrets.token_hex(12)}@example.com"
    response = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={
            "email": email,
            "password": secrets.token_urlsafe(24),
            "full_name": "Test User",
        },
    )

    assert response.status_code == 200
    user = session.exec(select(User).where(User.email == email)).one()
    assert user.email_verified is False
    assert response.json()["email_verified"] is False


def test_unknown_password_reset_is_non_enumerating(
    monkeypatch: pytest.MonkeyPatch,
    identity_client: tuple[TestClient, Session],
) -> None:
    client, session = identity_client
    monkeypatch.setattr(
        "app.api.routes.login.RedisRateLimiter.check",
        lambda _self, **_kwargs: None,
    )
    known_email = f"{secrets.token_hex(12)}@example.com"
    unknown_email = f"{secrets.token_hex(12)}@example.com"
    user = User(
        email=known_email,
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
    )
    session.add(user)
    session.commit()
    monkeypatch.setattr(
        "app.api.routes.login.PasswordResetService.request",
        lambda self, user_id: None,
    )

    known = client.post(
        f"{settings.API_V1_STR}/auth/request-password-reset",
        json={"email": known_email},
    )
    unknown = client.post(
        f"{settings.API_V1_STR}/auth/request-password-reset",
        json={"email": unknown_email},
    )

    assert known.status_code == unknown.status_code == 202
    assert known.json()["message"] == unknown.json()["message"]


def test_invalid_email_verification_is_generic(
    identity_client: tuple[TestClient, Session],
) -> None:
    client, _ = identity_client
    response = client.get(
        f"{settings.API_V1_STR}/auth/verify-email",
        params={"token": secrets.token_urlsafe(32)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification token"


def test_cookie_session_authenticates_protected_route(
    identity_client: tuple[TestClient, Session],
) -> None:
    client, session = identity_client
    user = User(
        email=f"{secrets.token_hex(12)}@example.com",
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session_token = create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers={"Cookie": f"{settings.AUTH_COOKIE_NAME}={session_token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_logout_clears_http_only_session_cookie(
    identity_client: tuple[TestClient, Session],
) -> None:
    client, _ = identity_client

    response = client.post(f"{settings.API_V1_STR}/auth/logout")

    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"].lower()
    assert f"{settings.AUTH_COOKIE_NAME.lower()}=" in set_cookie
    assert "max-age=0" in set_cookie
    assert "httponly" in set_cookie


def test_password_reset_fails_closed_when_redis_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    identity_client: tuple[TestClient, Session],
) -> None:
    from app.services.identity import RateLimitUnavailable

    client, _ = identity_client

    def fail_closed(_self: object, **_kwargs: object) -> None:
        raise RateLimitUnavailable

    monkeypatch.setattr("app.api.routes.login.RedisRateLimiter.check", fail_closed)
    response = client.post(
        f"{settings.API_V1_STR}/auth/request-password-reset",
        json={"email": f"{secrets.token_hex(12)}@example.com"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Identity service temporarily unavailable"


def test_admin_email_change_resets_verification_and_requests_email(
    monkeypatch: pytest.MonkeyPatch,
    identity_client: tuple[TestClient, Session],
) -> None:
    client, session = identity_client
    admin = User(
        email=f"{secrets.token_hex(12)}@example.com",
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        is_superuser=True,
        email_verified=True,
    )
    user = User(
        email=f"{secrets.token_hex(12)}@example.com",
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        email_verified=True,
    )
    session.add(admin)
    session.add(user)
    session.commit()
    session.refresh(admin)
    session.refresh(user)
    requested = []
    monkeypatch.setattr(
        "app.api.routes.users.EmailVerificationService.request",
        lambda self, user_id: requested.append(user_id),
    )
    new_email = f"{secrets.token_hex(12)}@example.com"
    admin_token = create_access_token(
        admin.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    response = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": new_email},
    )

    assert response.status_code == 200
    assert response.json()["email_verified"] is False
    assert requested == [user.id]
