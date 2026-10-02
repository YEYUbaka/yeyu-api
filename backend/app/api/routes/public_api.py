from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Path, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.api.deps import (
    ApiKeyPrincipalDep,
    ClientIpDep,
    SessionDep,
    get_api_runner,
    get_redis_store,
)
from app.core.config import settings
from app.models import ApiDefinition
from app.schemas.api_keys import ApiErrorResponse
from app.schemas.policy import PolicyDecision
from app.services.execution.models import (
    MAX_PARAMETER_BYTES,
    ApiResponse,
    ExecutionContext,
)
from app.services.execution.registry import BUILTIN_SLUGS
from app.services.execution.runner import ApiRunner
from app.services.policy import PolicyDenied, PolicyService
from app.services.quota import QuotaDatabaseUnavailable
from app.services.redis import RedisStore, RedisUnavailable

router = APIRouter(prefix="/tools", tags=["public-api"])

SlugPath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]

PUBLIC_STATUSES = ("healthy", "published")
TOOL_ADAPTER_NAME = "builtin-tools"
TOOL_TIMEOUT_MS = 5_000
RATE_LIMIT_CODES = frozenset(
    {"MINUTE_LIMIT", "IP_MINUTE_LIMIT", "DAILY_QUOTA_EXCEEDED", "CONCURRENCY_LIMIT"}
)
INTERNAL_ADMISSION_CODES = frozenset(
    {
        "ADMISSION_REQUIRED",
        "INVALID_ADMISSION",
        "ADMISSION_REUSED",
        "ADMISSION_EXPIRED",
        "ADMISSION_CONTEXT_MISMATCH",
    }
)
POLICY_MESSAGES = {
    "MINUTE_LIMIT": "Minute rate limit exceeded",
    "IP_MINUTE_LIMIT": "IP rate limit exceeded",
    "DAILY_QUOTA_EXCEEDED": "Daily quota exceeded",
    "CONCURRENCY_LIMIT": "Concurrency limit exceeded",
    "IP_NOT_ALLOWED": "Client IP is not allowed",
    "POLICY_DISABLED": "API policy is disabled",
    "ACCOUNT_UNVERIFIED": "Account email is not verified",
    "ACCOUNT_SUSPENDED": "Account is suspended",
}


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    headers = {"X-Request-ID": request_id}
    if retry_after_seconds is not None and retry_after_seconds > 0:
        headers["Retry-After"] = str(retry_after_seconds)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
        headers=headers,
    )


def _public_tool_definition(session: Session, slug: str) -> ApiDefinition | None:
    if slug not in BUILTIN_SLUGS:
        return None
    definition = session.exec(
        select(ApiDefinition).where(
            ApiDefinition.slug == slug,
            ApiDefinition.visibility == "public",
            ApiDefinition.status.in_(PUBLIC_STATUSES),
        )
    ).first()
    if definition is None:
        return None

    expected_paths = {
        f"/v1/tools/{slug}",
        f"{settings.API_V1_STR}/tools/{slug}",
    }
    if (
        definition.method.upper() != "GET"
        or definition.auth_type != "api_key"
        or definition.adapter_name != TOOL_ADAPTER_NAME
        or definition.path not in expected_paths
    ):
        return None
    return definition


def _collect_query_params(
    request: Request,
    request_id: str,
) -> dict[str, str] | JSONResponse:
    raw_query = request.scope.get("query_string", b"")
    if not isinstance(raw_query, bytes) or len(raw_query) > MAX_PARAMETER_BYTES:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="RESOURCE_LIMIT",
            message="Query parameters are too large",
            request_id=request_id,
        )

    params: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        if key in params:
            return _error_response(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="INVALID_PARAMETERS",
                message="Duplicate query parameters are not accepted",
                request_id=request_id,
            )
        params[key] = value
    return params


