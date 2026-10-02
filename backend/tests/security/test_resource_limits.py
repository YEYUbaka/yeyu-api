from __future__ import annotations

import os
import secrets
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from time import monotonic, sleep
from typing import Any
from uuid import uuid4

os.environ.update(
    {
        "SECRET_KEY": secrets.token_urlsafe(32),
        "PROJECT_NAME": "Yeyu API security tests",
        "DATABASE_URL": "postgresql://localhost/yeyu_security_test",
        "FIRST_SUPERUSER": "security-owner@example.com",
        "FIRST_SUPERUSER_PASSWORD": secrets.token_urlsafe(32),
        "API_KEY_PEPPER": secrets.token_urlsafe(32),
        "FASTAPI_ENV": "development",
    }
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.api.routes.public_api as public_api_module
from app.api.deps import (
    get_api_runner,
    get_client_ip,
    get_db,
    get_redis_store,
)
from app.core import security
from app.core.config import settings
from app.main import app
from app.models import ApiDefinition, ApiKey, ApiPolicy, User
from app.services.execution.models import AdapterResult, ApiAdapter, ExecutionContext
from app.services.execution.registry import AdapterRegistry
from app.services.execution.runner import ApiRunner, ExecutionCompletion
from app.services.quota import QuotaLease, QuotaService
from app.services.redis import RedisStore, RedisUnavailable

PUBLIC_API_PATH = f"{settings.API_V1_STR}/tools"


class SecurityQuotaRedis:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.leases: dict[str, dict[str, int]] = {}
        self.fences: dict[str, set[str]] = {}
        self.cancellations: dict[str, dict[str, int]] = {}
        self.fail_after_acquire = False

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
                        zip(counts, limits, strict=True),
                        1,
                    )
                    if current > limit
                ),
                None,
            )
            if failed is not None:
                remaining = []
                for index, (key, current) in enumerate(
                    zip(keys, counts, strict=True)
                ):
                    after_rollback = current - 1
                    if after_rollback <= 0:
                        self.counters.pop(key, None)
                    else:
                        self.counters[key] = after_rollback
                    remaining.append(limits[index] - after_rollback)
                return [
                    0,
                    failed,
                    counts[failed - 1] - 1,
                    int(values[-1]),
                    *remaining,
                ]
            for key, current in zip(keys, counts, strict=True):
                self.counters[key] = current
            remaining = [
                limit - current
                for limit, current in zip(limits, counts, strict=True)
            ]
            return [1, min(remaining), 0, 0, *remaining]

        if "ZSCORE" in script and "ZREMRANGEBYSCORE" not in script:
            key = keys[0]
            now, ttl, token = int(values[0]), int(values[1]), values[2]
            leases = self.leases.setdefault(key, {})
            if token not in self.fences.get(keys[1], set()):
                return 0
            leases[token] = now + ttl
            return 1

        if "ZREMRANGEBYSCORE" in script and "latest_cancel" not in script:
            key = keys[0]
            now, limit, ttl, token = (
                int(values[0]),
                int(values[1]),
                int(values[2]),
                values[3],
            )
            cancellations = self.cancellations.setdefault(keys[2], {})
            for current_token, expires_at in list(cancellations.items()):
                if expires_at <= now:
                    del cancellations[current_token]
            if token in cancellations:
                return [-1, 0, ttl]
            fenced = len(self.fences.get(keys[1], set()))
            if fenced >= limit:
                return [0, fenced, ttl]
            leases = self.leases.setdefault(key, {})
            for current_token, expires_at in list(leases.items()):
                if expires_at <= now:
                    del leases[current_token]
            if len(leases) >= limit:
                return [0, len(leases), ttl]
            leases[token] = now + ttl
            self.fences.setdefault(keys[1], set()).add(token)
            if self.fail_after_acquire:
                self.fail_after_acquire = False
                raise RuntimeError("simulated response loss")
            return [1, len(leases), ttl]

        if "KEYS[3]" in script and "ZREM" in script:
            key = keys[0]
            token = values[0]
            now, tombstone_ttl = int(values[1]), int(values[2])
            cancellations = self.cancellations.setdefault(keys[2], {})
            for current_token, expires_at in list(cancellations.items()):
                if expires_at <= now:
                    del cancellations[current_token]
            cancellations[token] = now + tombstone_ttl
            leases = self.leases.setdefault(key, {})
            leases.pop(token, None)
            markers = self.fences.setdefault(keys[1], set())
            markers.discard(token)
            if not markers:
                self.fences.pop(keys[1], None)
            if not leases:
                self.leases.pop(key, None)
            return 1

        if "ZREM" in script:
            key = keys[0]
            token = values[0]
            leases = self.leases.setdefault(key, {})
            removed = int(leases.pop(token, None) is not None)
            markers = self.fences.setdefault(keys[1], set())
            markers.discard(token)
            if not markers:
                self.fences.pop(keys[1], None)
            if not leases:
                self.leases.pop(key, None)
            return removed

        if "SADD" in script:
            token = values[0]
            self.fences.setdefault(keys[1], set()).add(token)
            return 1

        raise AssertionError(f"unexpected Redis script: {script}")


