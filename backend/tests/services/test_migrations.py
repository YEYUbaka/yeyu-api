from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint

from app.models import ApiDefinition, AuditEvent, UsageDaily

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = (
    PROJECT_ROOT
    / "backend"
    / "app"
    / "alembic"
    / "versions"
    / "20261003_add_usage_cache_tables.py"
)
AUDIT_MIGRATION_PATH = (
    PROJECT_ROOT
    / "backend"
    / "app"
    / "alembic"
    / "versions"
    / "20261004_add_audit_events.py"
)
CATALOG_BOUNDARY_MIGRATION_PATH = (
    PROJECT_ROOT
    / "backend"
    / "app"
    / "alembic"
    / "versions"
    / "20261005_harden_catalog_boundaries.py"
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


def _load_migration(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load migration: {path.name}")
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


def test_audit_event_model_and_migration_are_durable_and_indexed() -> None:
    source = AUDIT_MIGRATION_PATH.read_text(encoding="utf-8")
    table = AuditEvent.__table__

    assert table.c.details.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.actor_id.nullable is True
    assert next(iter(table.c.actor_id.foreign_keys)).ondelete == "SET NULL"
    assert {
        index.name
        for index in table.indexes
    } >= {
        "ix_audit_event_request_id",
        "ix_audit_event_action",
        "ix_audit_event_object_type",
        "ix_audit_event_outcome",
        "ix_audit_event_created_at",
    }
    assert 'down_revision = "20261003_add_usage_cache_tables"' in source
    assert "details" in source and "nullable=False" in source
    assert 'ondelete="SET NULL"' in source


def test_audit_event_downgrade_fails_closed_offline_and_when_populated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration(AUDIT_MIGRATION_PATH, "audit_event_migration")
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: True)

    with pytest.raises(RuntimeError, match="offline"):
        migration.downgrade()

    class Result:
        def scalar_one(self) -> int:
            return 1

    class Connection:
        def execute(self, _statement: object) -> Result:
            return Result()

    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.op, "get_bind", lambda: Connection())

    with pytest.raises(RuntimeError, match="contains data"):
        migration._refuse_if_populated()


def test_catalog_boundary_migration_matches_model_constraints() -> None:
    migration = _load_migration(
        CATALOG_BOUNDARY_MIGRATION_PATH,
        "catalog_boundary_migration",
    )
    recorded: dict[str, str] = {}

    def record_check(name: str, _table: str, condition: str) -> None:
        recorded[name] = condition

    original_create_check = migration.op.create_check_constraint
    migration.op.create_check_constraint = record_check
    try:
        migration.upgrade()
    finally:
        migration.op.create_check_constraint = original_create_check

    model_constraints = {
        constraint.name: " ".join(str(constraint.sqltext).split())
        for constraint in ApiDefinition.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    expected_names = {
        "ck_api_definition_status_allowed",
        "ck_api_definition_adapter_name_allowlist",
        "ck_api_definition_provider_ref_allowlist",
        "ck_api_definition_path_internal",
    }

    assert expected_names <= set(recorded)
    for name in expected_names:
        assert " ".join(recorded[name].split()) == model_constraints[name]
