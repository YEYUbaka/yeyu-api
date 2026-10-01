from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import (
    ApiError,
    ApiErrorRoute,
    ApiKeyPrincipalDep,
    CurrentUser,
    SessionDep,
)
from app.models import User
from app.schemas.api_keys import (
    ApiKeyCreate,
    ApiKeysPublic,
    CreatedApiKeyResponse,
)
from app.services.api_keys import (
    AccountSuspendedError,
    AccountUnverifiedError,
    ApiKeyAlreadyRevoked,
    ApiKeyNotFound,
    ApiKeyOwnershipError,
    ApiKeyService,
)

router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"],
    route_class=ApiErrorRoute,
)


def _ensure_user_can_manage_keys(current_user: User) -> None:
    if not current_user.is_active:
        raise ApiError(403, "ACCOUNT_SUSPENDED", "Account is suspended")
    if not current_user.email_verified:
        raise ApiError(403, "ACCOUNT_UNVERIFIED", "Account email is not verified")


def _raise_lifecycle_error(exc: Exception) -> None:
    if isinstance(exc, AccountUnverifiedError):
        raise ApiError(403, "ACCOUNT_UNVERIFIED", "Account email is not verified")
    if isinstance(exc, AccountSuspendedError):
        raise ApiError(403, "ACCOUNT_SUSPENDED", "Account is suspended")
    if isinstance(exc, ApiKeyNotFound):
        raise HTTPException(status_code=404, detail="API key not found") from exc
    if isinstance(exc, ApiKeyOwnershipError):
        raise HTTPException(status_code=403, detail="API key is not owned by user") from exc
    if isinstance(exc, ApiKeyAlreadyRevoked):
        raise ApiError(409, "API_KEY_REVOKED", "API key is revoked")
    raise exc


@router.post("", response_model=CreatedApiKeyResponse, status_code=201)
def create_api_key(
    payload: ApiKeyCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> CreatedApiKeyResponse:
    _ensure_user_can_manage_keys(current_user)
    try:
        created = ApiKeyService(session).create(current_user.id, payload.label)
    except Exception as exc:
        _raise_lifecycle_error(exc)
    return CreatedApiKeyResponse(data=created)


@router.get("", response_model=ApiKeysPublic)
def list_api_keys(
    session: SessionDep,
    current_user: CurrentUser,
) -> ApiKeysPublic:
    records = ApiKeyService(session).list(current_user.id)
    return ApiKeysPublic(data=records, count=len(records))


@router.get("/public-auth-check", include_in_schema=True)
def public_auth_check(principal: ApiKeyPrincipalDep) -> dict[str, object]:
    """Small protected boundary used by clients and contract tests.

    Task 5 owns actual tool execution; this route only proves independent key
    authentication and does not execute an adapter.
    """
    return {"data": {"key_id": principal.key_id, "prefix": principal.prefix}}


@router.post("/{key_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    try:
        ApiKeyService(session).revoke(key_id, current_user.id)
    except Exception as exc:
        _raise_lifecycle_error(exc)


@router.post("/{key_id}/rotate", response_model=CreatedApiKeyResponse, status_code=201)
def rotate_api_key(
    key_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> CreatedApiKeyResponse:
    try:
        created = ApiKeyService(session).rotate(key_id, current_user.id)
    except Exception as exc:
        _raise_lifecycle_error(exc)
    return CreatedApiKeyResponse(data=created)
