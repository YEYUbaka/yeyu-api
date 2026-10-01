from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from uuid import UUID

import pytest
from redis.exceptions import RedisError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import ApiDefinition, UsageDaily
from app.schemas.api_keys import ApiKeyPrincipal
from app.schemas.policy import PolicyDecision, PolicyUpdate
from app.services.policy import PolicyDenied, PolicyService
from app.services.quota import QuotaLease, QuotaService
from app.services.redis import RedisUnavailable


class CountingRedis:
    def __init__(self) -> None:
        self.count = 0

    def eval(self, *_args: object) -> int:
        self.count += 1
        return self.count


class AtomicRedis:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.leases: dict[str, dict[str, int]] = {}
        self.lease_key_expiry: dict[str, int] = {}

    def eval(self, script: str, numkeys: int, *args: object) -> object:
        keys = [str(value) for value in args[:numkeys]]
        values = [str(value) for value in args[numkeys:]]
        if "ZREMRANGEBYSCORE" in script:
            if "ZREVRANGE" not in script or "math.ceil" not in script:
                raise AssertionError(
                    "lease script must retain the maximum member expiration"
                )
            key = keys[0]
            now, limit, ttl, token = (
                int(values[0]),
                int(values[1]),
                int(values[2]),
                values[3],
            )
            if self.lease_key_expiry.get(key, now + 1) <= now:
                self.leases.pop(key, None)
            leases = self.leases.setdefault(key, {})
            for current_token, expires_at in list(leases.items()):
                if expires_at <= now:
                    del leases[current_token]
            if len(leases) >= limit:
                retry = min(leases.values()) - now
                return [0, len(leases), max(1, retry)]
            leases[token] = now + ttl
            self.lease_key_expiry[key] = max(leases.values())
            return [1, len(leases), ttl]
        if "ZREM" in script:
            key = keys[0]
            token = values[0]
            leases = self.leases.setdefault(key, {})
            return int(leases.pop(token, None) is not None)
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
                for key, current in zip(keys, counts, strict=True):
                    after_rollback = current - 1
                    if after_rollback <= 0:
                        self.counters.pop(key, None)
                    else:
                        self.counters[key] = after_rollback
                    remaining_after.append(
                        limits[len(remaining_after)] - after_rollback
                    )
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
        raise AssertionError(f"unexpected Redis script: {script}")


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _api(session: Session, slug: str = "uuid") -> ApiDefinition:
    api = ApiDefinition(
        slug=slug,
        name="UUID",
        summary="UUID",
        category="tools",
        method="GET",
        path=f"/v1/tools/{slug}",
        adapter_name="builtin-tools",
    )
    session.add(api)
    session.commit()
    session.refresh(api)
    return api


def _principal() -> ApiKeyPrincipal:
    return ApiKeyPrincipal(
        key_id=UUID(int=1),
        user_id=UUID(int=2),
        prefix="yeyu_test",
        hash_version=1,
    )


def test_policy_blocks_second_request_when_minute_limit_is_one(
    session: Session,
) -> None:
    api = _api(session)
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    service = PolicyService(
        session,
        redis=CountingRedis(),
        minute_limit=1,
        daily_limit=1000,
    )

    first = service.evaluate(_principal(), api, ip_address("192.0.2.10"), now)
    second = service.evaluate(_principal(), api, ip_address("192.0.2.10"), now)

    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "MINUTE_LIMIT"
    assert second.retry_after_seconds is not None
    assert second.retry_after_seconds > 0


def test_policy_charges_weighted_daily_usage_and_resets_on_utc_date(
    session: Session,
) -> None:
    api = _api(session)
    service = PolicyService(session, redis=AtomicRedis())
    service.upsert(
        api.slug,
        PolicyUpdate(
            minute_limit=100,
            ip_minute_limit=100,
            daily_limit=5,
            weight=3,
        ),
    )
    principal = _principal()
    before_midnight = datetime(2026, 10, 1, 23, 59, tzinfo=UTC)

    first = service.evaluate(
        principal, api, ip_address("192.0.2.10"), before_midnight
    )
    second = service.evaluate(
        principal, api, ip_address("192.0.2.10"), before_midnight
    )
    next_day = service.evaluate(
        principal,
        api,
        ip_address("192.0.2.10"),
        datetime(2026, 10, 2, 0, 0, tzinfo=UTC),
    )

    assert first.allowed is True
    assert first.daily_remaining == 2
    assert second.allowed is False
    assert second.reason == "DAILY_QUOTA_EXCEEDED"
    assert second.daily_remaining == 2
    assert second.retry_after_seconds is not None
    assert next_day.allowed is True

    rows = session.exec(select(UsageDaily)).all()
    assert len(rows) == 2
    assert {row.request_count for row in rows} == {1}
    assert {row.weighted_units for row in rows} == {3}


