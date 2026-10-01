from __future__ import annotations

import os
import secrets
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


@pytest.fixture()
def key_session() -> Iterator[Session]:
    from app import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _task4_types() -> tuple[object | None, object | None, object | None]:
    try:
        from app.models import ApiKey, User
        from app.services.api_keys import ApiKeyService
    except (ImportError, AttributeError):
        return None, None, None
    return ApiKey, User, ApiKeyService


def _require_task4_types() -> tuple[type, type, type]:
    api_key, user, service = _task4_types()
    assert api_key is not None, "Task 4 ApiKey model is not implemented"
    assert user is not None, "Task 4 User model integration is not implemented"
    assert service is not None, "Task 4 ApiKeyService is not implemented"
    return api_key, user, service  # type: ignore[return-value]


def _verified_user(user_type: type) -> object:
    return user_type(
        email=f"{secrets.token_hex(12)}@example.com",
        hashed_password=secrets.token_urlsafe(24),
        email_verified=True,
        is_active=True,
    )


def _settings_values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "FASTAPI_ENV": "production",
        "SECRET_KEY": "settings-test-secret",
        "API_KEY_PEPPER": "settings-test-api-key-pepper",
        "PROJECT_NAME": "Yeyu API Settings Test",
        "DATABASE_URL": "postgresql://postgres:db-password@example.com:5432/app",
        "FIRST_SUPERUSER": "admin@example.com",
        "FIRST_SUPERUSER_PASSWORD": "settings-test-password",
    }
    values.update(overrides)
    return values


def test_non_development_requires_an_independent_api_key_pepper() -> None:
    from app.core.config import Settings

    with pytest.raises(ValidationError, match="API_KEY_PEPPER"):
        Settings(**_settings_values(API_KEY_PEPPER=None))


def test_production_rejects_reusing_secret_key_as_api_key_pepper() -> None:
    from app.core.config import Settings

    with pytest.raises(ValidationError, match="independent"):
        Settings(**_settings_values(API_KEY_PEPPER="settings-test-secret"))


@pytest.mark.parametrize(
    ("previous_pepper", "previous_version", "current_version"),
    (
        ("old-pepper", None, 2),
        (None, 1, 2),
        ("old-pepper", 0, 2),
        ("old-pepper", 2, 2),
        (None, None, 0),
    ),
)
def test_pepper_versions_must_be_valid_pairs(
    previous_pepper: str | None,
    previous_version: int | None,
    current_version: int,
) -> None:
    from app.core.config import Settings

    with pytest.raises(ValidationError, match="(?i)pepper|version"):
        Settings(
            **_settings_values(
                API_KEY_PEPPER_VERSION=current_version,
                API_KEY_PREVIOUS_PEPPER=previous_pepper,
                API_KEY_PREVIOUS_PEPPER_VERSION=previous_version,
            )
        )


def test_valid_current_and_previous_pepper_configuration_is_accepted() -> None:
    from app.core.config import Settings

    configured = Settings(
        **_settings_values(
            API_KEY_PEPPER_VERSION=2,
            API_KEY_PREVIOUS_PEPPER="old-pepper",
            API_KEY_PREVIOUS_PEPPER_VERSION=1,
        )
    )

    assert configured.API_KEY_PEPPER_VERSION == 2
    assert configured.API_KEY_PREVIOUS_PEPPER_VERSION == 1


def test_hash_helper_does_not_fallback_to_secret_key_outside_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import security
    from app.core.config import settings

    monkeypatch.setattr(settings, "FASTAPI_ENV", "production")
    monkeypatch.setattr(settings, "API_KEY_PEPPER", None)

    with pytest.raises(ValueError, match="API_KEY_PEPPER"):
        security.hash_api_key("raw-key", version=settings.API_KEY_PEPPER_VERSION)