class BlockingAdapter(ApiAdapter):
    adapter_name = "builtin-tools"
    cacheable = False

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()

    def execute(
        self,
        context: ExecutionContext,
        params: dict[str, Any],
    ) -> AdapterResult:
        del params
        self.started.set()
        self.release.wait(timeout=2)
        self.finished.set()
        return AdapterResult(data={"ok": True}, data_at=context.now)


class PublicSecurityEnvironment:
    def __init__(
        self,
        client: TestClient,
        raw_key: str,
        blocker: BlockingAdapter,
        runner: ApiRunner,
        engine: Any,
        redis: SecurityQuotaRedis,
    ) -> None:
        self.client = client
        self.raw_key = raw_key
        self.blocker = blocker
        self.runner = runner
        self.engine = engine
        self.redis = redis


@pytest.fixture()
def public_security_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[PublicSecurityEnvironment]:
    monkeypatch.setattr(public_api_module, "TOOL_TIMEOUT_MS", 25)
    monkeypatch.setattr(settings, "API_KEY_PEPPER", "security-test-pepper")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    redis_client = SecurityQuotaRedis()
    blocker = BlockingAdapter()
    runner = ApiRunner(
        registry=AdapterRegistry(overrides={"time": blocker}),
        max_workers=2,
    )
    raw_key = "runtime_" + secrets.token_urlsafe(32)

    def override_get_db() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    def override_get_client_ip() -> object:
        return "192.0.2.10"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_client_ip] = override_get_client_ip
    app.dependency_overrides[get_redis_store] = lambda: RedisStore(redis_client)
    app.dependency_overrides[get_api_runner] = lambda: runner

    with Session(engine) as session:
        user = User(
            email="security-runtime@example.com",
            hashed_password=security.get_password_hash(secrets.token_urlsafe(24)),
            email_verified=True,
            is_active=True,
        )
        api = ApiDefinition(
            slug="time",
            name="Time API",
            summary="Security test API",
            category="tools",
            method="GET",
            path="/v1/tools/time",
            visibility="public",
            status="published",
            adapter_name="builtin-tools",
        )
        session.add_all([user, api])
        session.commit()
        session.refresh(user)
        session.refresh(api)
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
        session.add(
            ApiPolicy(
                api_definition_id=api.id,
                minute_limit=20,
                ip_minute_limit=20,
                daily_limit=100,
                concurrency_limit=1,
                weight=1,
            )
        )
        session.commit()

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield PublicSecurityEnvironment(
                client,
                raw_key,
                blocker,
                runner,
                engine,
                redis_client,
            )
    finally:
        if blocker.started.is_set():
            blocker.release.set()
            blocker.finished.wait(timeout=2)
        runner.close()
        app.dependency_overrides.pop(get_api_runner, None)
        app.dependency_overrides.pop(get_redis_store, None)
        app.dependency_overrides.pop(get_client_ip, None)
        app.dependency_overrides.pop(get_db, None)


