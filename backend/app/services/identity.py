from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import EmailStr, TypeAdapter, ValidationError
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.models import (
    EmailVerificationToken,
    OAuthIdentity,
    PasswordResetToken,
    User,
)
from app.utils import generate_email_verification_email, generate_reset_password_email
from app.utils import send_email as default_send_email


class IdentityError(Exception):
    """Base class for account and identity failures."""


class InvalidVerificationToken(IdentityError):
    """The supplied token is unknown, expired, or already consumed."""


class IdentityConflict(IdentityError):
    """The provider identity is already owned by another account."""


class UnverifiedOAuthEmail(IdentityError):
    """GitHub did not attest the email address."""


class UserNotFound(IdentityError):
    """The requested local account does not exist."""


class RateLimitExceeded(IdentityError):
    """The identity endpoint exceeded its short-window request limit."""


class RateLimitUnavailable(IdentityError):
    """The shared rate-limit store is unavailable; fail closed."""


class RedisRateLimiter:
    """Use one atomic Redis script for short-window identity throttling."""

    _increment_script = (
        "local count = redis.call('INCR', KEYS[1]); "
        "if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; "
        "return count"
    )

    def __init__(self, client: Redis[str] | Any | None = None) -> None:
        if client is not None:
            self.client = client
            return
        try:
            self.client = Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS,
                socket_timeout=settings.GITHUB_OAUTH_TIMEOUT_SECONDS,
                decode_responses=True,
            )
        except (RedisError, OSError, ValueError) as exc:
            raise RateLimitUnavailable from exc

    def check(
        self,
        *,
        scope: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        key = f"yeyu:identity:rate:{scope}:{digest}"
        try:
            count = int(
                self.client.eval(
                    self._increment_script,
                    1,
                    key,
                    window_seconds,
                )
            )
        except (RedisError, OSError, TypeError, ValueError) as exc:
            raise RateLimitUnavailable from exc
        if count > limit:
            raise RateLimitExceeded


def _now() -> datetime:
    return datetime.now(UTC)


def _email_key(email: str) -> str:
    return email.strip().casefold()


_email_adapter = TypeAdapter(EmailStr)


def _validated_email(email: str) -> str:
    try:
        return str(_email_adapter.validate_python(email))
    except ValidationError as exc:
        raise UnverifiedOAuthEmail from exc


class IdentityService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def link_github(
        self,
        user_id: UUID,
        provider_subject: str,
        email: str,
        email_verified: bool,
        *,
        allow_active_binding: bool = False,
    ) -> OAuthIdentity:
        user = self.session.get(User, user_id)
        if user is None:
            raise UserNotFound
        if not provider_subject or len(provider_subject) > 255:
            raise IdentityConflict
        if not email_verified:
            raise UnverifiedOAuthEmail
        email = _validated_email(email)

        existing = self.session.exec(
            select(OAuthIdentity).where(
                OAuthIdentity.provider == "github",
                OAuthIdentity.provider_subject == provider_subject,
            )
        ).first()
        if existing is not None:
            if existing.user_id != user_id:
                raise IdentityConflict
            return existing

        normalized_email = _email_key(email)
        current_email = _email_key(str(user.email))
        matching_user = self.session.exec(
            select(User).where(func.lower(User.email) == normalized_email)
        ).first()
        if matching_user is not None and matching_user.id != user_id:
            raise IdentityConflict
        if not allow_active_binding and (
            matching_user is None
            or not user.email_verified
            or current_email != normalized_email
        ):
            raise IdentityConflict

        identity = OAuthIdentity(
            user_id=user_id,
            provider="github",
            provider_subject=provider_subject,
            email=email,
            email_verified=True,
        )
        self.session.add(identity)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raced_identity = self.session.exec(
                select(OAuthIdentity).where(
                    OAuthIdentity.provider == "github",
                    OAuthIdentity.provider_subject == provider_subject,
                )
            ).first()
            if raced_identity is not None and raced_identity.user_id != user_id:
                raise IdentityConflict from exc
            raise
        self.session.refresh(identity)
        return identity

    def resolve_github_login(
        self,
        provider_subject: str,
        email: str,
        email_verified: bool,
    ) -> tuple[User, OAuthIdentity]:
        existing_identity = self.session.exec(
            select(OAuthIdentity).where(
                OAuthIdentity.provider == "github",
                OAuthIdentity.provider_subject == provider_subject,
            )
        ).first()
        if existing_identity is not None:
            user = self.session.get(User, existing_identity.user_id)
            if user is None:
                raise UserNotFound
            return user, existing_identity

        if not email_verified:
            raise UnverifiedOAuthEmail

        email = _validated_email(email)
        normalized_email = _email_key(email)
        user = self.session.exec(
            select(User).where(func.lower(User.email) == normalized_email)
        ).first()
        if user is not None:
            if not user.email_verified:
                raise IdentityConflict
            identity = self.link_github(
                user.id,
                provider_subject,
                email,
                email_verified=True,
            )
            return user, identity

        # Do not create an unrequested GitHub-only account. The user must
        # first create and verify the email account, then explicitly bind the
        # provider identity after re-authentication.
        raise IdentityConflict


class _OpaqueTokenService:
    model: Any
    purpose: str

    def __init__(
        self,
        *,
        session: Session,
        mailer: Callable[..., None] = default_send_email,
        now: Callable[[], datetime] = _now,
    ) -> None:
        self.session = session
        self.mailer = mailer
        self.now = now

    def _issue(
        self,
        *,
        user_id: UUID,
        expires_at: datetime,
        token_factory: Callable[[], str] | None = None,
    ) -> str:
        if self.session.get(User, user_id) is None:
            raise UserNotFound
        now = self.now()
        self.session.exec(
            update(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.consumed_at.is_(None),
            )
            .values(consumed_at=now)
            .execution_options(synchronize_session=False)
        )
        raw_token = (token_factory or security.generate_opaque_token)()
        token = self.model(
            user_id=user_id,
            token_hash=security.hash_opaque_token(raw_token, purpose=self.purpose),
            expires_at=expires_at,
        )
        self.session.add(token)
        self.session.commit()
        return raw_token

    def _consume(self, raw_token: str) -> UUID:
        if not raw_token:
            raise InvalidVerificationToken
        now = self.now()
        token_hash = security.hash_opaque_token(raw_token, purpose=self.purpose)
        result = self.session.exec(
            update(self.model)
            .where(
                self.model.token_hash == token_hash,
                self.model.consumed_at.is_(None),
                self.model.expires_at > now,
            )
            .values(consumed_at=now)
            .execution_options(synchronize_session=False)
        )
        if getattr(result, "rowcount", 0) != 1:
            self.session.rollback()
            raise InvalidVerificationToken
        token = self.session.exec(
            select(self.model).where(self.model.token_hash == token_hash)
        ).first()
        if token is None:
            self.session.rollback()
            raise InvalidVerificationToken
        return token.user_id


class EmailVerificationService(_OpaqueTokenService):
    model = EmailVerificationToken
    purpose = "email-verification"

    def __init__(
        self,
        *,
        session: Session,
        mailer: Callable[..., None] = default_send_email,
        now: Callable[[], datetime] = _now,
    ) -> None:
        super().__init__(session=session, mailer=mailer, now=now)
        self.identity = IdentityService(session)

    def issue_verification_token(self, user_id: UUID) -> str:
        return self._issue(
            user_id=user_id,
            expires_at=self.now()
            + timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES),
        )

    def request(self, user_id: UUID) -> None:
        user = self.session.get(User, user_id)
        if user is None:
            return
        raw_token = self.issue_verification_token(user_id)
        if not settings.emails_enabled:
            return
        email_data = generate_email_verification_email(
            email_to=str(user.email),
            email=str(user.email),
            token=raw_token,
        )
        self.mailer(
            email_to=str(user.email),
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

    def verify(self, raw_token: str) -> User:
        user_id = self._consume(raw_token)
        user = self.session.get(User, user_id)
        if user is None:
            self.session.rollback()
            raise InvalidVerificationToken
        user.email_verified = True
        self.session.add(user)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(user)
        return user

    def issue_password_reset_token(self, user_id: UUID) -> str:
        service = PasswordResetService(
            session=self.session,
            mailer=self.mailer,
            now=self.now,
        )
        return service.issue_token(user_id)

    def consume_password_reset_token(self, raw_token: str, *, commit: bool = False) -> UUID:
        service = PasswordResetService(
            session=self.session,
            mailer=self.mailer,
            now=self.now,
        )
        return service.consume_token(raw_token, commit=commit)


class PasswordResetService(_OpaqueTokenService):
    model = PasswordResetToken
    purpose = "password-reset"

    def issue_token(self, user_id: UUID) -> str:
        return self._issue(
            user_id=user_id,
            expires_at=self.now()
            + timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS),
        )

    def request(self, user_id: UUID) -> None:
        user = self.session.get(User, user_id)
        if user is None:
            return
        raw_token = self.issue_token(user_id)
        if not settings.emails_enabled:
            return
        email_data = generate_reset_password_email(
            email_to=str(user.email),
            email=str(user.email),
            token=raw_token,
        )
        self.mailer(
            email_to=str(user.email),
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

    def consume_token(self, raw_token: str, *, commit: bool = False) -> UUID:
        user_id = self._consume(raw_token)
        if commit:
            try:
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise
        return user_id

    def consume_legacy_token(
        self, raw_token: str, email: str, *, commit: bool = False
    ) -> UUID:
        """Consume one pre-Task-2 JWT while migrating existing reset links.

        The JWT is verified by the caller. This method records only its hash,
        so a legacy link is still single-use after its first successful use.
        """
        if not raw_token:
            raise InvalidVerificationToken
        user = self.session.exec(
            select(User).where(func.lower(User.email) == _email_key(email))
        ).first()
        if user is None:
            raise InvalidVerificationToken
        token_hash = security.hash_opaque_token(raw_token, purpose=self.purpose)
        existing = self.session.exec(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        ).first()
        if existing is not None:
            raise InvalidVerificationToken
        now = self.now()
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now,
            consumed_at=now,
        )
        self.session.add(token)
        try:
            if commit:
                self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise InvalidVerificationToken from exc
        return user.id
