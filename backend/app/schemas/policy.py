from __future__ import annotations

from datetime import datetime
from ipaddress import ip_network
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_allowed_ips(value: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in value:
        candidate = item.strip()
        if not candidate:
            raise ValueError("allowed_ips entries must not be empty")
        try:
            normalized.append(str(ip_network(candidate, strict=False)))
        except ValueError as exc:
            raise ValueError(
                "allowed_ips entries must be valid IP addresses or CIDR networks"
            ) from exc
    return normalized


class PolicyUpdate(BaseModel):
    enabled: bool | None = None
    minute_limit: int | None = Field(default=None, ge=0, le=1_000_000)
    ip_minute_limit: int | None = Field(default=None, ge=0, le=1_000_000)
    daily_limit: int | None = Field(default=None, ge=0, le=10_000_000)
    concurrency_limit: int | None = Field(default=None, ge=1, le=100_000)
    weight: int | None = Field(default=None, ge=1, le=1_000)
    allowed_ips: list[str] | None = None

    @field_validator("allowed_ips")
    @classmethod
    def validate_allowed_ips(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_allowed_ips(value) if value is not None else None


class PolicyView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    api_slug: str
    enabled: bool
    minute_limit: int
    ip_minute_limit: int
    daily_limit: int
    concurrency_limit: int
    weight: int
    allowed_ips: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PolicyDecision(BaseModel):
    allowed: bool
    code: str | None = None
    reason: str | None = None
    retry_after_seconds: int | None = None
    daily_remaining: int | None = None
    minute_remaining: int | None = None
    ip_minute_remaining: int | None = None


class PolicyErrorResponse(BaseModel):
    error: dict[str, Any]