def test_concurrency_lease_survives_http_timeout_until_adapter_finishes(
    public_security_environment: PublicSecurityEnvironment,
) -> None:
    environment = public_security_environment
    headers = {"X-API-Key": environment.raw_key}

    first = environment.client.get(f"{PUBLIC_API_PATH}/time", headers=headers)
    assert first.status_code == 504
    assert environment.blocker.started.wait(timeout=1) is True

    second = environment.client.get(f"{PUBLIC_API_PATH}/time", headers=headers)

    assert second.status_code == 429
    assert second.json()["error"]["code"] == "CONCURRENCY_LIMIT"
    assert "runtime_" not in second.text
    assert "https://" not in second.text

    environment.blocker.release.set()
    assert environment.blocker.finished.wait(timeout=1) is True
    deadline = monotonic() + 1
    while environment.redis.leases and monotonic() < deadline:
        sleep(0.005)

    third = environment.client.get(f"{PUBLIC_API_PATH}/time", headers=headers)
    assert third.status_code == 200


class RenewalProbeStore:
    def __init__(self, *, fail_first_release: bool = False) -> None:
        self.renewed = threading.Event()
        self.release_attempts = 0
        self.fail_first_release = fail_first_release
        self.fenced = threading.Event()

    def renew_lease(self, **_kwargs: object) -> bool:
        self.renewed.set()
        return True

    def fence_lease(self, **_kwargs: object) -> bool:
        self.fenced.set()
        return True

    def release_lease(self, **_kwargs: object) -> bool:
        self.release_attempts += 1
        if self.fail_first_release and self.release_attempts == 1:
            raise RuntimeError("release unavailable")
        return True


class LostRenewalStore(RenewalProbeStore):
    def renew_lease(self, **_kwargs: object) -> bool:
        return False


def test_lease_renews_until_completion_and_retries_failed_cleanup() -> None:
    store = RenewalProbeStore(fail_first_release=True)
    lease = QuotaLease(
        store=store,  # type: ignore[arg-type]
        key="security-quota-key",
        token="security-quota-token",
        lease_ttl_seconds=1,
    )
    lease.start_renewal(interval_seconds=0.01)
    assert store.renewed.wait(timeout=1) is True

    with pytest.raises(RuntimeError, match="release unavailable"):
        lease.release()

    deadline = monotonic() + 1
    while not lease.released and monotonic() < deadline:
        sleep(0.005)
    assert lease.released is True
    assert store.release_attempts >= 2


def test_lost_renewal_fences_future_requests_until_completion() -> None:
    store = LostRenewalStore()
    lease = QuotaLease(
        store=store,  # type: ignore[arg-type]
        key="security-fenced-key",
        token="security-fenced-token",
        lease_ttl_seconds=1,
    )
    lease.start_renewal(interval_seconds=0.01)

    assert store.fenced.wait(timeout=1) is True
    assert lease.release() is True
    assert lease.released is True


def test_fence_marker_blocks_reacquire_until_release() -> None:
    client = SecurityQuotaRedis()
    store = RedisStore(client)
    key = "security-fenced-redis-key"

    first = store.acquire_lease(
        key=key,
        token="security-fenced-first",
        limit=1,
        ttl_seconds=1,
        now_seconds=100,
    )
    assert first.allowed is True

    client.leases[key]["security-fenced-first"] = 99
    second = store.acquire_lease(
        key=key,
        token="security-fenced-second",
        limit=1,
        ttl_seconds=1,
        now_seconds=100,
    )
    assert second.allowed is False

    assert store.release_lease(key=key, token="security-fenced-first") is True
    third = store.acquire_lease(
        key=key,
        token="security-fenced-third",
        limit=1,
        ttl_seconds=1,
        now_seconds=100,
    )
    assert third.allowed is True


