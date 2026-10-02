from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.routes import health


def test_health_does_not_require_dependencies(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_hides_dependency_details(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        health,
        "check_readiness",
        lambda: {
            "database": "failed",
            "redis": "ok",
            "migrations": "ok",
        },
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "database": "failed",
            "redis": "ok",
            "migrations": "ok",
        },
    }
    assert "postgresql" not in response.text.lower()
    assert "redis://" not in response.text.lower()
    assert "secret" not in response.text.lower()
