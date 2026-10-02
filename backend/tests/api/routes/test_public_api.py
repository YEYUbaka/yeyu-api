from __future__ import annotations

import json
import secrets
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from ipaddress import IPv4Address, ip_address
from typing import Any
from uuid import UUID

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.deps import (
    ApiError,
    close_api_runner,
    close_redis_store,
    get_api_runner,
    get_client_ip,
    get_db,
    get_redis_store,
)
from app.api.routes.public_api import (
    _execution_status,
    _policy_response,
)
from app.core import security
from app.core.config import settings
from app.main import app
from app.models import ApiDefinition, ApiKey, ApiPolicy, User
from app.schemas.policy import PolicyDecision
from app.services.execution.models import ApiResponse
from app.services.execution.runner import ApiRunner
from app.services.redis import RedisStore

PUBLIC_API_PATH = f"{settings.API_V1_STR}/tools"


@dataclass
class PublicApiEnvironment:
    client: TestClient
    engine: object
    raw_key: str = field(repr=False)
    user_id: UUID = field(repr=False)
    redis: InMemoryQuotaRedis | None = None

    def __iter__(self):
        yield self.client
        yield self.engine
        yield self.raw_key
        yield self.user_id
        yield self.redis


class InMemoryQuotaRedis:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.leases: dict[str, dict[str, int]] = {}
        self.now = 1_000

    def eval(self, script: str, numkeys: int, *args: object) -> object:
        keys = [str(value) for value in args[:numkeys]]
        values = [str(value) for value in args[numkeys:]]
        if "INCRBY" in script:
            limits = [int(value) for value in values[:-1]]
            counts = [self.counters.get(key, 0) + 1 for key in keys]
            failed = next(
                (
                    index
                    for index, (current, limit) in enumerate(
                        zip(counts, limits, strict=True), 1
                    )
                    if current > limit
                ),
                None,
            )
            if failed is not None:
                remaining_after: list[int] = []
                for index, (key, current) in enumerate(
                    zip(keys, counts, strict=True)
                ):
                    after_rollback = current - 1
                    if after_rollback <= 0:
                        self.counters.pop(key, None)
                    else:
                        self.counters[key] = after_rollback
                    remaining_after.append(limits[index] - after_rollback)
                return [
                    0,
                    failed,
                    counts[failed - 1] - 1,
                    int(values[-1]),
                    *remaining_after,
                ]
            for key, current in zip(keys, counts, strict=True):
                self.counters[key] = current
            remaining = [
                limit - current
                for limit, current in zip(limits, counts, strict=True)
            ]
            return [1, min(remaining), 0, 0, *remaining]

        if "ZREMRANGEBYSCORE" in script:
            key = keys[0]
            now, limit, ttl, token = (
                int(values[0]),
                int(values[1]),
                int(values[2]),
                values[3],
            )
            leases = self.leases.setdefault(key, {})
            for current_token, expires_at in list(leases.items()):
                if expires_at <= now:
                    del leases[current_token]
            if len(leases) >= limit:
                retry = max(1, min(leases.values()) - now)
                return [0, len(leases), retry]
            leases[token] = now + ttl
            return [1, len(leases), ttl]

        if "ZREM" in script:
            key = keys[0]
            token = values[0]
            leases = self.leases.setdefault(key, {})
            removed = int(leases.pop(token, None) is not None)
            if not leases:
                self.leases.pop(key, None)
            return removed

        raise AssertionError(f"unexpected Redis script: {script}")


class BrokenQuotaRedis:
    def eval(self, *_args: object) -> object:
        raise RuntimeError("redis unavailable")


class LeaseBrokenQuotaRedis(InMemoryQuotaRedis):
    def eval(self, script: str, numkeys: int, *args: object) -> object:
        if "ZREMRANGEBYSCORE" in script:
            raise RuntimeError("lease unavailable")
        return super().eval(script, numkeys, *args)