def test_offline_downgrade_emits_database_side_data_loss_guards() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment.update(
        {
            "FASTAPI_ENV": "development",
            "SECRET_KEY": "offline-migration-test-secret",
            "API_KEY_PEPPER": "offline-migration-test-pepper",
            "PROJECT_NAME": "Yeyu API Migration Test",
            "DATABASE_URL": "postgresql://postgres:db-password@example.com:5432/app",
            "FIRST_SUPERUSER": "admin@example.com",
            "FIRST_SUPERUSER_PASSWORD": "offline-migration-test-password",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "downgrade",
            "20261002_add_key_policy_tables:20261001_add_catalog_tables",
            "--sql",
        ],
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    sql = completed.stdout
    assert "DO $$" in sql
    policy_guard = sql.index("IF EXISTS (SELECT 1 FROM api_policy")
    key_guard = sql.index("IF EXISTS (SELECT 1 FROM api_key")
    assert policy_guard < sql.index("DROP TABLE api_policy")
    assert key_guard < sql.index("DROP TABLE api_key")


def test_create_persists_only_public_prefix_and_hmac_digest(
    key_session: Session,
) -> None:
    api_key_type, user_type, service_type = _require_task4_types()
    user = _verified_user(user_type)
    key_session.add(user)
    key_session.commit()
    key_session.refresh(user)

    created = service_type(key_session).create(user.id, "local")
    row = key_session.exec(select(api_key_type)).one()

    assert isinstance(created.id, UUID)
    assert created.secret
    assert created.prefix == row.prefix
    assert row.key_hash != created.secret
    assert created.secret not in repr(row)
    assert not hasattr(row, "secret")
    assert row.hash_version >= 1
    assert len(created.secret.encode("utf-8")) >= 32


def test_authenticate_returns_principal_and_distinguishes_revocation(
    key_session: Session,
) -> None:
    api_key_type, user_type, service_type = _require_task4_types()
    user = _verified_user(user_type)
    key_session.add(user)
    key_session.commit()
    key_session.refresh(user)
    service = service_type(key_session)
    created = service.create(user.id, None)

    principal = service.authenticate(created.secret)
    assert principal is not None
    assert principal.key_id == created.id
    assert principal.user_id == user.id
    assert principal.prefix == created.prefix
    assert principal.revoked_at is None

    service.revoke(created.id, user.id)
    revoked = service.authenticate(created.secret)
    assert revoked is not None
    assert revoked.revoked_at is not None
    assert key_session.exec(select(api_key_type)).one().revoked_at is not None


def test_rotate_is_atomic_when_new_key_commit_fails(key_session: Session) -> None:
    _api_key_type, user_type, service_type = _require_task4_types()
    user = _verified_user(user_type)
    key_session.add(user)
    key_session.commit()
    key_session.refresh(user)
    service = service_type(key_session)
    old = service.create(user.id, "before-rotation")

    original_commit = key_session.commit

    def fail_commit() -> None:
        raise RuntimeError("simulated rotation commit failure")

    key_session.commit = fail_commit  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="simulated rotation commit failure"):
        service.rotate(old.id, user.id)
    key_session.commit = original_commit  # type: ignore[method-assign]

    key_session.rollback()
    surviving = service.authenticate(old.secret)
    assert surviving is not None
    assert surviving.revoked_at is None


def test_create_commit_failure_rolls_back_new_key(key_session: Session) -> None:
    _api_key_type, user_type, service_type = _require_task4_types()
    user = _verified_user(user_type)
    key_session.add(user)
    key_session.commit()
    key_session.refresh(user)
    service = service_type(key_session)

    original_commit = key_session.commit

    def fail_commit() -> None:
        raise RuntimeError("simulated create commit failure")

    key_session.commit = fail_commit  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="simulated create commit failure"):
        service.create(user.id, "failed-create")
    key_session.commit = original_commit  # type: ignore[method-assign]

    key_session.rollback()
    assert key_session.exec(select(_api_key_type)).all() == []