def test_uncertain_acquire_cleans_committed_marker() -> None:
    client = SecurityQuotaRedis()
    client.fail_after_acquire = True
    store = RedisStore(client)
    service = QuotaService(object(), redis=store)  # type: ignore[arg-type]
    user_id = uuid4()
    api_key_id = uuid4()

    with pytest.raises(RedisUnavailable):
        service.acquire_concurrency(
            user_id=user_id,
            api_key_id=api_key_id,
            api_slug="time",
            concurrency_limit=1,
            lease_ttl_seconds=1,
            now=datetime.now(UTC),
        )
    assert client.fences == {}
    assert len(client.cancellations) == 1
    lease = service.acquire_concurrency(
        user_id=user_id,
        api_key_id=api_key_id,
        api_slug="time",
        concurrency_limit=1,
        lease_ttl_seconds=1,
        now=datetime.now(UTC),
    )
    assert lease.release() is True

    late_key = "security-late-acquire-key"
    assert store.cancel_lease(key=late_key, token="security-late-token") is True
    with pytest.raises(RedisUnavailable):
        store.acquire_lease(
            key=late_key,
            token="security-late-token",
            limit=1,
            ttl_seconds=1,
            now_seconds=100,
        )


def test_cleanup_reservation_returns_after_successful_release() -> None:
    client = SecurityQuotaRedis()
    service = QuotaService(object(), redis=RedisStore(client))  # type: ignore[arg-type]
    user_id = uuid4()
    api_key_id = uuid4()
    now = datetime.now(UTC)

    for _ in range(1025):
        lease = service.acquire_concurrency(
            user_id=user_id,
            api_key_id=api_key_id,
            api_slug="time",
            concurrency_limit=1,
            lease_ttl_seconds=1,
            now=now,
        )
        assert lease.release() is True


def test_completion_releases_when_runner_does_not_submit_a_future() -> None:
    released = threading.Event()
    runner = ApiRunner()
    try:
        completion = ExecutionCompletion(released.set)
        response = runner.run(
            "time",
            ExecutionContext(
                request_id="security-validation-1",
                api_slug="time",
                api_key_id="security-key-1",
                user_id="security-user-1",
                client_ip="192.0.2.10",
                timeout_ms=100,
                now=datetime.now(UTC),
            ),
            {"url": "https://not-accepted.example"},
            completion=completion,
        )

        assert response.success is False
        completion.complete_if_idle()
        assert released.is_set() is True
    finally:
        runner.close()


def test_completion_hook_failure_fails_before_future_admission() -> None:
    released = threading.Event()

    def fail_to_start_renewal() -> None:
        raise RuntimeError("renewal unavailable")

    adapter = BlockingAdapter()
    runner = ApiRunner(registry=AdapterRegistry(overrides={"time": adapter}))
    completion = ExecutionCompletion(
        released.set,
        on_pending=fail_to_start_renewal,
    )
    try:
        response = runner.run(
            "time",
            ExecutionContext(
                request_id="security-validation-2",
                api_slug="time",
                api_key_id="security-key-2",
                user_id="security-user-2",
                client_ip="192.0.2.10",
                timeout_ms=100,
                now=datetime.now(UTC),
            ),
            {},
            completion=completion,
        )

        assert response.success is False
        assert response.error is not None
        assert response.error["code"] == "UPSTREAM_ERROR"
        assert released.is_set() is True
        assert adapter.started.is_set() is False
    finally:
        runner.close()


def test_public_api_auth_error_has_matching_request_id_header(
    public_security_environment: PublicSecurityEnvironment,
) -> None:
    response = public_security_environment.client.get(f"{PUBLIC_API_PATH}/time")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "security-test-pepper" not in response.text


@pytest.mark.parametrize(
    ("method", "path", "expected_status"),
    [
        ("get", f"{PUBLIC_API_PATH}", 404),
        ("post", f"{PUBLIC_API_PATH}/time", 405),
        ("get", f"{PUBLIC_API_PATH}/Bad_Slug", 422),
    ],
)
def test_public_api_asgi_errors_are_bounded_and_request_identified(
    public_security_environment: PublicSecurityEnvironment,
    method: str,
    path: str,
    expected_status: int,
) -> None:
    request = getattr(public_security_environment.client, method)
    response = request(path, headers={"X-API-Key": public_security_environment.raw_key})

    assert response.status_code == expected_status
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "https://" not in response.text
    assert "Traceback" not in response.text
    assert "runtime_" not in response.text
