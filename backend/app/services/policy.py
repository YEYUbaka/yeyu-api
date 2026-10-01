from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address, ip_network
from threading import Lock
from typing import Any
from uuid import UUID

from pydantic import IPvAnyAddress
from sqlmodel import Session, select

from app.models import ApiDefinition, ApiPolicy
from app.schemas.api_keys import ApiKeyPrincipal
from app.schemas.policy import PolicyDecision, PolicyUpdate, PolicyView
from app.services.quota import (
    MINUTE_WINDOW_SECONDS,
    ConcurrencyLimitExceeded,
    QuotaLease,
    QuotaService,
)


class PolicyError(Exception):
    """Base class for policy configuration failures."""


class PolicyApiNotFound(PolicyError):
    pass


class PolicyDenied(PolicyError):
    def __init__(self, decision: PolicyDecision) -> None:
        self.decision = decision
        super().__init__(decision.reason or decision.code or "policy denied")


DEFAULT_MINUTE_LIMIT = 60
DEFAULT_IP_MINUTE_LIMIT = 60
DEFAULT_DAILY_LIMIT = 1000
DEFAULT_CONCURRENCY_LIMIT = 1
DEFAULT_WEIGHT = 1
ADMISSION_TTL_SECONDS = MINUTE_WINDOW_SECONDS


def _now() -> datetime:
    return datetime.now(UTC)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class _PolicyLimits:
    minute: int
    ip_minute: int
    daily: int
    concurrency: int
    weight: int


@dataclass(frozen=True, slots=True)
class _PolicyAdmission:
    token: str = field(repr=False)
    user_id: UUID
    api_key_id: UUID
    api_slug: str
    client_ip: str
    concurrency_limit: int
    expires_at: datetime
    daily_remaining: int | None
    minute_remaining: int | None
    ip_minute_remaining: int | None


