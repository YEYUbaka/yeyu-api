from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.readiness import CHECK_FAILED, CHECK_NAMES, CHECK_OK, check_readiness

router = APIRouter(tags=["health"])


def _fixed_checks(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return dict.fromkeys(CHECK_NAMES, CHECK_FAILED)
    return {
        name: CHECK_OK if value.get(name) == CHECK_OK else CHECK_FAILED
        for name in CHECK_NAMES
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
def ready() -> dict[str, object] | JSONResponse:
    try:
        checks = _fixed_checks(check_readiness())
    except Exception:
        checks = dict.fromkeys(CHECK_NAMES, CHECK_FAILED)

    if all(status == CHECK_OK for status in checks.values()):
        return {"status": "ready", "checks": checks}
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "checks": checks},
    )
