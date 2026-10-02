from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from heapq import heappop, heappush
from itertools import count
from threading import Condition, Event, Lock, Thread, Timer
from time import monotonic
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from app.models import UsageDaily
from app.services.redis import LimitResult, RedisStore, RedisUnavailable

MINUTE_WINDOW_SECONDS = 60
DEFAULT_CONCURRENCY_LEASE_TTL_SECONDS = 120
_LEASE_RENEW_INTERVAL_FRACTION = 3
_MIN_LEASE_RENEW_INTERVAL_SECONDS = 0.5
_CLEANUP_QUEUE_SIZE = 1024
_CLEANUP_RETRY_MIN_SECONDS = 0.5
_CLEANUP_RETRY_MAX_SECONDS = 30.0
logger = logging.getLogger(__name__)


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


CleanupOperation = Literal["release", "cancel"]


class _LeaseCleanupScheduler:
    """Bounded, deduplicated retry queue for Redis lease cleanup."""

    def __init__(self, *, max_pending: int) -> None:
        self._heap: list[
            tuple[float, int, tuple[str, str, str], Any, CleanupOperation, int]
        ] = []
        self._max_pending = max_pending
        self._pending: set[tuple[str, str, str]] = set()
        self._condition = Condition(Lock())
        self._sequence = count()
        self._reserved = 0
        self._worker_started = False
        self._worker_restart_timer: Timer | None = None

    def reserve(self) -> bool:
        with self._condition:
            if self._heap and not self._worker_started:
                self._ensure_worker_locked()
            if len(self._pending) + self._reserved >= self._max_pending:
                return False
            self._reserved += 1
            return True

    def release_reservation(self) -> None:
        with self._condition:
            if self._reserved > 0:
                self._reserved -= 1
            self._condition.notify()

    def _ensure_worker_locked(self) -> bool:
        if self._worker_started:
            return True
        self._worker_started = True
        try:
            Thread(
                target=self._run,
                name="yeyu-quota-cleanup",
                daemon=True,
            ).start()
        except Exception:
            self._worker_started = False
            logger.warning("quota lease cleanup worker could not start")
            self._schedule_worker_restart_locked()
            return False
        return True

    def _schedule_worker_restart_locked(self) -> None:
        if (
            self._worker_restart_timer is not None
            and self._worker_restart_timer.is_alive()
        ):
            return
        try:
            timer = Timer(1.0, self._restart_worker)
            timer.daemon = True
            self._worker_restart_timer = timer
            timer.start()
        except Exception:
            self._worker_restart_timer = None
            logger.warning("quota lease cleanup worker restart could not start")

    def _restart_worker(self) -> None:
        with self._condition:
            self._worker_restart_timer = None
            if self._heap and not self._worker_started:
                self._ensure_worker_locked()
            self._condition.notify()

    def submit(
        self,
        lease: Any,
        operation: CleanupOperation,
        *,
        reserved: bool = False,
    ) -> bool:
        task_id = (lease.key, lease.token, operation)
        with self._condition:
            if task_id in self._pending:
                return True
            if reserved:
                if self._reserved <= 0:
                    return False
            elif len(self._pending) + self._reserved >= self._max_pending:
                return False
            self._pending.add(task_id)
            if reserved:
                self._reserved -= 1
            heappush(
                self._heap,
                (monotonic(), next(self._sequence), task_id, lease, operation, 0),
            )
            self._ensure_worker_locked()
            self._condition.notify()
            return True

    def _run(self) -> None:
        try:
            while True:
                with self._condition:
                    while True:
                        if not self._heap:
                            self._condition.wait()
                            continue
                        due, _sequence, task_id, lease, operation, attempt = self._heap[0]
                        delay = due - monotonic()
                        if delay > 0:
                            self._condition.wait(delay)
                            continue
                        heappop(self._heap)
                        break
                try:
                    completed = lease._perform_cleanup(operation)
                except Exception:
                    completed = False
                    logger.warning("quota lease cleanup worker failed")
                with self._condition:
                    if completed:
                        self._pending.discard(task_id)
                    else:
                        delay = min(
                            _CLEANUP_RETRY_MIN_SECONDS * (2 ** min(attempt, 6)),
                            _CLEANUP_RETRY_MAX_SECONDS,
                        )
                        heappush(
                            self._heap,
                            (
                                monotonic() + delay,
                                next(self._sequence),
                                task_id,
                                lease,
                                operation,
                                attempt + 1,
                            ),
                        )
                    self._condition.notify()
        except Exception:
            logger.warning("quota lease cleanup worker stopped unexpectedly")
            with self._condition:
                self._worker_started = False
                if self._heap:
                    self._ensure_worker_locked()


_cleanup_scheduler = _LeaseCleanupScheduler(max_pending=_CLEANUP_QUEUE_SIZE)