def test_create_and_rotate_do_not_require_post_commit_refresh(
    key_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _api_key_type, user_type, service_type = _require_task4_types()
    user = _verified_user(user_type)
    key_session.add(user)
    key_session.commit()
    key_session.refresh(user)
    service = service_type(key_session)
    original = service.create(user.id, "before-refresh-failure")

    def fail_refresh(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("refresh must not be required after commit")

    monkeypatch.setattr(key_session, "refresh", fail_refresh)

    created = service.create(user.id, "create-without-refresh")
    rotated = service.rotate(original.id, user.id)

    assert created.secret
    assert rotated.secret
    assert rotated.id != original.id
    assert service.authenticate(original.secret).revoked_at is not None


def test_versioned_hmac_does_not_use_plaintext_key_as_storage_value() -> None:
    try:
        from app.core import security
    except ImportError:
        pytest.fail("Task 4 API-key security helpers are not implemented")

    raw_key = secrets.token_urlsafe(32)
    digest = security.hash_api_key(raw_key, version=1)

    assert len(digest) == 64
    assert digest != raw_key
    assert security.verify_api_key_hash(raw_key, digest, version=1)
    assert not security.verify_api_key_hash(
        secrets.token_urlsafe(32), digest, version=1
    )


def test_authenticate_accepts_an_explicit_previous_pepper_version(
    key_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _api_key_type, user_type, service_type = _require_task4_types()
    from app.core.config import settings

    user = _verified_user(user_type)
    key_session.add(user)
    key_session.commit()
    key_session.refresh(user)

    old_pepper = "old-api-key-pepper-for-test"
    monkeypatch.setattr(settings, "API_KEY_PEPPER", old_pepper)
    monkeypatch.setattr(settings, "API_KEY_PEPPER_VERSION", 1)
    created = service_type(key_session).create(user.id, "version-1")

    monkeypatch.setattr(settings, "API_KEY_PEPPER", secrets.token_urlsafe(32))
    monkeypatch.setattr(settings, "API_KEY_PEPPER_VERSION", 2)
    monkeypatch.setattr(settings, "API_KEY_PREVIOUS_PEPPER", old_pepper)
    monkeypatch.setattr(settings, "API_KEY_PREVIOUS_PEPPER_VERSION", 1)

    principal = service_type(key_session).authenticate(created.secret)
    assert principal is not None
    assert principal.hash_version == 1


def test_policy_evaluation_rejects_unverified_or_revoked_principal(
    key_session: Session,
) -> None:
    try:
        from app.models import ApiDefinition
        from app.schemas.api_keys import ApiKeyPrincipal
        from app.schemas.policy import PolicyUpdate
        from app.services.policy import PolicyService
    except (ImportError, AttributeError):
        pytest.fail("Task 4 policy interfaces are not implemented")

    api = ApiDefinition(
        slug="uuid",
        name="UUID",
        summary="UUID",
        category="tools",
        method="GET",
        path="/v1/tools/uuid",
        adapter_name="builtin-tools",
    )
    key_session.add(api)
    key_session.commit()
    key_session.refresh(api)
    now = datetime.now(UTC)

    unverified = ApiKeyPrincipal(
        key_id=UUID(int=1),
        user_id=UUID(int=2),
        prefix="yeyu_test",
        hash_version=1,
        email_verified=False,
        is_active=True,
    )
    revoked = unverified.model_copy(update={"email_verified": True, "revoked_at": now})

    service = PolicyService(key_session)
    assert service.evaluate(unverified, api, "192.0.2.10", now).code == (
        "ACCOUNT_UNVERIFIED"
    )
    assert service.evaluate(revoked, api, "192.0.2.10", now).code == (
        "API_KEY_REVOKED"
    )

    policy_service = PolicyService(key_session)
    policy = policy_service.upsert(
        "uuid",
        PolicyUpdate(allowed_ips=["192.0.2.0/24"], minute_limit=5),
    )
    assert policy.minute_limit == 5
    allowed = unverified.model_copy(update={"email_verified": True})
    assert policy_service.evaluate(allowed, api, "192.0.2.10", now).allowed
    assert policy_service.evaluate(allowed, api, "198.51.100.10", now).code == (
        "IP_NOT_ALLOWED"
    )


def test_policy_evaluation_fails_closed_for_historical_invalid_allowlist(
    key_session: Session,
) -> None:
    from app.models import ApiDefinition, ApiPolicy
    from app.schemas.api_keys import ApiKeyPrincipal
    from app.services.policy import PolicyService

    api = ApiDefinition(
        slug="historical-invalid-policy",
        name="Historical invalid policy",
        summary="Historical invalid policy",
        category="tools",
        method="GET",
        path="/v1/tools/historical-invalid-policy",
        adapter_name="builtin-tools",
    )
    key_session.add(api)
    key_session.commit()
    key_session.refresh(api)
    key_session.add(ApiPolicy(api_definition_id=api.id, allowed_ips=["not-an-ip"]))
    key_session.commit()

    principal = ApiKeyPrincipal(
        key_id=UUID(int=3),
        user_id=UUID(int=4),
        prefix="yeyu_test",
        hash_version=1,
    )
    decision = PolicyService(key_session).evaluate(
        principal,
        api,
        "192.0.2.10",
        datetime.now(UTC),
    )

    assert decision.allowed is False
    assert decision.code == "IP_NOT_ALLOWED"
