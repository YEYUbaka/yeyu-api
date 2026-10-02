from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import initial_data
from app.catalog_seed import PUBLIC_CATALOG_SEEDS, seed_public_catalog
from app.models import ApiDefinition


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _definitions(session: Session) -> list[ApiDefinition]:
    return list(
        session.exec(select(ApiDefinition).order_by(ApiDefinition.slug)).all()
    )


def test_public_catalog_seed_creates_time_and_uuid_with_adapter_contract(
    session: Session,
) -> None:
    seed_public_catalog(session)

    definitions = _definitions(session)
    assert [definition.slug for definition in definitions] == ["time", "uuid"]

    for definition in definitions:
        assert definition.method == "GET"
        assert definition.auth_type == "api_key"
        assert definition.adapter_name == "builtin-tools"
        assert definition.visibility == "public"
        assert definition.status in {"healthy", "published"}
        assert definition.is_free is True
        assert definition.path == f"/v1/tools/{definition.slug}"
        assert definition.source_label == "Yeyu API"
        assert definition.cache_rules["cacheable"] is False
        assert definition.cache_rules["stale_if_error"] is False
        assert "INVALID_PARAMETERS" in {
            error["code"] for error in definition.error_codes
        }

        examples = json.dumps(definition.examples, ensure_ascii=False)
        assert "<YOUR_API_KEY>" in examples
        assert "sk-" not in examples

    time_definition = definitions[0]
    timezone_parameter = time_definition.parameters[0]
    assert timezone_parameter["name"] == "timezone"
    assert timezone_parameter["in"] == "query"
    assert timezone_parameter["required"] is False
    assert timezone_parameter["schema"]["default"] == "UTC"
    assert set(time_definition.response_schema["properties"]) == {
        "utc",
        "unix_timestamp",
        "timezone",
        "local",
    }

    uuid_definition = definitions[1]
    assert uuid_definition.parameters == []
    assert uuid_definition.response_schema["properties"]["version"]["const"] == 4
    assert set(uuid_definition.response_schema["required"]) == {"uuid", "version"}


def test_public_catalog_seed_is_idempotent_and_preserves_admin_edits(
    session: Session,
) -> None:
    seed_public_catalog(session)

    time_definition = session.exec(
        select(ApiDefinition).where(ApiDefinition.slug == "time")
    ).one()
    time_definition.summary = "管理员维护的时间工具说明"
    time_definition.status = "healthy"
    time_definition.examples = [
        {"language": "text", "request": "管理员示例 <YOUR_API_KEY>"}
    ]
    time_definition.cache_rules = {
        "cacheable": True,
        "ttl_seconds": 7,
        "stale_if_error": True,
    }
    time_definition.updated_at = datetime(2026, 10, 1, 12, 34, 56)
    session.add(time_definition)
    session.commit()
    session.expire_all()

    before = session.exec(
        select(ApiDefinition).where(ApiDefinition.slug == "time")
    ).one()
    before_id = before.id
    before_updated_at = before.updated_at

    seed_public_catalog(session)
    session.expire_all()

    definitions = _definitions(session)
    assert len(definitions) == 2
    after = session.exec(
        select(ApiDefinition).where(ApiDefinition.slug == "time")
    ).one()
    assert after.id == before_id
    assert after.updated_at == before_updated_at
    assert after.summary == "管理员维护的时间工具说明"
    assert after.status == "healthy"
    assert after.examples == [
        {"language": "text", "request": "管理员示例 <YOUR_API_KEY>"}
    ]
    assert after.cache_rules == {
        "cacheable": True,
        "ttl_seconds": 7,
        "stale_if_error": True,
    }


def test_public_catalog_seeds_are_deeply_immutable() -> None:
    assert isinstance(PUBLIC_CATALOG_SEEDS, tuple)

    with pytest.raises(TypeError):
        PUBLIC_CATALOG_SEEDS[0] = PUBLIC_CATALOG_SEEDS[1]  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        PUBLIC_CATALOG_SEEDS[0].slug = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        PUBLIC_CATALOG_SEEDS[0].parameters[0]["required"] = True  # type: ignore[index]


def test_init_seeds_catalog_after_existing_init_db(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[str, object]] = []

    class SessionStub:
        def __enter__(self) -> SessionStub:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    session = SessionStub()
    monkeypatch.setattr(initial_data, "Session", lambda _engine: session)
    monkeypatch.setattr(
        initial_data,
        "init_db",
        lambda passed_session: events.append(("init_db", passed_session)),
    )
    monkeypatch.setattr(
        initial_data,
        "seed_public_catalog",
        lambda passed_session: events.append(("seed", passed_session)),
    )

    initial_data.init()

    assert events == [("init_db", session), ("seed", session)]
