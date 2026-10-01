import uuid
from datetime import UTC, date, datetime

from pydantic import EmailStr
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    UniqueConstraint,
)
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    email_verified: bool = Field(default=False, nullable=False, index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)
    api_keys: list[ApiKey] = Relationship(back_populates="user", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    email_verified: bool = False
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class OAuthIdentity(SQLModel, table=True):
    __tablename__ = "oauth_identity"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_oauth_identity_provider_subject",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    provider: str = Field(default="github", max_length=32, nullable=False)
    provider_subject: str = Field(max_length=255, nullable=False, index=True)
    email: EmailStr = Field(max_length=255, nullable=False)
    email_verified: bool = Field(default=False, nullable=False)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class EmailVerificationToken(SQLModel, table=True):
    __tablename__ = "email_verification_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    token_hash: str = Field(max_length=64, nullable=False, unique=True)
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True), nullable=False
    )  # type: ignore
    consumed_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    token_hash: str = Field(max_length=64, nullable=False, unique=True)
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True), nullable=False
    )  # type: ignore
    consumed_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ApiKey(SQLModel, table=True):
    """A user-owned API credential; the raw secret is never a model field."""

    __tablename__ = "api_key"
    __table_args__ = (
        UniqueConstraint(
            "key_hash",
            "hash_version",
            name="uq_api_key_key_hash_version",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    prefix: str = Field(max_length=32, index=True, nullable=False)
    key_hash: str = Field(max_length=64, index=True, nullable=False)
    hash_version: int = Field(default=1, nullable=False)
    label: str | None = Field(default=None, max_length=100)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    user: User | None = Relationship(back_populates="api_keys")


class ApiDefinition(SQLModel, table=True):
    """Curated API metadata; execution is owned by a fixed adapter name."""

    __tablename__ = "api_definition"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_api_definition_slug"),
        CheckConstraint("auth_type = 'api_key'", name="ck_api_definition_auth_type"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(max_length=100, index=True, nullable=False)
    name: str = Field(max_length=255, nullable=False)
    summary: str = Field(max_length=1000, nullable=False)
    category: str = Field(max_length=64, index=True, nullable=False)
    method: str = Field(max_length=16, nullable=False)
    path: str = Field(max_length=255, nullable=False)
    auth_type: str = Field(default="api_key", max_length=32, nullable=False)
    parameters: list[dict[str, object]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    response_schema: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    error_codes: list[dict[str, object]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    examples: list[dict[str, object]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    visibility: str = Field(default="public", max_length=32, index=True, nullable=False)
    status: str = Field(default="trial", max_length=32, index=True, nullable=False)
    is_free: bool = Field(default=True, nullable=False)
    source_label: str = Field(default="Yeyu API", max_length=255, nullable=False)
    adapter_name: str = Field(max_length=128, nullable=False)
    provider_ref: str | None = Field(default=None, max_length=255)
    cache_rules: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ApiPolicy(SQLModel, table=True):
    """Database-backed policy defaults consumed by the future quota layer."""

    __tablename__ = "api_policy"
    __table_args__ = (
        UniqueConstraint(
            "api_definition_id",
            name="uq_api_policy_api_definition_id",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    api_definition_id: uuid.UUID = Field(
        foreign_key="api_definition.id", nullable=False, index=True
    )
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    api_key_id: uuid.UUID | None = Field(
        default=None, foreign_key="api_key.id", index=True
    )
    enabled: bool = Field(default=True, nullable=False)
    minute_limit: int = Field(default=60, nullable=False)
    ip_minute_limit: int = Field(default=60, nullable=False)
    daily_limit: int = Field(default=1000, nullable=False)
    concurrency_limit: int = Field(default=1, nullable=False)
    weight: int = Field(default=1, nullable=False)
    allowed_ips: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UsageDaily(SQLModel, table=True):
    """Authoritative UTC-day weighted usage for one user/key/API tuple."""

    __tablename__ = "usage_daily"
    __table_args__ = (
        UniqueConstraint(
            "utc_date",
            "user_id",
            "api_key_id",
            "api_slug",
            name="uq_usage_daily_dimension",
        ),
        CheckConstraint(
            "request_count >= 0",
            name="ck_usage_daily_request_count_nonnegative",
        ),
        CheckConstraint(
            "weighted_units >= 0",
            name="ck_usage_daily_weighted_units_nonnegative",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    utc_date: date = Field(sa_type=Date, nullable=False, index=True)  # type: ignore
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, index=True
    )
    api_key_id: uuid.UUID = Field(
        foreign_key="api_key.id", nullable=False, index=True
    )
    api_slug: str = Field(max_length=100, nullable=False, index=True)
    request_count: int = Field(default=0, nullable=False)
    weighted_units: int = Field(default=0, nullable=False)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CacheEntry(SQLModel, table=True):
    """Redis-compatible cache metadata retained for future durable indexing."""

    __tablename__ = "cache_entry"
    __table_args__ = (
        UniqueConstraint(
            "api_slug",
            "params_fingerprint",
            name="uq_cache_entry_api_params",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    api_slug: str = Field(max_length=100, nullable=False, index=True)
    params_fingerprint: str = Field(max_length=64, nullable=False, index=True)
    payload: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    data_at: datetime = Field(
        sa_type=DateTime(timezone=True), nullable=False  # type: ignore
    )
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True), nullable=False  # type: ignore
    )
    stale_until: datetime = Field(
        sa_type=DateTime(timezone=True), nullable=False  # type: ignore
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
