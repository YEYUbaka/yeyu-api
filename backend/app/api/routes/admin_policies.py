from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.schemas.policy import PolicyUpdate, PolicyView
from app.services.audit import AuditService
from app.services.policy import PolicyApiNotFound, PolicyService

router = APIRouter(
    prefix="/admin/policies",
    tags=["admin-policies"],
    dependencies=[Depends(get_current_active_superuser)],
)

ApiSlugPath = Annotated[str, Path(min_length=1, max_length=100)]


@router.get("/{api_slug}", response_model=PolicyView)
def get_policy(api_slug: ApiSlugPath, session: SessionDep) -> PolicyView:
    try:
        return PolicyService(session).get(api_slug)
    except PolicyApiNotFound as exc:
        raise HTTPException(status_code=404, detail="API policy target not found") from exc


@router.put("/{api_slug}", response_model=PolicyView)
def update_policy(
    api_slug: ApiSlugPath,
    payload: PolicyUpdate,
    session: SessionDep,
    request: Request,
    current_user: CurrentUser,
) -> PolicyView:
    try:
        view = PolicyService(session).upsert(api_slug, payload, commit=False)
        AuditService(session).record(
            actor_id=current_user.id,
            action="policy.update",
            object_type="api_policy",
            object_id=api_slug,
            outcome="success",
            metadata={"changed_fields": sorted(payload.model_dump(exclude_unset=True))},
            request_id=getattr(request.state, "request_id", None),
        )
        session.commit()
        return view
    except PolicyApiNotFound as exc:
        raise HTTPException(status_code=404, detail="API policy target not found") from exc
    except (SQLAlchemyError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="Policy operation temporarily unavailable"
        ) from exc
