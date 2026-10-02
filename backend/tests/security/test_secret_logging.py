from __future__ import annotations

import os
import secrets
from typing import Any

os.environ.update(
    {
        "SECRET_KEY": secrets.token_urlsafe(32),
        "PROJECT_NAME": "Yeyu API security logging tests",
        "DATABASE_URL": "postgresql://localhost/yeyu_security_logging_test",
        "FIRST_SUPERUSER": "security-logging@example.com",
        "FIRST_SUPERUSER_PASSWORD": secrets.token_urlsafe(32),
        "API_KEY_PEPPER": secrets.token_urlsafe(32),
        "FASTAPI_ENV": "development",
    }
)

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.middleware.request_logging import RequestLoggingMiddleware
from app.services.audit import AuditService


class CaptureSession:
    def __init__(self) -> None:
        self.items: list[Any] = []

    def add(self, item: Any) -> None:
        self.items.append(item)


class FixedClientScope:
    def __init__(self, application: Any) -> None:
        self.application = application

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            scope = dict(scope)
            scope["client"] = ("203.0.113.77", 4567)
        await self.application(scope, receive, send)


def test_request_logging_and_audit_keep_sensitive_values_out_of_logs(
    caplog: Any,
) -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    capture = CaptureSession()

    @app.post("/security/{slug}")
    async def security_route(slug: str, request: Request) -> JSONResponse:
        request.state.api_slug = slug
        request.state.error_category = "invalid_parameters"
        payload = await request.json()
        AuditService(capture).record(
            actor_id=None,
            action="security.test",
            object_type="request",
            object_id="request-1",
            outcome="rejected",
            metadata={
                "authorization": request.headers.get("authorization"),
                "token": request.query_params.get("token"),
                "password": payload.get("password"),
            },
            request_id=request.state.request_id,
        )
        request_id = request.state.request_id
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_PARAMETERS",
                    "message": "Request is invalid",
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )

    secret_markers = {
        "header": "AUTH_HEADER_SENTINEL",
        "query": "QUERY_SECRET_SENTINEL",
        "body": "BODY_SECRET_SENTINEL",
        "ip": "203.0.113.77",
    }

    with caplog.at_level(logging.INFO, logger="yeyu.request"):
        with TestClient(FixedClientScope(app)) as client:
            response = client.post(
                "/security/test-slug",
                params={"token": secret_markers["query"]},
                headers={"Authorization": secret_markers["header"]},
                json={"password": secret_markers["body"]},
            )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == response.json()["error"]["request_id"]
    assert len(capture.items) == 1
    audit_details = capture.items[0].details
    assert audit_details["authorization"] == "[REDACTED]"
    assert audit_details["token"] == "[REDACTED]"
    assert audit_details["password"] == "[REDACTED]"

    log_text = caplog.text
    for marker in secret_markers.values():
        assert marker not in log_text
    assert "Authorization" not in log_text
    assert "password" not in log_text
    assert "token" not in log_text
    assert secret_markers["ip"] not in log_text
