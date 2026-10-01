from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint

from app.models import UsageDaily

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = (
    PROJECT_ROOT
    / "backend"
    / "app"
    / "alembic"
    / "versions"
    / "20261003_add_usage_cache_tables.py"
)


def _migration_module():
    spec = importlib.util.spec_from_file_location(
        "usage_cache_migration",
        MIGRATION_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("could not load usage/cache migration")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_usage_daily_model_has_non_negative_checks() -> None:
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in UsageDaily.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {
        "ck_usage_daily_request_count_nonnegative": "request_count >= 0",
        "ck_usage_daily_weighted_units_nonnegative": "weighted_units >= 0",
    }


def test_usage_cache_migration_declares_matching_checks() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "ck_usage_daily_request_count_nonnegative" in source
    assert "ck_usage_daily_weighted_units_nonnegative" in source


def test_usage_cache_downgrade_fails_closed_in_offline_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _migration_module()
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: True)

    with pytest.raises(RuntimeError, match="offline"):
        migration.downgrade()


def test_usage_cache_online_guard_allows_empty_and_rejects_populated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _migration_module()

    class Result:
        def __init__(self, count: int) -> None:
            self.count = count

        def scalar_one(self) -> int:
            return self.count

    class Connection:
        count = 0

        def execute(self, _statement: object) -> Result:
            return Result(self.count)

    connection = Connection()
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    migration._refuse_if_populated("usage_daily")
    connection.count = 1
    with pytest.raises(RuntimeError, match="contains data"):
        migration._refuse_if_populated("usage_daily")
