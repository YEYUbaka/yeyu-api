from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.catalog import ApiDefinitionAdmin

CheckStatus = Literal["ok", "failed"]
AdminHealthStatus = Literal["ready", "not_ready"]


class AdminCatalogPage(BaseModel):
    data: list[ApiDefinitionAdmin]
    count: int
    page: int
    page_size: int


class AuditEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None = None
    request_id: str | None = None
    action: str
    object_type: str
    object_id: str
    outcome: str
    details: dict[str, object]
    created_at: datetime


class AuditEventPage(BaseModel):
    data: list[AuditEventPublic]
    count: int
    page: int
    page_size: int


class HealthChecks(BaseModel):
    database: CheckStatus
    redis: CheckStatus
    migrations: CheckStatus


class AdminHealthView(BaseModel):
    status: AdminHealthStatus
    checks: HealthChecks


class AdminPageQuery(BaseModel):
    page: int = Field(default=1, ge=1, le=100_000)
    page_size: int = Field(default=50, ge=1, le=100)
