from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from app.models import UsageDaily
from app.services.redis import LimitResult, RedisStore

MINUTE_WINDOW_SECONDS = 60
DEFAULT_CONCURRENCY_LEASE_TTL_SECONDS = 120


class QuotaDatabaseUnavailable(RuntimeError):
    """The authoritative daily quota store could not be updated safely."""


class ConcurrencyLimitExceeded(RuntimeError):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__("concurrency limit exceeded")


@dataclass(frozen=True)
class DailyUsageResult:
    allowed: bool
    request_count: int
    weighted_units: int
    remaining: int
    retry_after_seconds: int | None = None


@dataclass
class QuotaLease:
    """A releasable Redis concurrency slot with idempotent cleanup."""

    store: RedisStore
    key: str
    token: str
    _released: bool = False

    @property
    def released(self) -> bool:
        return self._released

    def release(self) -> bool:
        if self._released:
            return False
        released = self.store.release_lease(key=self.key, token=self.token)
        self._released = True
        return released

    def __enter__(self) -> QuotaLease:
        return self

    def __exit__(
        self,
        _exc_type: object,
        exc: BaseException | None,
        _tb: object,
    ) -> Literal[False]:
        try:
            self.release()
        except Exception as cleanup_error:
            if exc is None:
                raise
            try:
                exc.add_note(
                    "quota lease release failed while preserving the original "
                    f"{type(exc).__name__}: {type(cleanup_error).__name__}"
                )
            except Exception:
                pass
        return False


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _retry_until_next_utc_day(now: datetime) -> int:
    normalized = _utc(now)
    next_day = datetime.combine(
        normalized.date() + timedelta(days=1), time.min, tzinfo=UTC
    )
    return max(1, int((next_day - normalized).total_seconds() + 0.999999))


class QuotaService:
    """Atomic Redis admission primitives and PostgreSQL daily accounting."""

    def __init__(self, session: Session, redis: Any | None = None) -> None:
        self.session = session
        self.redis = redis if isinstance(redis, RedisStore) else RedisStore(redis)

    @staticmethod
    def _key(scope: str, *parts: object) -> str:
        material = "\x1f".join(str(part) for part in parts)
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return f"yeyu:quota:{scope}:{digest}"

    def check_minute_limits(
        self,
        *,
        user_id: UUID,
        api_key_id: UUID,
        api_slug: str,
        client_ip: str,
        minute_limit: int,
        ip_minute_limit: int,
    ) -> LimitResult:
        return self.redis.check_limits(
            keys=(
                self._key("minute-account", user_id, api_slug),
                self._key("minute-key", api_key_id, api_slug),
                self._key("minute-ip", client_ip, api_slug),
            ),
            limits=(minute_limit, minute_limit, ip_minute_limit),
            window_seconds=MINUTE_WINDOW_SECONDS,
        )

    def _usage_row(
        self,
        *,
        utc_date: date,
        user_id: UUID,
        api_key_id: UUID,
        api_slug: str,
    ) -> UsageDaily | None:
        return self.session.exec(
            select(UsageDaily).where(
                UsageDaily.utc_date == utc_date,
                UsageDaily.user_id == user_id,
                UsageDaily.api_key_id == api_key_id,
                UsageDaily.api_slug == api_slug,
            )
        ).first()

    def daily_remaining(
        self,
        *,
        now: datetime,
        user_id: UUID,
        api_key_id: UUID,
        api_slug: str,
        daily_limit: int,
    ) -> int:
        row = self._usage_row(
            utc_date=_utc(now).date(),
            user_id=user_id,
            api_key_id=api_key_id,
            api_slug=api_slug,
        )
        return max(0, daily_limit - (row.weighted_units if row else 0))

    def charge_daily(
        self,
        *,
        now: datetime,
        user_id: UUID,
        api_key_id: UUID,
        api_slug: str,
        daily_limit: int,
        weight: int,
    ) -> DailyUsageResult:
        if daily_limit < 0 or weight <= 0:
            raise ValueError("daily_limit must be non-negative and weight positive")

        utc_now = _utc(now)
        utc_date = utc_now.date()
        existing = self._usage_row(
            utc_date=utc_date,
            user_id=user_id,
            api_key_id=api_key_id,
            api_slug=api_slug,
        )
        current_count = existing.request_count if existing else 0
        current_weight = existing.weighted_units if existing else 0
        if current_weight + weight > daily_limit:
            return DailyUsageResult(
                allowed=False,
                request_count=current_count,
                weighted_units=current_weight,
                remaining=max(0, daily_limit - current_weight),
                retry_after_seconds=_retry_until_next_utc_day(utc_now),
            )

        bind = self.session.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
        if dialect_name == "postgresql":
            insert = postgresql_insert
        elif dialect_name == "sqlite":
            insert = sqlite_insert
        else:
            raise QuotaDatabaseUnavailable(
                f"unsupported database dialect for atomic daily quota: {dialect_name}"
            )

        table = UsageDaily.__table__
        statement = insert(table).values(
            id=uuid4(),
            utc_date=utc_date,
            user_id=user_id,
            api_key_id=api_key_id,
            api_slug=api_slug,
            request_count=1,
            weighted_units=weight,
            created_at=utc_now,
            updated_at=utc_now,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["utc_date", "user_id", "api_key_id", "api_slug"],
            set_={
                "request_count": table.c.request_count + 1,
                "weighted_units": table.c.weighted_units + weight,
                "updated_at": utc_now,
            },
            where=table.c.weighted_units + weight <= daily_limit,
        )
        try:
            result = self.session.execute(statement)
            if getattr(result, "rowcount", 0) != 1:
                self.session.rollback()
                existing = self._usage_row(
                    utc_date=utc_date,
                    user_id=user_id,
                    api_key_id=api_key_id,
                    api_slug=api_slug,
                )
                current_count = existing.request_count if existing else 0
                current_weight = existing.weighted_units if existing else 0
                return DailyUsageResult(
                    allowed=False,
                    request_count=current_count,
                    weighted_units=current_weight,
                    remaining=max(0, daily_limit - current_weight),
                    retry_after_seconds=_retry_until_next_utc_day(utc_now),
                )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise QuotaDatabaseUnavailable from exc

        row = self._usage_row(
            utc_date=utc_date,
            user_id=user_id,
            api_key_id=api_key_id,
            api_slug=api_slug,
        )
        if row is None:
            raise QuotaDatabaseUnavailable("daily quota row disappeared after commit")
        return DailyUsageResult(
            allowed=True,
            request_count=row.request_count,
            weighted_units=row.weighted_units,
            remaining=max(0, daily_limit - row.weighted_units),
        )

    def acquire_concurrency(
        self,
        *,
        user_id: UUID,
        api_key_id: UUID,
        api_slug: str,
        concurrency_limit: int,
        now: datetime | None = None,
        lease_ttl_seconds: int = DEFAULT_CONCURRENCY_LEASE_TTL_SECONDS,
    ) -> QuotaLease:
        token = secrets.token_urlsafe(18)
        key = self._key("concurrency", user_id, api_key_id, api_slug)
        result = self.redis.acquire_lease(
            key=key,
            token=token,
            limit=concurrency_limit,
            ttl_seconds=lease_ttl_seconds,
            now_seconds=int(_utc(now or datetime.now(UTC)).timestamp()),
        )
        if not result.allowed:
            raise ConcurrencyLimitExceeded(result.retry_after_seconds or lease_ttl_seconds)
        return QuotaLease(store=self.redis, key=key, token=token)

    def acquire(self, **kwargs: Any) -> QuotaLease:
        return self.acquire_concurrency(**kwargs)