def test_ip_minute_limit_is_reported_and_policy_rejection_is_not_billed(
    session: Session,
) -> None:
    api = _api(session)
    service = PolicyService(session, redis=AtomicRedis())
    service.upsert(
        api.slug,
        PolicyUpdate(
            minute_limit=10,
            ip_minute_limit=1,
            daily_limit=100,
        ),
    )
    principal = _principal()
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    first = service.evaluate(principal, api, ip_address("192.0.2.10"), now)
    second = service.evaluate(principal, api, ip_address("192.0.2.10"), now)

    assert first.allowed is True
    assert first.ip_minute_remaining == 0
    assert second.allowed is False
    assert second.reason == "IP_MINUTE_LIMIT"
    assert second.ip_minute_remaining == 0
    assert len(session.exec(select(UsageDaily)).all()) == 1

    service.upsert(api.slug, PolicyUpdate(enabled=False))
    rejected = service.evaluate(
        principal,
        api,
        ip_address("192.0.2.10"),
        now,
    )
    assert rejected.allowed is False
    assert rejected.reason == "POLICY_DISABLED"
    assert len(session.exec(select(UsageDaily)).all()) == 1


def test_concurrency_lease_is_releasable_and_rejection_does_not_bill(
    session: Session,
) -> None:
    api = _api(session)
    service = PolicyService(session, redis=AtomicRedis())
    service.upsert(
        api.slug,
        PolicyUpdate(
            minute_limit=100,
            ip_minute_limit=100,
            daily_limit=100,
            concurrency_limit=1,
        ),
    )
    principal = _principal()
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    first_decision = service.evaluate(
        principal, api, ip_address("192.0.2.10"), now
    )
    lease = service.acquire(
        principal,
        api,
        ip_address("192.0.2.10"),
        now,
        decision=first_decision,
    )
    second_decision = service.evaluate(
        principal, api, ip_address("192.0.2.10"), now
    )
    with pytest.raises(PolicyDenied) as exc_info:
        service.acquire(
            principal,
            api,
            ip_address("192.0.2.10"),
            now,
            decision=second_decision,
        )

    assert exc_info.value.decision.reason == "CONCURRENCY_LIMIT"
    assert session.exec(select(UsageDaily)).one().request_count == 2
    assert lease.release() is True
    assert lease.release() is False

    replacement_decision = service.evaluate(
        principal, api, ip_address("192.0.2.10"), now
    )
    replacement = service.acquire(
        principal,
        api,
        ip_address("192.0.2.10"),
        now,
        decision=replacement_decision,
    )
    assert replacement.released is False
    replacement.release()
    assert session.exec(select(UsageDaily)).one().request_count == 3


def test_policy_evaluate_admission_is_private_and_acquire_does_not_double_charge(
    session: Session,
) -> None:
    api = _api(session)
    service = PolicyService(session, redis=AtomicRedis())
    principal = _principal()
    ip = ip_address("192.0.2.10")
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    decision = service.evaluate(principal, api, ip, now)
    lease = service.acquire(principal, api, ip, now, decision=decision)

    assert "_admission" not in decision.model_dump()
    assert "admission" not in decision.model_json_schema().get("properties", {})
    assert session.exec(select(UsageDaily)).one().request_count == 1
    lease.release()

    with pytest.raises(PolicyDenied) as exc_info:
        service.acquire(principal, api, ip, now, decision=decision)
    assert exc_info.value.decision.code == "ADMISSION_REUSED"
    assert session.exec(select(UsageDaily)).one().request_count == 1


def test_policy_acquire_rejects_missing_or_forged_admission(
    session: Session,
) -> None:
    api = _api(session)
    service = PolicyService(session, redis=AtomicRedis())
    principal = _principal()
    ip = ip_address("192.0.2.10")
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    with pytest.raises(PolicyDenied) as missing:
        service.acquire(principal, api, ip, now)
    assert missing.value.decision.code == "ADMISSION_REQUIRED"

    with pytest.raises(PolicyDenied) as forged:
        service.acquire(
            principal,
            api,
            ip,
            now,
            decision=PolicyDecision(allowed=True),
        )
    assert forged.value.decision.code == "INVALID_ADMISSION"
    assert session.exec(select(UsageDaily)).all() == []


