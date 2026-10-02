from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_superuser
from app.api.routes.health import _fixed_checks
from app.core.readiness import CHECK_NAMES, CHECK_OK, check_readiness
from app.schemas.admin import AdminHealthView, HealthChecks

router = APIRouter(
    prefix="/admin/health",
    tags=["admin-health"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("", response_model=AdminHealthView)
def read_admin_health() -> AdminHealthView:
    try:
        checks = _fixed_checks(check_readiness())
    except Exception:
        checks = dict.fromkeys(CHECK_NAMES, "failed")

    status = "ready" if all(value == CHECK_OK for value in checks.values()) else "not_ready"
    return AdminHealthView(status=status, checks=HealthChecks(**checks))
