from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator
from sqlmodel import SQLModel

CATALOG_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
ALLOWED_ADAPTER_NAMES = frozenset({"builtin-tools"})
ALLOWED_PROVIDER_REFS = frozenset(
    {
        "provider:internal-tools",
        "builtin-tools:time",
        "builtin-tools:uuid",
    }
)
ALLOWED_STATUS_VALUES = frozenset(
    {"trial", "healthy", "published", "draft", "disabled"}
)


def _validate_internal_path(value: str) -> str:
    value = value.strip()
    if (
        not value.startswith("/")
        or value.startswith("//")
        or "://" in value
        or "\\" in value
        or "%" in value
        or "?" in value
        or "#" in value
    ):
        raise ValueError("path must be an internal absolute API path")
    if ".." in value:
        raise ValueError("path traversal is not allowed")
    return value


def _validate_provider_ref(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if (
        not value
        or value not in ALLOWED_PROVIDER_REFS
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}", value)
    ):
        raise ValueError("provider_ref must be an internal reference")
    return value


def _validate_metadata_tree(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        raise ValueError("catalog metadata nesting is too deep")
    if isinstance(value, dict):
        if len(value) > 128:
            raise ValueError("catalog metadata object is too large")
        for key, nested in value.items():
            if not isinstance(key, str) or len(key) > 128:
                raise ValueError("catalog metadata keys must be short strings")
            _validate_metadata_tree(nested, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > 64:
            raise ValueError("catalog metadata list is too large")
        for nested in value:
            _validate_metadata_tree(nested, depth=depth + 1)
    elif not isinstance(value, (str, int, float, bool, type(None))):
        raise ValueError("catalog metadata must be JSON-compatible")
    return value


def _validate_adapter_name(value: str) -> str:
    value = value.strip()
    if value not in ALLOWED_ADAPTER_NAMES:
        raise ValueError("adapter_name is not in the fixed adapter allowlist")
    return value


def _validate_status(value: str) -> str:
    value = value.strip().casefold()
    if value not in ALLOWED_STATUS_VALUES:
        raise ValueError("status is not in the fixed status allowlist")
    return value


def _validate_metadata(value: Any) -> Any:
    return _validate_metadata_tree(value)


class CatalogItem(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    summary: str
    category: str
    method: str
    path: str
    auth_type: str
    is_free: bool
    status: str
    updated_at: datetime | None = None


class CatalogPage(SQLModel):
    data: list[CatalogItem]
    count: int
    page: int
    page_size: int


class ApiAuth(SQLModel):
    type: Literal["api_key"]
    header: str = "X-API-Key"


class ApiDetail(SQLModel):
    slug: str
    name: str
    summary: str
    category: str
    method: str
    path: str
    auth: ApiAuth
    is_free: bool
    status: str
    updated_at: datetime | None = None
    parameters: list[dict[str, Any]]
    response_schema: dict[str, Any]
    errors: list[dict[str, Any]]
    examples: list[dict[str, Any]]
    source: str
    cache_rules: dict[str, Any]


class ApiDefinitionCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    summary: str = Field(default="", max_length=1000)
    category: str = Field(min_length=1, max_length=64)
    method: str = Field(default="GET", min_length=1, max_length=16)
    path: str = Field(max_length=255)
    auth_type: Literal["api_key"] = "api_key"
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    response_schema: dict[str, Any] = Field(default_factory=dict)
    error_codes: list[dict[str, Any]] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    visibility: str = Field(default="public", min_length=1, max_length=32)
    status: str = Field(default="trial", min_length=1, max_length=32)
    is_free: bool = True
    source: str = Field(default="Yeyu API", max_length=255)
    adapter_name: str = Field(min_length=1, max_length=128)
    provider_ref: str | None = Field(default=None, max_length=255)
    cache_rules: dict[str, Any] = Field(default_factory=dict)

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _validate_internal_path(value)

    @field_validator("provider_ref")
    @classmethod
    def validate_provider_ref(cls, value: str | None) -> str | None:
        return _validate_provider_ref(value)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return _validate_status(value)

    @field_validator("adapter_name")
    @classmethod
    def validate_adapter_name(cls, value: str) -> str:
        return _validate_adapter_name(value)

    @field_validator(
        "parameters", "response_schema", "error_codes", "examples", "cache_rules"
    )
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        return _validate_metadata(value)


class ApiDefinitionUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=1000)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    method: str | None = Field(default=None, min_length=1, max_length=16)
    path: str | None = Field(default=None, max_length=255)
    auth_type: Literal["api_key"] | None = None
    parameters: list[dict[str, Any]] | None = None
    response_schema: dict[str, Any] | None = None
    error_codes: list[dict[str, Any]] | None = None
    examples: list[dict[str, Any]] | None = None
    visibility: str | None = Field(default=None, min_length=1, max_length=32)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    is_free: bool | None = None
    source: str | None = Field(default=None, max_length=255)
    adapter_name: str | None = Field(default=None, min_length=1, max_length=128)
    provider_ref: str | None = Field(default=None, max_length=255)
    cache_rules: dict[str, Any] | None = None

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str | None) -> str | None:
        return _validate_internal_path(value) if value is not None else None

    @field_validator("provider_ref")
    @classmethod
    def validate_provider_ref(cls, value: str | None) -> str | None:
        return _validate_provider_ref(value)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        return _validate_status(value) if value is not None else None

    @field_validator("adapter_name")
    @classmethod
    def validate_adapter_name(cls, value: str | None) -> str | None:
        return _validate_adapter_name(value) if value is not None else None

    @field_validator(
        "parameters", "response_schema", "error_codes", "examples", "cache_rules"
    )
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        return _validate_metadata(value)


class ApiDefinitionAdmin(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    summary: str
    category: str
    method: str
    path: str
    auth_type: str
    parameters: list[dict[str, Any]]
    response_schema: dict[str, Any]
    error_codes: list[dict[str, Any]]
    examples: list[dict[str, Any]]
    visibility: str
    status: str
    is_free: bool
    source: str
    adapter_name: str
    provider_ref: str | None = None
    cache_rules: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None
