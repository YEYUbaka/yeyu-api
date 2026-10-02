from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import security
from app.models import UserCreate
from tests.utils.utils import random_email, random_lower_string

ADMIN_REQUESTS: tuple[tuple[str, str, dict[str, Any] | None], ...] = (
    ("GET", "/api/v1/admin/catalog", None),
    ("GET", "/api/v1/admin/audit", None),
    ("GET", "/api/v1/admin/health", None),
    ("GET", "/api/v1/admin/policies/time", None),
    (
        "POST",
        "/api/v1/admin/catalog/non-secret-test-definition",
        {
            "name": "Non-secret test definition",
            "summary": "A bounded authorization test payload.",
            "category": "tools",
            "method": "GET",
            "path": "/v1/tools/time",
            "adapter_name": "builtin-tools",
            "provider_ref": "builtin-tools:time",
            "status": "trial",
        },
    ),
    (
        "PATCH",
        "/api/v1/admin/catalog/time",
        {"summary": "Non-secret authorization test update."},
    ),
    ("DELETE", "/api/v1/admin/catalog/time", None),
    (
        "PUT",
        "/api/v1/admin/policies/time",
        {"minute_limit": 60, "daily_limit": 1000},
    ),
)


def _request(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    headers: dict[str, str] | None = None,
):
    return client.request(method, path, headers=headers, json=payload)


@pytest.mark.parametrize("method,path,payload", ADMIN_REQUESTS)
def test_normal_user_cannot_read_or_mutate_admin_resources(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    response = _request(
        client, method, path, payload, headers=normal_user_token_headers
    )

    assert response.status_code == 403


@pytest.mark.parametrize("method,path,payload", ADMIN_REQUESTS)
def test_anonymous_cannot_read_or_mutate_admin_resources(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    response = _request(client, method, path, payload)

    assert response.status_code == 403


@pytest.mark.parametrize("method,path,payload", ADMIN_REQUESTS)
def test_api_key_cannot_read_or_mutate_admin_resources(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    response = _request(
        client,
        method,
        path,
        payload,
        headers={"X-API-Key": "<NON_SECRET_API_KEY>"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize("method,path,payload", ADMIN_REQUESTS)
def test_invalid_bearer_cannot_read_or_mutate_admin_resources(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    response = _request(
        client,
        method,
        path,
        payload,
        headers={"Authorization": "Bearer <NON_SECRET_INVALID_TOKEN>"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize("method,path,payload", ADMIN_REQUESTS)
def test_expired_bearer_cannot_read_or_mutate_admin_resources(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    expired_token = security.create_access_token(
        subject="expired-admin-test",
        expires_delta=timedelta(seconds=-60),
    )
    response = _request(
        client,
        method,
        path,
        payload,
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize("method,path,payload", ADMIN_REQUESTS)
def test_inactive_superuser_cannot_read_or_mutate_admin_resources(
    client: TestClient,
    db: Session,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
        ),
    )
    user.is_superuser = True
    user.is_active = False
    db.add(user)
    db.commit()
    token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=5),
    )

    response = _request(
        client,
        method,
        path,
        payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_superuser_can_read_admin_health(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/v1/admin/health", headers=superuser_token_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "not_ready"}
