from collections.abc import Generator
from functools import lru_cache
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.api_key import APIKeyHeader
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User
from app.schemas.api_keys import ApiErrorResponse, ApiKeyPrincipal
from app.services.api_keys import ApiKeyService
from app.services.execution.runner import ApiRunner
from app.services.redis import RedisStore

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str | None, Depends(reusable_oauth2)]

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_client_ip(request: Request) -> IPv4Address | IPv6Address:
    """Return the direct peer address without trusting forwarding headers."""

    client = request.client
    if client is None or not client.host:
        raise ApiError(400, "CLIENT_IP_UNAVAILABLE", "Client IP is unavailable")
    try:
        return ip_address(client.host)
    except ValueError as exc:
        raise ApiError(400, "CLIENT_IP_UNAVAILABLE", "Client IP is invalid") from exc


ClientIpDep = Annotated[
    IPv4Address | IPv6Address, Depends(get_client_ip)
]


@lru_cache(maxsize=1)
def get_redis_store() -> RedisStore:
    """Return the process-local Redis primitive used by quota boundaries."""

    return RedisStore()


@lru_cache(maxsize=1)
def get_api_runner() -> ApiRunner:
    """Return one bounded executor per application process."""

    return ApiRunner()


def close_api_runner() -> None:
    if get_api_runner.cache_info().currsize == 0:
        return
    runner = get_api_runner()
    try:
        runner.close()
    finally:
        get_api_runner.cache_clear()


def close_redis_store() -> None:
    if get_redis_store.cache_info().currsize == 0:
        return
    store = get_redis_store()
    try:
        close = getattr(store.client, "close", None)
        if callable(close):
            close()
    finally:
        get_redis_store.cache_clear()


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.request_id = str(uuid4())
        super().__init__(message)

    def response_body(self) -> dict[str, object]:
        return ApiErrorResponse(
            error={
                "code": self.code,
                "message": self.message,
                "request_id": self.request_id,
            }
        ).model_dump(mode="json")


def get_current_user(request: Request, session: SessionDep, token: TokenDep) -> User:
    raw_token = token or request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    try:
        payload = jwt.decode(
            raw_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        ) from None
    if not token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    try:
        user_id = UUID(token_data.sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        ) from None
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_api_key_principal(
    request: Request,
    session: SessionDep,
    raw_key: Annotated[str | None, Security(api_key_header)],
) -> ApiKeyPrincipal:
    """Authenticate only the X-API-Key header, never the management cookie."""
    del request
    if not raw_key:
        raise ApiError(401, "API_KEY_REQUIRED", "API key is required")
    if len(raw_key.encode("utf-8")) > 256:
        raise ApiError(401, "API_KEY_INVALID", "API key is invalid")
    principal = ApiKeyService(session).authenticate(raw_key)
    if principal is None:
        raise ApiError(401, "API_KEY_INVALID", "API key is invalid")
    if principal.revoked_at is not None:
        raise ApiError(401, "API_KEY_REVOKED", "API key is revoked")
    if not principal.email_verified:
        raise ApiError(403, "ACCOUNT_UNVERIFIED", "Account email is not verified")
    if not principal.is_active:
        raise ApiError(403, "ACCOUNT_SUSPENDED", "Account is suspended")
    return principal


ApiKeyPrincipalDep = Annotated[
    ApiKeyPrincipal, Depends(get_api_key_principal)
]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
