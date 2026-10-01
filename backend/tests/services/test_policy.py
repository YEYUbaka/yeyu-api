from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from ipaddress import ip_address
from uuid import UUID

import pytest
from redis.exceptions import RedisError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import ApiDefinition, UsageDaily
from app.schemas.api_keys import ApiKeyPrincipal
from app.schemas.policy import PolicyUpdate
from app.services.policy import PolicyDenied, PolicyService
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

    def eval(self, script: str, numkeys: int, *args: object) -> object:
        keys = [str(value) for value in args[:numkeys]]
        values = [str(value) for value in args[numkeys:]]
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
                retry = min(leases.values()) - now
                return [0, len(leases), max(1, retry)]
            leases[token] = now + ttl
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
                for key, current in zip(keys, counts, strict=True):
                    if current <= 1:
                        self.counters.pop(key, None)
                    else:
                        self.counters[key] = current - 1
                return [0, failed, counts[failed - 1] - 1, int(values[-1])]
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

    lease = service.acquire(principal, api, ip_address("192.0.2.10"), now)
    with pytest.raises(PolicyDenied) as exc_info:
        service.acquire(principal, api, ip_address("192.0.2.10"), now)

    assert exc_info.value.decision.reason == "CONCURRENCY_LIMIT"
    assert len(session.exec(select(UsageDaily)).all()) == 1
    assert lease.release() is True
    assert lease.release() is False

    replacement = service.acquire(
        principal, api, ip_address("192.0.2.10"), now
    )
    assert replacement.released is False
    replacement.release()
    assert session.exec(select(UsageDaily)).one().request_count == 2


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
