from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/admin/catalog",
        "/api/v1/admin/audit",
        "/api/v1/admin/health",
    ],
)
def test_normal_user_cannot_read_admin_resources(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    path: str,
) -> None:
    response = client.get(path, headers=normal_user_token_headers)

    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/admin/catalog",
        "/api/v1/admin/audit",
        "/api/v1/admin/health",
    ],
)
def test_api_key_cannot_read_admin_resources(
    client: TestClient, path: str
) -> None:
    response = client.get(path, headers={"X-API-Key": "<NON_SECRET_API_KEY>"})

    assert response.status_code == 403