@dataclass
class QuotaLease:
    """A releasable Redis concurrency slot with idempotent cleanup."""

    store: RedisStore
    key: str
    token: str
    lease_ttl_seconds: int = DEFAULT_CONCURRENCY_LEASE_TTL_SECONDS
    _released: bool = False
    _state_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _renew_stop: Event = field(default_factory=Event, init=False, repr=False)
    _renew_thread: Thread | None = field(default=None, init=False, repr=False)
    _release_requested: bool = field(default=False, init=False, repr=False)
    _release_in_progress: bool = field(default=False, init=False, repr=False)
    _lease_fenced: bool = field(default=False, init=False, repr=False)
    cleanup_reserved: bool = False

    @property
    def released(self) -> bool:
        with self._state_lock:
            return self._released

    def _start_renewal_locked(self, interval_seconds: float) -> None:
        if self._released or self._release_requested:
            return
        if not callable(getattr(self.store, "renew_lease", None)):
            return
        if self._renew_thread is not None and self._renew_thread.is_alive():
            return
        self._renew_stop.clear()
        self._renew_thread = Thread(
            target=self._renew_loop,
            args=(interval_seconds,),
            name="yeyu-quota-lease-renewal",
            daemon=True,
        )
        self._renew_thread.start()

    def start_renewal(self, *, interval_seconds: float | None = None) -> None:
        if not callable(getattr(self.store, "renew_lease", None)) or not callable(
            getattr(self.store, "fence_lease", None)
        ):
            raise RuntimeError("quota lease requires renewal and fencing support")
        interval = (
            max(
                _MIN_LEASE_RENEW_INTERVAL_SECONDS,
                self.lease_ttl_seconds / _LEASE_RENEW_INTERVAL_FRACTION,
            )
            if interval_seconds is None
            else interval_seconds
        )
        if interval <= 0:
            raise ValueError("interval_seconds must be positive")
        with self._state_lock:
            self._start_renewal_locked(interval)

    def _fence(self) -> bool:
        with self._state_lock:
            if self._released or self._release_requested:
                return False
            try:
                fenced = self.store.fence_lease(key=self.key, token=self.token)
            except Exception:
                logger.warning("quota lease fencing failed")
                return False
            self._lease_fenced = fenced
            if fenced:
                self._renew_stop.set()
        if not fenced:
            logger.warning("quota lease fencing was rejected")
        return fenced

    def _renew_loop(self, interval_seconds: float) -> None:
        while not self._renew_stop.wait(interval_seconds):
            with self._state_lock:
                if self._released or self._release_requested:
                    return
            try:
                renewed = self.store.renew_lease(
                    key=self.key,
                    token=self.token,
                    ttl_seconds=self.lease_ttl_seconds,
                )
            except Exception:
                logger.warning("quota lease renewal failed")
                if self._fence():
                    return
                continue
            if not renewed and self._fence():
                return

    def _perform_cleanup(self, operation: CleanupOperation) -> bool:
        try:
            if operation == "cancel":
                cancel = getattr(self.store, "cancel_lease", None)
                if not callable(cancel):
                    return False
                completed = bool(cancel(key=self.key, token=self.token))
                if not completed:
                    return False
            else:
                self.store.release_lease(key=self.key, token=self.token)
        except Exception:
            logger.warning("quota lease cleanup attempt failed")
            return False
        with self._state_lock:
            self._release_in_progress = False
            self._release_requested = False
            self._released = True
            self._renew_stop.set()
        self._release_cleanup_reservation()
        return True

    def _release_cleanup_reservation(self) -> None:
        with self._state_lock:
            if not self.cleanup_reserved:
                return
            self.cleanup_reserved = False
        _cleanup_scheduler.release_reservation()

    def _schedule_cleanup(self, operation: CleanupOperation) -> None:
        if not callable(getattr(self.store, "renew_lease", None)):
            logger.warning("quota lease cleanup retry is unavailable")
            return
        with self._state_lock:
            reserved = self.cleanup_reserved
        if not _cleanup_scheduler.submit(
            self,
            operation,
            reserved=reserved,
        ):
            logger.warning("quota lease cleanup queue is full")
            return
        if reserved:
            with self._state_lock:
                self.cleanup_reserved = False

    def cancel_uncertain(self) -> bool:
        """Tombstone a lease whose acquire result was not observable."""
        with self._state_lock:
            if self._released or self._release_in_progress:
                return self._released
            self._release_in_progress = True
            self._release_requested = True
            self._renew_stop.set()
        try:
            cancel = getattr(self.store, "cancel_lease", None)
            if not callable(cancel):
                raise RuntimeError("quota lease cancellation is unavailable")
            completed = bool(cancel(key=self.key, token=self.token))
        except Exception:
            with self._state_lock:
                self._release_in_progress = False
            self._schedule_cleanup("cancel")
            return False
        if not completed:
            with self._state_lock:
                self._release_in_progress = False
            self._schedule_cleanup("cancel")
            return False
        with self._state_lock:
            self._release_in_progress = False
            self._release_requested = False
            self._released = True
            self._renew_stop.set()
        self._release_cleanup_reservation()
        return True

    def release(self) -> bool:
        with self._state_lock:
            if self._released or self._release_in_progress or self._release_requested:
                return False
            self._release_in_progress = True
            self._release_requested = True
            self._renew_stop.set()
        try:
            released = self.store.release_lease(key=self.key, token=self.token)
        except Exception:
            with self._state_lock:
                self._release_in_progress = False
                self._renew_stop.clear()
            self._schedule_cleanup("release")
            raise
        with self._state_lock:
            self._release_in_progress = False
            self._release_requested = False
            self._released = True
            self._renew_stop.set()
        self._release_cleanup_reservation()
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
        if not _cleanup_scheduler.reserve():
            raise RedisUnavailable("quota cleanup capacity is unavailable")
        lease = QuotaLease(
            store=self.redis,
            key=key,
            token=token,
            lease_ttl_seconds=lease_ttl_seconds,
            cleanup_reserved=True,
        )
        try:
            result = self.redis.acquire_lease(
                key=key,
                token=token,
                limit=concurrency_limit,
                ttl_seconds=lease_ttl_seconds,
                now_seconds=int(_utc(now or datetime.now(UTC)).timestamp()),
            )
        except RedisUnavailable:
            lease.cancel_uncertain()
            raise
        except Exception:
            lease._release_cleanup_reservation()
            raise
        if not result.allowed:
            lease._release_cleanup_reservation()
            raise ConcurrencyLimitExceeded(result.retry_after_seconds or lease_ttl_seconds)
        return lease

    def acquire(self, **kwargs: Any) -> QuotaLease:
        return self.acquire_concurrency(**kwargs)
