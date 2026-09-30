from __future__ import annotations

import secrets
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import get_password_hash
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