def _policy_response(decision: PolicyDecision, request_id: str) -> JSONResponse:
    code = decision.code or "POLICY_DENIED"
    if code in INTERNAL_ADMISSION_CODES:
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="QUOTA_UNAVAILABLE",
            message="Quota service is temporarily unavailable",
            request_id=request_id,
            retry_after_seconds=decision.retry_after_seconds,
        )
    response_status = (
        status.HTTP_429_TOO_MANY_REQUESTS
        if code in RATE_LIMIT_CODES
        else status.HTTP_403_FORBIDDEN
    )
    return _error_response(
        status_code=response_status,
        code=code,
        message=POLICY_MESSAGES.get(code, "API policy denied this request"),
        request_id=request_id,
        retry_after_seconds=decision.retry_after_seconds,
    )


def _execution_status(response: ApiResponse) -> int:
    if response.success:
        return status.HTTP_200_OK
    code = (response.error or {}).get("code")
    if code in {"INVALID_PARAMETERS", "RESOURCE_LIMIT"}:
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    if code == "UPSTREAM_TIMEOUT":
        return status.HTTP_504_GATEWAY_TIMEOUT
    if code == "UPSTREAM_ERROR":
        return status.HTTP_502_BAD_GATEWAY
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _execution_response(response: ApiResponse) -> JSONResponse:
    request_id = str(response.meta.get("request_id", uuid4()))
    return JSONResponse(
        status_code=_execution_status(response),
        content=response.model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )


@router.get(
    "/{slug}",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "API key required"},
        403: {"model": ApiErrorResponse, "description": "API policy denied"},
        404: {"model": ApiErrorResponse, "description": "API not found"},
        422: {"model": ApiErrorResponse, "description": "Invalid parameters"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        502: {"model": ApiErrorResponse, "description": "Upstream execution failed"},
        503: {"model": ApiErrorResponse, "description": "Quota unavailable"},
        504: {"model": ApiErrorResponse, "description": "Execution timed out"},
    },
)
def execute_tool(
    slug: SlugPath,
    request: Request,
    session: SessionDep,
    principal: ApiKeyPrincipalDep,
    client_ip: ClientIpDep,
    redis: Annotated[RedisStore, Depends(get_redis_store)],
    runner: Annotated[ApiRunner, Depends(get_api_runner)],
) -> JSONResponse:
    request_id = str(uuid4())
    params_or_response = _collect_query_params(request, request_id)
    if isinstance(params_or_response, JSONResponse):
        return params_or_response
    params = params_or_response

    try:
        definition = _public_tool_definition(session, slug)
    except SQLAlchemyError:
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="API_UNAVAILABLE",
            message="API catalog is temporarily unavailable",
            request_id=request_id,
        )
    if definition is None:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="API_NOT_FOUND",
            message="API is not available",
            request_id=request_id,
        )

    now = datetime.now(UTC)
    policy = PolicyService(session, redis=redis)
    try:
        decision = policy.evaluate(principal, definition, client_ip, now)
    except (RedisUnavailable, QuotaDatabaseUnavailable, SQLAlchemyError):
        return _quota_unavailable(request_id)
    if not decision.allowed:
        return _policy_response(decision, request_id)

    try:
        with policy.acquire(
            principal,
            definition,
            client_ip,
            now,
            decision=decision,
        ):
            context = ExecutionContext(
                request_id=request_id,
                api_slug=slug,
                api_key_id=principal.api_key_id,
                user_id=principal.user_id,
                client_ip=client_ip,
                timeout_ms=TOOL_TIMEOUT_MS,
                now=now,
            )
            response = runner.run(slug, context, params)
    except PolicyDenied as exc:
        return _policy_response(exc.decision, request_id)
    except (RedisUnavailable, QuotaDatabaseUnavailable, SQLAlchemyError):
        return _quota_unavailable(request_id)

    return _execution_response(response)


def _quota_unavailable(request_id: str) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="QUOTA_UNAVAILABLE",
        message="Quota service is temporarily unavailable",
        request_id=request_id,
    )


__all__ = ["router"]