class PolicyService:
    def __init__(
        self,
        session: Session,
        redis: Any | None = None,
        *,
        minute_limit: int | None = None,
        daily_limit: int | None = None,
        ip_minute_limit: int | None = None,
        concurrency_limit: int | None = None,
        weight: int | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.default_minute_limit = (
            DEFAULT_MINUTE_LIMIT if minute_limit is None else minute_limit
        )
        self.default_ip_minute_limit = (
            DEFAULT_IP_MINUTE_LIMIT
            if ip_minute_limit is None
            else ip_minute_limit
        )
        self.default_daily_limit = (
            DEFAULT_DAILY_LIMIT if daily_limit is None else daily_limit
        )
        self.default_concurrency_limit = (
            DEFAULT_CONCURRENCY_LIMIT
            if concurrency_limit is None
            else concurrency_limit
        )
        self.default_weight = DEFAULT_WEIGHT if weight is None else weight
        self._quota_service = (
            QuotaService(session, redis) if redis is not None else None
        )
        self._admissions: dict[int, _PolicyAdmission] = {}
        self._admission_lock = Lock()

    def _api(self, api_slug: str) -> ApiDefinition:
        api = self.session.exec(
            select(ApiDefinition).where(ApiDefinition.slug == api_slug)
        ).first()
        if api is None:
            raise PolicyApiNotFound
        return api

    def _policy(self, api: ApiDefinition) -> ApiPolicy | None:
        return self.session.exec(
            select(ApiPolicy).where(ApiPolicy.api_definition_id == api.id)
        ).first()

    @staticmethod
    def _view(api: ApiDefinition, policy: ApiPolicy | None) -> PolicyView:
        if policy is None:
            return PolicyView(
                api_slug=api.slug,
                enabled=True,
                minute_limit=DEFAULT_MINUTE_LIMIT,
                ip_minute_limit=DEFAULT_IP_MINUTE_LIMIT,
                daily_limit=DEFAULT_DAILY_LIMIT,
                concurrency_limit=DEFAULT_CONCURRENCY_LIMIT,
                weight=DEFAULT_WEIGHT,
                allowed_ips=[],
            )
        return PolicyView(
            id=policy.id,
            api_slug=api.slug,
            enabled=policy.enabled,
            minute_limit=policy.minute_limit,
            ip_minute_limit=policy.ip_minute_limit,
            daily_limit=policy.daily_limit,
            concurrency_limit=policy.concurrency_limit,
            weight=policy.weight,
            allowed_ips=list(policy.allowed_ips),
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )

    def get(self, api_slug: str) -> PolicyView:
        api = self._api(api_slug)
        return self._view(api, self._policy(api))

    def upsert(self, api_slug: str, payload: PolicyUpdate) -> PolicyView:
        api = self._api(api_slug)
        policy = self._policy(api)
        if policy is None:
            policy = ApiPolicy(api_definition_id=api.id)
        values = payload.model_dump(exclude_unset=True)
        for key, value in values.items():
            setattr(policy, key, value)
        policy.updated_at = _now()
        self.session.add(policy)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(policy)
        return self._view(api, policy)

    @staticmethod
    def _deny(
        code: str,
        *,
        reason: str | None = None,
        retry_after_seconds: int | None = None,
        daily_remaining: int | None = None,
        minute_remaining: int | None = None,
        ip_minute_remaining: int | None = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            code=code,
            reason=reason or code,
            retry_after_seconds=retry_after_seconds,
            daily_remaining=daily_remaining,
            minute_remaining=minute_remaining,
            ip_minute_remaining=ip_minute_remaining,
        )

    @staticmethod
    def _ip_allowed(ip: IPvAnyAddress, allowed_ips: list[str]) -> bool:
        if not allowed_ips:
            return True
        candidate = ip_address(str(ip))
        for value in allowed_ips:
            try:
                if candidate in ip_network(value, strict=False):
                    return True
            except ValueError:
                continue
        return False

    def _static_evaluate(
        self,
        principal: ApiKeyPrincipal,
        api: ApiDefinition,
        ip: IPvAnyAddress,
    ) -> tuple[PolicyDecision, _PolicyLimits]:
        if principal.revoked_at is not None:
            return self._deny("API_KEY_REVOKED"), _PolicyLimits(0, 0, 0, 0, 0)
        if not principal.email_verified:
            return self._deny("ACCOUNT_UNVERIFIED"), _PolicyLimits(0, 0, 0, 0, 0)
        if not principal.is_active:
            return self._deny("ACCOUNT_SUSPENDED"), _PolicyLimits(0, 0, 0, 0, 0)

        policy = self._policy(api)
        if policy is None:
            limits = _PolicyLimits(
                self.default_minute_limit,
                self.default_ip_minute_limit,
                self.default_daily_limit,
                self.default_concurrency_limit,
                self.default_weight,
            )
            return (
                PolicyDecision(
                    allowed=True,
                    daily_remaining=limits.daily,
                    minute_remaining=min(limits.minute, limits.ip_minute),
                    ip_minute_remaining=limits.ip_minute,
                ),
                limits,
            )
        if not policy.enabled:
            return self._deny("POLICY_DISABLED"), _PolicyLimits(0, 0, 0, 0, 0)
        if not self._ip_allowed(ip, policy.allowed_ips):
            return self._deny("IP_NOT_ALLOWED"), _PolicyLimits(0, 0, 0, 0, 0)

        limits = _PolicyLimits(
            policy.minute_limit,
            policy.ip_minute_limit,
            policy.daily_limit,
            policy.concurrency_limit,
            policy.weight,
        )
        return (
            PolicyDecision(
                allowed=True,
                daily_remaining=limits.daily,
                minute_remaining=min(limits.minute, limits.ip_minute),
                ip_minute_remaining=limits.ip_minute,
            ),
            limits,
        )

    def _quota(self) -> QuotaService:
        if self._quota_service is None:
            self._quota_service = QuotaService(self.session)
        return self._quota_service

    def _consume_quotas(
        self,
        *,
        principal: ApiKeyPrincipal,
        api: ApiDefinition,
        ip: IPvAnyAddress,
        now: datetime,
        limits: _PolicyLimits,
        static_decision: PolicyDecision,
    ) -> PolicyDecision:
        quota = self._quota()
        rate = quota.check_minute_limits(
            user_id=principal.user_id,
            api_key_id=principal.api_key_id,
            api_slug=api.slug,
            client_ip=str(ip),
            minute_limit=limits.minute,
            ip_minute_limit=limits.ip_minute,
        )
        per_limit = rate.remaining_by_limit
        minute_remaining = (
            min(per_limit[:2]) if len(per_limit) >= 2 else rate.remaining
        )
        ip_remaining = (
            per_limit[2] if len(per_limit) >= 3 else rate.remaining
        )
        if not rate.allowed:
            daily_remaining = quota.daily_remaining(
                now=now,
                user_id=principal.user_id,
                api_key_id=principal.api_key_id,
                api_slug=api.slug,
                daily_limit=limits.daily,
            )
            reason = "IP_MINUTE_LIMIT" if rate.failed_index == 3 else "MINUTE_LIMIT"
            return self._deny(
                reason,
                daily_remaining=daily_remaining,
                minute_remaining=minute_remaining,
                ip_minute_remaining=ip_remaining,
                retry_after_seconds=rate.retry_after_seconds,
            )

        daily = quota.charge_daily(
            now=now,
            user_id=principal.user_id,
            api_key_id=principal.api_key_id,
            api_slug=api.slug,
            daily_limit=limits.daily,
            weight=limits.weight,
        )
        if not daily.allowed:
            return self._deny(
                "DAILY_QUOTA_EXCEEDED",
                daily_remaining=daily.remaining,
                minute_remaining=minute_remaining,
                ip_minute_remaining=ip_remaining,
                retry_after_seconds=daily.retry_after_seconds,
            )
        return PolicyDecision(
            allowed=True,
            daily_remaining=daily.remaining,
            minute_remaining=minute_remaining,
            ip_minute_remaining=ip_remaining,
            code=static_decision.code,
            reason=static_decision.reason,
        )

    def evaluate(
        self,
        principal: ApiKeyPrincipal,
        api: ApiDefinition,
        ip: IPvAnyAddress,
        now: datetime,
    ) -> PolicyDecision:
        static_decision, limits = self._static_evaluate(principal, api, ip)
        if not static_decision.allowed:
            return static_decision
        # Task 4 callers without a Redis dependency retain the original pure
        # policy behavior. Task 5 callers inject Redis and get fail-closed,
        # atomic quota accounting.
        if self.redis is None:
            return static_decision
        consumed = self._consume_quotas(
            principal=principal,
            api=api,
            ip=ip,
            now=now,
            limits=limits,
            static_decision=static_decision,
        )
        if not consumed.allowed:
            return consumed
        admission = _PolicyAdmission(
            token=secrets.token_urlsafe(32),
            user_id=principal.user_id,
            api_key_id=principal.api_key_id,
            api_slug=api.slug,
            client_ip=str(ip),
            concurrency_limit=limits.concurrency,
            expires_at=_utc(now) + timedelta(seconds=ADMISSION_TTL_SECONDS),
            daily_remaining=consumed.daily_remaining,
            minute_remaining=consumed.minute_remaining,
            ip_minute_remaining=consumed.ip_minute_remaining,
        )
        with self._admission_lock:
            self._admissions[id(admission)] = admission
        consumed._admission = admission
        return consumed

    def _take_admission(
        self,
        *,
        decision: PolicyDecision | None,
        principal: ApiKeyPrincipal,
        api: ApiDefinition,
        ip: IPvAnyAddress,
        now: datetime,
    ) -> _PolicyAdmission:
        if decision is None:
            raise PolicyDenied(self._deny("ADMISSION_REQUIRED"))
        if not decision.allowed:
            raise PolicyDenied(self._deny("INVALID_ADMISSION"))
        admission = decision._admission
        if not isinstance(admission, _PolicyAdmission):
            raise PolicyDenied(self._deny("INVALID_ADMISSION"))
        with self._admission_lock:
            stored = self._admissions.get(id(admission))
            if stored is None:
                raise PolicyDenied(self._deny("ADMISSION_REUSED"))
            if stored is not admission:
                raise PolicyDenied(self._deny("INVALID_ADMISSION"))
            current = _utc(now)
            if current >= admission.expires_at:
                self._admissions.pop(id(admission), None)
                raise PolicyDenied(self._deny("ADMISSION_EXPIRED"))
            if (
                admission.user_id != principal.user_id
                or admission.api_key_id != principal.api_key_id
                or admission.api_slug != api.slug
                or admission.client_ip != str(ip)
            ):
                raise PolicyDenied(self._deny("ADMISSION_CONTEXT_MISMATCH"))
            self._admissions.pop(id(admission), None)
            return admission

    @staticmethod
    def _preserve_original_error(
        original: BaseException,
        cleanup_error: BaseException,
    ) -> None:
        try:
            original.add_note(
                "quota lease cleanup failed while preserving the original "
                f"{type(original).__name__}: {type(cleanup_error).__name__}"
            )
        except Exception:
            pass

    def acquire(
        self,
        principal: ApiKeyPrincipal,
        api: ApiDefinition,
        ip: IPvAnyAddress,
        now: datetime | None = None,
        *,
        decision: PolicyDecision | None = None,
    ) -> QuotaLease:
        """Acquire only concurrency using a one-time evaluated admission."""

        current = _utc(now or _now())
        admission = self._take_admission(
            decision=decision,
            principal=principal,
            api=api,
            ip=ip,
            now=current,
        )
        static_decision, _limits = self._static_evaluate(principal, api, ip)
        if not static_decision.allowed:
            raise PolicyDenied(static_decision)
        quota = self._quota()
        lease: QuotaLease | None = None
        try:
            lease = quota.acquire_concurrency(
                user_id=principal.user_id,
                api_key_id=principal.api_key_id,
                api_slug=api.slug,
                concurrency_limit=admission.concurrency_limit,
                now=current,
            )
        except ConcurrencyLimitExceeded as exc:
            denied = self._deny(
                "CONCURRENCY_LIMIT",
                daily_remaining=admission.daily_remaining,
                minute_remaining=admission.minute_remaining,
                ip_minute_remaining=admission.ip_minute_remaining,
                retry_after_seconds=exc.retry_after_seconds,
            )
            raise PolicyDenied(denied) from exc
        except BaseException as exc:
            if lease is not None and not lease.released:
                try:
                    lease.release()
                except Exception as cleanup_error:
                    self._preserve_original_error(exc, cleanup_error)
            raise
        return lease
