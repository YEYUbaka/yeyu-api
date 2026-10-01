from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.models import ApiKey, User
from app.schemas.api_keys import ApiKeyPrincipal, ApiKeyPublic, CreatedApiKey


class ApiKeyError(Exception):
    """Base class for API-key lifecycle failures."""


class ApiKeyNotFound(ApiKeyError):
    pass


class ApiKeyOwnershipError(ApiKeyError):
    pass


class ApiKeyAlreadyRevoked(ApiKeyError):
    pass


class ApiKeyUserNotFound(ApiKeyError):
    pass


class AccountUnverifiedError(ApiKeyError):
    pass


class AccountSuspendedError(ApiKeyError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


class ApiKeyService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_user(self, user_id: UUID) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise ApiKeyUserNotFound
        return user

    def _ensure_key_eligible(self, user_id: UUID) -> User:
        user = self._get_user(user_id)
        if not user.is_active:
            raise AccountSuspendedError
        if not user.email_verified:
            raise AccountUnverifiedError
        return user

    @staticmethod
    def _created_response(record: ApiKey, raw_key: str) -> CreatedApiKey:
        created_at = record.created_at or _now()
        return CreatedApiKey(
            id=record.id,
            prefix=record.prefix,
            secret=raw_key,
            created_at=created_at,
        )

    @staticmethod
    def _new_record(user_id: UUID, label: str | None) -> tuple[ApiKey, str]:
        raw_key = security.generate_api_key()
        hash_version = settings.API_KEY_PEPPER_VERSION
        record = ApiKey(
            user_id=user_id,
            prefix=security.get_api_key_prefix(raw_key),
            key_hash=security.hash_api_key(raw_key, version=hash_version),
            hash_version=hash_version,
            label=label,
        )
        return record, raw_key

    def create(self, user_id: UUID, label: str | None) -> CreatedApiKey:
        self._ensure_key_eligible(user_id)
        record, raw_key = self._new_record(user_id, label)
        self.session.add(record)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(record)
        return self._created_response(record, raw_key)

    def list(self, user_id: UUID) -> list[ApiKeyPublic]:
        self._get_user(user_id)
        records = self.session.exec(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        ).all()
        return [ApiKeyPublic.model_validate(record) for record in records]

    def _owned_key(self, key_id: UUID, user_id: UUID) -> ApiKey:
        record = self.session.get(ApiKey, key_id)
        if record is None:
            raise ApiKeyNotFound
        if record.user_id != user_id:
            raise ApiKeyOwnershipError
        return record

    def revoke(self, key_id: UUID, user_id: UUID) -> None:
        record = self._owned_key(key_id, user_id)
        if record.revoked_at is not None:
            return
        record.revoked_at = _now()
        self.session.add(record)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def rotate(self, key_id: UUID, user_id: UUID) -> CreatedApiKey:
        """Revoke and replace a key in one transaction.

        A failed flush or commit rolls back both the old-row revocation and the
        new-row insert, leaving the old credential usable.
        """
        self._ensure_key_eligible(user_id)
        old_record = self._owned_key(key_id, user_id)
        if old_record.revoked_at is not None:
            raise ApiKeyAlreadyRevoked

        replacement, raw_key = self._new_record(user_id, old_record.label)
        try:
            old_record.revoked_at = _now()
            self.session.add(old_record)
            self.session.add(replacement)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(replacement)
        return self._created_response(replacement, raw_key)

    def authenticate(self, raw_key: str) -> ApiKeyPrincipal | None:
        if not raw_key:
            return None
        prefix = security.get_api_key_prefix(raw_key)
        records = self.session.exec(
            select(ApiKey).where(ApiKey.prefix == prefix)
        ).all()
        for record in records:
            if not security.verify_api_key_hash(
                raw_key,
                record.key_hash,
                version=record.hash_version,
            ):
                continue
            user = self.session.get(User, record.user_id)
            if user is None:
                return None
            return ApiKeyPrincipal(
                key_id=record.id,
                user_id=record.user_id,
                prefix=record.prefix,
                hash_version=record.hash_version,
                email_verified=user.email_verified,
                is_active=user.is_active,
                revoked_at=record.revoked_at,
            )
        return None
