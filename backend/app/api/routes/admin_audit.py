from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import AuditEvent
from app.schemas.admin import AuditEventPage, AuditEventPublic
from app.services.redaction import RedactionService

router = APIRouter(
    prefix="/admin/audit",
    tags=["admin-audit"],
    dependencies=[Depends(get_current_active_superuser)],
)

_FILTER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
FilterValue = Annotated[str | None, Query(max_length=64)]


def _validate_filter(value: str | None, name: str) -> str | None:
    if value is not None and _FILTER_PATTERN.fullmatch(value) is None:
        raise HTTPException(status_code=422, detail=f"Invalid {name} filter")
    return value


def _public_event(event: AuditEvent) -> AuditEventPublic:
    return AuditEventPublic(
        id=event.id,
        actor_id=event.actor_id,
        request_id=event.request_id,
        action=event.action,
        object_type=event.object_type,
        object_id=event.object_id,
        outcome=event.outcome,
        details=RedactionService.sanitize_metadata(event.details),
        created_at=event.created_at,
    )


@router.get("", response_model=AuditEventPage)
def read_audit_events(
    session: SessionDep,
    page: int = Query(default=1, ge=1, le=100_000),
    page_size: int = Query(default=50, ge=1, le=100),
    action: FilterValue = None,
    outcome: FilterValue = None,
) -> AuditEventPage:
    action = _validate_filter(action, "action")
    outcome = _validate_filter(outcome, "outcome")

    statement = select(AuditEvent)
    if action is not None:
        statement = statement.where(AuditEvent.action == action)
    if outcome is not None:
        statement = statement.where(AuditEvent.outcome == outcome)

    count = session.exec(
        select(func.count()).select_from(statement.subquery())
    ).one()
    events = session.exec(
        statement.order_by(AuditEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AuditEventPage(
        data=[_public_event(event) for event in events],
        count=count,
        page=page,
        page_size=page_size,
    )
