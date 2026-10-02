from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.api.deps import get_redis_store
from app.core.db import engine

CHECK_NAMES = ("database", "redis", "migrations")
CHECK_OK = "ok"
CHECK_FAILED = "failed"

_ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"


def check_database() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


def check_redis() -> bool:
    try:
        return bool(get_redis_store().ping())
    except Exception:
        return False


def _script_directory() -> ScriptDirectory:
    config = Config()
    config.set_main_option("script_location", str(_ALEMBIC_DIR))
    return ScriptDirectory.from_config(config)


def check_migrations() -> bool:
    try:
        script = _script_directory()
        expected_heads = set(script.get_heads())
        if not expected_heads:
            return False

        with engine.connect() as connection:
            current_heads = set(
                MigrationContext.configure(connection).get_current_heads()
            )
        return current_heads == expected_heads
    except Exception:
        return False


def _status(check: Callable[[], bool]) -> str:
    try:
        return CHECK_OK if check() else CHECK_FAILED
    except Exception:
        return CHECK_FAILED


def check_readiness() -> dict[str, str]:
    checks: Mapping[str, Callable[[], bool]] = {
        "database": check_database,
        "redis": check_redis,
        "migrations": check_migrations,
    }
    return {name: _status(checks[name]) for name in CHECK_NAMES}
