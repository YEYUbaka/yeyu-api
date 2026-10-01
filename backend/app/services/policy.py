from __future__ import annotations

from datetime import UTC, datetime
from ipaddress import ip_address, ip_network
from typing import Any

from pydantic import IPvAnyAddress
from sqlmodel import Session, select

from app.models import ApiDefinition, ApiPolicy
from app.schemas.api_keys import ApiKeyPrincipal
from app.schemas.policy import PolicyDecision, PolicyUpdate, PolicyView


class PolicyError(Exception):
    """Base class for policy configuration failures."""


class PolicyApiNotFound(PolicyError):
    pass


DEFAULT_MINUTE_LIMIT = 60
DEFAULT_IP_MINUTE_LIMIT = 60
DEFAULT_DAILY_LIMIT = 1000
DEFAULT_CONCURRENCY_LIMIT = 1
DEFAULT_WEIGHT = 1


def _now() -> datetime:
    return datetime.now(UTC)


class PolicyService:
    def __init__(
        self,
        session: Session,
        redis: Any | None = None,
        *,
        minute_limit: int | None = None,
        daily_limit: int | None = None,
    ) -> None:
        # Redis is accepted for the Task 5 constructor contract but is not used
        # until that task owns atomic quota accounting.
        self.session = session
        self.redis = redis
        self.default_minute_limit = (
            DEFAULT_MINUTE_LIMIT if minute_limit is None else minute_limit
        )
        self.default_daily_limit = (
            DEFAULT_DAILY_LIMIT if daily_limit is None else daily_limit
        )

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
    ) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            code=code,
            reason=reason or code,
            retry_after_seconds=retry_after_seconds,
            daily_remaining=daily_remaining,
            minute_remaining=minute_remaining,
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

    def evaluate(
        self,
        principal: ApiKeyPrincipal,
        api: ApiDefinition,
        ip: IPvAnyAddress,
        now: datetime,
    ) -> PolicyDecision:
        del now
        if principal.revoked_at is not None:
            return self._deny("API_KEY_REVOKED")
        if not principal.email_verified:
            return self._deny("ACCOUNT_UNVERIFIED")
        if not principal.is_active:
            return self._deny("ACCOUNT_SUSPENDED")

        policy = self._policy(api)
        if policy is None:
            return PolicyDecision(
                allowed=True,
                daily_remaining=self.default_daily_limit,
                minute_remaining=self.default_minute_limit,
            )
        if not policy.enabled:
            return self._deny("POLICY_DISABLED")
        if not self._ip_allowed(ip, policy.allowed_ips):
            return self._deny("IP_NOT_ALLOWED")

        return PolicyDecision(
            allowed=True,
            daily_remaining=policy.daily_limit,
            minute_remaining=min(policy.minute_limit, policy.ip_minute_limit),
        )
