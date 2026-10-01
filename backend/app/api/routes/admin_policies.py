from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.deps import SessionDep, get_current_active_superuser
from app.schemas.policy import PolicyUpdate, PolicyView
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
) -> PolicyView:
    try:
        return PolicyService(session).upsert(api_slug, payload)
    except PolicyApiNotFound as exc:
        raise HTTPException(status_code=404, detail="API policy target not found") from exc
