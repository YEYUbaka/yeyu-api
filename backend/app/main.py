from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.deps import ApiError, close_api_runner, close_redis_store
from app.api.main import api_router
from app.api.routes import health
from app.core.config import settings
from app.middleware.request_logging import RequestLoggingMiddleware

FRONTEND_DIR = Path(__file__).parent / "frontend"


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        close_api_runner()
        close_redis_store()


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or exc.request_id
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


def _is_public_tool_path(request: Request) -> bool:
    prefix = f"{settings.API_V1_STR}/tools"
    path = request.url.path
    return path == prefix or path.startswith(f"{prefix}/")


def _public_request_error(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or "request-unidentified"
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    if not _is_public_tool_path(request):
        return await http_exception_handler(request, exc)
    if exc.status_code == 404:
        code, message = "API_NOT_FOUND", "API is not available"
    elif exc.status_code == 405:
        code, message = "METHOD_NOT_ALLOWED", "Method is not allowed"
    else:
        code, message = "REQUEST_REJECTED", "Request is not accepted"
    return _public_request_error(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    if not _is_public_tool_path(request):
        return await request_validation_exception_handler(request, exc)
    del exc
    return _public_request_error(
        request,
        status_code=422,
        code="INVALID_REQUEST",
        message="Request is invalid",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health.router)
app.include_router(api_router, prefix=settings.API_V1_STR)
if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=FRONTEND_DIR)