@pytest.mark.parametrize(
    ("context", "expected_code"),
    [
        ("principal", "ADMISSION_CONTEXT_MISMATCH"),
        ("api", "ADMISSION_CONTEXT_MISMATCH"),
        ("ip", "ADMISSION_CONTEXT_MISMATCH"),
    ],
)
def test_policy_admission_is_bound_to_principal_api_and_ip(
    session: Session,
    context: str,
    expected_code: str,
) -> None:
    api = _api(session, slug="uuid")
    other_api = _api(session, slug="other")
    service = PolicyService(session, redis=AtomicRedis())
    principal = _principal()
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    decision = service.evaluate(
        principal, api, ip_address("192.0.2.10"), now
    )

    candidate_principal = principal
    candidate_api = api
    candidate_ip = ip_address("192.0.2.10")
    if context == "principal":
        candidate_principal = principal.model_copy(
            update={"user_id": UUID(int=3)}
        )
    elif context == "api":
        candidate_api = other_api
    else:
        candidate_ip = ip_address("192.0.2.11")

    with pytest.raises(PolicyDenied) as exc_info:
        service.acquire(
            candidate_principal,
            candidate_api,
            candidate_ip,
            now,
            decision=decision,
        )
    assert exc_info.value.decision.code == expected_code


def test_policy_admission_expires(session: Session) -> None:
    api = _api(session)
    service = PolicyService(session, redis=AtomicRedis())
    principal = _principal()
    ip = ip_address("192.0.2.10")
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    decision = service.evaluate(principal, api, ip, now)

    with pytest.raises(PolicyDenied) as exc_info:
        service.acquire(
            principal,
            api,
            ip,
            now + timedelta(seconds=60),
            decision=decision,
        )
    assert exc_info.value.decision.code == "ADMISSION_EXPIRED"


def test_policy_reports_failed_ip_remaining_after_counter_rollback(
    session: Session,
) -> None:
    api = _api(session)
    redis = AtomicRedis()
    service = PolicyService(session, redis=redis)
    service.upsert(
        api.slug,
        PolicyUpdate(minute_limit=10, ip_minute_limit=1, daily_limit=100),
    )
    principal = _principal()
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    first = service.evaluate(principal, api, ip_address("192.0.2.10"), now)
    second = service.evaluate(principal, api, ip_address("192.0.2.10"), now)

    assert first.allowed is True
    assert second.allowed is False
    assert second.minute_remaining == 9
    assert second.ip_minute_remaining == 0


@pytest.mark.parametrize(
    ("first_ttl", "second_ttl", "expected_offset"),
    [(120, 10, 120), (10, 120, 121)],
)
def test_concurrency_key_ttl_retains_maximum_member_expiry(
    session: Session,
    first_ttl: int,
    second_ttl: int,
    expected_offset: int,
) -> None:
    redis = AtomicRedis()
    quota = QuotaService(session, redis=redis)
    principal = _principal()
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    first = quota.acquire_concurrency(
        user_id=principal.user_id,
        api_key_id=principal.api_key_id,
        api_slug="uuid",
        concurrency_limit=3,
        now=now,
        lease_ttl_seconds=first_ttl,
    )
    second = quota.acquire_concurrency(
        user_id=principal.user_id,
        api_key_id=principal.api_key_id,
        api_slug="uuid",
        concurrency_limit=3,
        now=now + timedelta(seconds=1),
        lease_ttl_seconds=second_ttl,
    )

    key = quota._key("concurrency", principal.user_id, principal.api_key_id, "uuid")
    assert redis.lease_key_expiry[key] == int(now.timestamp()) + expected_offset
    first.release()
    second.release()


def test_quota_lease_cleanup_does_not_hide_original_exception() -> None:
    class BrokenReleaseStore:
        def release_lease(self, **_kwargs: object) -> bool:
            raise RuntimeError("release failed")

    lease = QuotaLease(
        store=BrokenReleaseStore(),
        key="quota-key",
        token="opaque-token",
    )

    with pytest.raises(ValueError, match="original"):
        with lease:
            raise ValueError("original")


def test_quota_lease_release_failure_is_not_silent() -> None:
    class BrokenReleaseStore:
        def release_lease(self, **_kwargs: object) -> bool:
            raise RuntimeError("release failed")

    lease = QuotaLease(
        store=BrokenReleaseStore(),
        key="quota-key",
        token="opaque-token",
    )

    with pytest.raises(RuntimeError, match="release failed"):
        lease.release()


def test_redis_failure_is_explicit_and_fails_closed(session: Session) -> None:
    class BrokenRedis:
        def eval(self, *_args: object) -> object:
            raise RedisError("redis unavailable")

    api = _api(session)
    service = PolicyService(session, redis=BrokenRedis())

    with pytest.raises(RedisUnavailable):
        service.evaluate(
            _principal(),
            api,
            ip_address("192.0.2.10"),
            datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        )

    assert session.exec(select(UsageDaily)).all() == []