@pytest.fixture()
def public_api_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[PublicApiEnvironment]:
    monkeypatch.setattr(settings, "API_KEY_PEPPER", "public-api-test-pepper")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    redis = InMemoryQuotaRedis()

    def override_get_db() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    def override_get_client_ip() -> IPv4Address:
        return ip_address("192.0.2.10")

    runner = ApiRunner()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_client_ip] = override_get_client_ip
    app.dependency_overrides[get_redis_store] = lambda: RedisStore(redis)
    with Session(engine) as session:
        user = User(
            email=f"public-api-{secrets.token_hex(8)}@example.com",
            hashed_password="not-used-by-this-fixture",
            email_verified=True,
            is_active=True,
        )
        time_api = ApiDefinition(
            slug="time",
            name="Time API",
            summary="Current time",
            category="tools",
            method="GET",
            path="/v1/tools/time",
            visibility="public",
            status="healthy",
            adapter_name="builtin-tools",
        )
        uuid_api = ApiDefinition(
            slug="uuid",
            name="UUID API",
            summary="Generate UUID",
            category="tools",
            method="GET",
            path="/v1/tools/uuid",
            visibility="public",
            status="published",
            adapter_name="builtin-tools",
        )
        session.add_all([user, time_api, uuid_api])
        session.commit()
        session.refresh(user)

        raw_key = "yk_test_" + secrets.token_urlsafe(32)
        record = ApiKey(
            user_id=user.id,
            prefix=security.get_api_key_prefix(raw_key),
            key_hash=security.hash_api_key(
                raw_key,
                version=settings.API_KEY_PEPPER_VERSION,
            ),
            hash_version=settings.API_KEY_PEPPER_VERSION,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        user_id = user.id

    app.dependency_overrides[get_api_runner] = lambda: runner
    try:
        with TestClient(app) as client:
            yield PublicApiEnvironment(client, engine, raw_key, user_id, redis)
    finally:
        runner.close()
        app.dependency_overrides.pop(get_api_runner, None)
        app.dependency_overrides.pop(get_redis_store, None)
        app.dependency_overrides.pop(get_client_ip, None)
        app.dependency_overrides.pop(get_db, None)


def test_public_tool_requires_api_key_and_does_not_use_cookie(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, _engine, _raw_key, _user_id, _redis = public_api_environment

    response = client.get(
        f"{PUBLIC_API_PATH}/uuid",
        cookies={settings.AUTH_COOKIE_NAME: "management-cookie-only"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "API_KEY_REQUIRED"
    assert "management-cookie-only" not in response.text


def test_public_time_and_uuid_execute_with_api_key(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, _engine, raw_key, _user_id, redis = public_api_environment
    headers = {"X-API-Key": raw_key}

    time_response = client.get(
        f"{PUBLIC_API_PATH}/time",
        headers=headers,
        params={"timezone": "Asia/Shanghai"},
    )
    uuid_response = client.get(f"{PUBLIC_API_PATH}/uuid", headers=headers)

    assert time_response.status_code == 200
    assert time_response.json()["success"] is True
    assert time_response.json()["data"]["timezone"] == "Asia/Shanghai"
    assert time_response.json()["meta"]["cache_hit"] is False
    assert time_response.json()["meta"]["stale"] is False
    assert time_response.json()["meta"]["request_id"]

    assert uuid_response.status_code == 200
    assert uuid_response.json()["success"] is True
    assert uuid_response.json()["data"]["version"] == 4
    assert redis.leases == {}


def test_public_route_rejects_unpublished_and_unknown_tools(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, engine, raw_key, _user_id, _redis = public_api_environment
    with Session(engine) as session:  # type: ignore[arg-type]
        session.add(
            ApiDefinition(
                slug="trial-tool",
                name="Trial",
                summary="Not public",
                category="tools",
                method="GET",
                path="/v1/tools/trial-tool",
                visibility="public",
                status="trial",
                adapter_name="builtin-tools",
            )
        )
        session.add(
            ApiDefinition(
                slug="weather",
                name="Weather",
                summary="Not registered",
                category="content",
                method="GET",
                path="/v1/tools/weather",
                visibility="public",
                status="healthy",
                adapter_name="builtin-tools",
            )
        )
        session.commit()

    headers = {"X-API-Key": raw_key}
    trial_response = client.get(
        f"{PUBLIC_API_PATH}/trial-tool",
        headers=headers,
    )
    unknown_response = client.get(
        f"{PUBLIC_API_PATH}/weather",
        headers=headers,
    )

    assert trial_response.status_code == 404
    assert trial_response.json()["error"]["code"] == "API_NOT_FOUND"
    assert unknown_response.status_code == 404
    assert unknown_response.json()["error"]["code"] == "API_NOT_FOUND"


def test_public_route_rejects_invalid_and_revoked_api_keys(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, engine, raw_key, _user_id, _redis = public_api_environment

    invalid_response = client.get(
        f"{PUBLIC_API_PATH}/uuid",
        headers={"X-API-Key": "not-a-valid-key"},
    )
    assert invalid_response.status_code == 401
    assert invalid_response.json()["error"]["code"] == "API_KEY_INVALID"

    with Session(engine) as session:  # type: ignore[arg-type]
        record = session.exec(select(ApiKey)).one()
        record.revoked_at = datetime.now(UTC)
        session.add(record)
        session.commit()

    revoked_response = client.get(
        f"{PUBLIC_API_PATH}/uuid",
        headers={"X-API-Key": raw_key},
    )
    assert revoked_response.status_code == 401
    assert revoked_response.json()["error"]["code"] == "API_KEY_REVOKED"


def test_public_tool_requires_a_published_fixed_definition(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, engine, raw_key, _user_id, _redis = public_api_environment
    with Session(engine) as session:  # type: ignore[arg-type]
        definition = session.exec(
            select(ApiDefinition).where(ApiDefinition.slug == "time")
        ).one()
        definition.status = "trial"
        session.add(definition)
        session.commit()

    response = client.get(
        f"{PUBLIC_API_PATH}/time",
        headers={"X-API-Key": raw_key},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "API_NOT_FOUND"

    with Session(engine) as session:  # type: ignore[arg-type]
        definition = session.exec(
            select(ApiDefinition).where(ApiDefinition.slug == "time")
        ).one()
        definition.status = "healthy"
        definition.path = "/not-a-fixed-tool-path"
        session.add(definition)
        session.commit()

    mismatch_response = client.get(
        f"{PUBLIC_API_PATH}/time",
        headers={"X-API-Key": raw_key},
    )
    assert mismatch_response.status_code == 404
    assert mismatch_response.json()["error"]["code"] == "API_NOT_FOUND"


def test_public_tool_rejects_query_shape_before_execution(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, _engine, raw_key, _user_id, _redis = public_api_environment
    headers = {"X-API-Key": raw_key}

    duplicate_response = client.get(
        f"{PUBLIC_API_PATH}/time",
        headers=headers,
        params=[("timezone", "UTC"), ("timezone", "UTC")],
    )
    oversized_response = client.get(
        f"{PUBLIC_API_PATH}/time",
        headers=headers,
        params={"timezone": "x" * 5_000},
    )

    assert duplicate_response.status_code == 422
    assert duplicate_response.json()["error"]["code"] == "INVALID_PARAMETERS"
    assert oversized_response.status_code == 422
    assert oversized_response.json()["error"]["code"] == "RESOURCE_LIMIT"


def test_public_tool_policy_rejects_an_unapproved_client_ip(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, engine, raw_key, _user_id, redis = public_api_environment
    with Session(engine) as session:  # type: ignore[arg-type]
        definition = session.exec(
            select(ApiDefinition).where(ApiDefinition.slug == "time")
        ).one()
        session.add(
            ApiPolicy(
                api_definition_id=definition.id,
                allowed_ips=["198.51.100.0/24"],
            )
        )
        session.commit()

    response = client.get(
        f"{PUBLIC_API_PATH}/time",
        headers={"X-API-Key": raw_key},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "IP_NOT_ALLOWED"
    assert redis.leases == {}


def test_public_response_status_mapping_and_internal_admission_error() -> None:
    def failed(code: str) -> ApiResponse:
        return ApiResponse(
            success=False,
            data=None,
            error={"code": code, "message": "safe", "request_id": "req"},
            meta={"request_id": "req", "cache_hit": False, "stale": False},
        )

    assert _execution_status(failed("UPSTREAM_TIMEOUT")) == 504
    assert _execution_status(failed("UPSTREAM_ERROR")) == 502
    assert _execution_status(failed("UNEXPECTED")) == 500
    response = _policy_response(
        PolicyDecision(
            allowed=False,
            code="ADMISSION_REUSED",
            retry_after_seconds=2,
        ),
        "req",
    )
    assert response.status_code == 503
    assert json.loads(response.body)["error"] == {
        "code": "QUOTA_UNAVAILABLE",
        "message": "Quota service is temporarily unavailable",
        "request_id": "req",
    }


def test_client_ip_and_process_dependencies_have_safe_boundaries() -> None:
    valid_request = Request(
        {"type": "http", "client": ("192.0.2.11", 1234), "headers": []}
    )
    assert get_client_ip(valid_request) == ip_address("192.0.2.11")

    invalid_request = Request(
        {"type": "http", "client": ("testclient", 1234), "headers": []}
    )
    with pytest.raises(ApiError, match="Client IP is invalid"):
        get_client_ip(invalid_request)

    runner = get_api_runner()
    assert runner.registry.slugs() == ("time", "uuid")
    close_api_runner()
    store = get_redis_store()
    assert isinstance(store, RedisStore)
    close_redis_store()


@pytest.mark.parametrize(
    ("slug", "params"),
    [
        ("uuid", {"timezone": "UTC"}),
        ("time", {"url": "https://example.invalid"}),
        ("time", {"timezone": "../etc/passwd"}),
    ],
)
def test_public_tool_rejects_untrusted_or_invalid_parameters(
    public_api_environment: PublicApiEnvironment,
    slug: str,
    params: dict[str, str],
) -> None:
    client, _engine, raw_key, _user_id, _redis = public_api_environment

    response = client.get(
        f"{PUBLIC_API_PATH}/{slug}",
        headers={"X-API-Key": raw_key},
        params=params,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] in {
        "INVALID_PARAMETERS",
        "RESOURCE_LIMIT",
    }
    assert "example.invalid" not in response.text


def test_public_policy_rejection_is_unified_and_does_not_run_adapter(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, engine, raw_key, _user_id, redis = public_api_environment
    with Session(engine) as session:  # type: ignore[arg-type]
        api = session.exec(
            select(ApiDefinition).where(ApiDefinition.slug == "time")
        ).one()
        session.add(
            ApiPolicy(
                api_definition_id=api.id,
                minute_limit=0,
                ip_minute_limit=0,
                daily_limit=1000,
                concurrency_limit=1,
                weight=1,
            )
        )
        session.commit()

    response = client.get(
        f"{PUBLIC_API_PATH}/time",
        headers={"X-API-Key": raw_key},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "MINUTE_LIMIT"
    assert redis.leases == {}


def test_public_quota_dependency_failure_fails_closed(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, _engine, raw_key, _user_id, _redis = public_api_environment
    app.dependency_overrides[get_redis_store] = lambda: RedisStore(
        BrokenQuotaRedis()
    )

    response = client.get(
        f"{PUBLIC_API_PATH}/uuid",
        headers={"X-API-Key": raw_key},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "QUOTA_UNAVAILABLE"
    assert "redis unavailable" not in response.text


def test_public_lease_failure_fails_closed(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, _engine, raw_key, _user_id, _redis = public_api_environment
    app.dependency_overrides[get_redis_store] = lambda: RedisStore(
        LeaseBrokenQuotaRedis()
    )

    response = client.get(
        f"{PUBLIC_API_PATH}/uuid",
        headers={"X-API-Key": raw_key},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "QUOTA_UNAVAILABLE"


def test_public_openapi_declares_api_key_security(
    public_api_environment: PublicApiEnvironment,
) -> None:
    client, _engine, _raw_key, _user_id, _redis = public_api_environment

    schema: dict[str, Any] = client.get(
        f"{settings.API_V1_STR}/openapi.json"
    ).json()
    operation = schema["paths"][f"{PUBLIC_API_PATH}/{{slug}}"]["get"]

    assert operation["security"] == [{"APIKeyHeader": []}]
    assert schema["components"]["securitySchemes"]["APIKeyHeader"]["name"] == (
        "X-API-Key"
    )
