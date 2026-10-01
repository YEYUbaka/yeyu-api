from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

API_ERROR_CODES = frozenset(
    {
        "API_KEY_REQUIRED",
        "API_KEY_INVALID",
        "API_KEY_REVOKED",
        "ACCOUNT_UNVERIFIED",
        "ACCOUNT_SUSPENDED",
        "RATE_LIMITED",
        "DAILY_QUOTA_EXCEEDED",
    }
)


class ApiKeyCreate(BaseModel):
    label: str | None = Field(default=None, max_length=100)


class CreatedApiKey(BaseModel):
    """The only response shape that contains a complete raw API secret."""

    id: UUID
    prefix: str
    secret: str
    created_at: datetime


class ApiKeyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prefix: str
    label: str | None = None
    hash_version: int
    created_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeysPublic(BaseModel):
    data: list[ApiKeyPublic]
    count: int


class CreatedApiKeyResponse(BaseModel):
    data: CreatedApiKey


class ApiKeyPrincipal(BaseModel):
    """Non-secret identity attached to a successfully matched API key."""

    key_id: UUID
    user_id: UUID
    prefix: str
    hash_version: int
    email_verified: bool = True
    is_active: bool = True
    revoked_at: datetime | None = None

    @property
    def id(self) -> UUID:
        return self.key_id

    @property
    def api_key_id(self) -> UUID:
        return self.key_id

    @property
    def account_verified(self) -> bool:
        return self.email_verified

    @property
    def account_suspended(self) -> bool:
        return not self.is_active

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ApiErrorResponse(BaseModel):
    error: ApiErrorDetail
