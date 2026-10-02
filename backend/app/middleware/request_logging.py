from __future__ import annotations

import json
import logging
import re
from time import monotonic
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("yeyu.request")
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _safe_value(value: object) -> str | None:
    if not isinstance(value, str) or _SAFE_VALUE.fullmatch(value) is None:
        return None
    return value


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit bounded request facts without reading request bodies or credentials."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        started = monotonic()
        response: Response | None = None
        outcome = "response"
        try:
            response = await call_next(request)
        except Exception:
            outcome = "exception"
            raise
        finally:
            latency_ms = round((monotonic() - started) * 1000, 2)
            status_code = response.status_code if response is not None else 500
            header_request_id = (
                response.headers.get("X-Request-ID") if response is not None else None
            )
            request_id = _safe_value(header_request_id) or _safe_value(
                getattr(request.state, "request_id", None)
            ) or request_id
            route = request.scope.get("route")
            route_template = getattr(route, "path", None)
            slug = getattr(request.state, "api_slug", None)
            safe_slug = slug if isinstance(slug, str) and _SAFE_SLUG.fullmatch(slug) else None
            error_category = _safe_value(
                getattr(request.state, "error_category", None)
            )
            event = {
                "request_id": request_id,
                "method": request.method,
                "route": route_template if isinstance(route_template, str) else None,
                "api_slug": safe_slug,
                "status": status_code,
                "latency_ms": latency_ms,
                "cache_hit": bool(getattr(request.state, "cache_hit", False)),
                "stale": bool(getattr(request.state, "stale", False)),
                "error_category": error_category,
                "outcome": outcome,
            }
            logger.info("request %s", json.dumps(event, sort_keys=True))

        assert response is not None
        response.headers.setdefault("X-Request-ID", request_id)
        return response
