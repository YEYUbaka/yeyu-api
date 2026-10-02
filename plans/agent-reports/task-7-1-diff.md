# Review package: 068092dbe64bed983f9c8614a389546159edc682..feb0136be09b0c3ddaed37af62b40b518f159c40

## Commits
feb0136 feat: seed public builtin catalog

## Files changed
 backend/app/catalog_seed.py                 | 296 ++++++++++++++++++++++++++++
 backend/app/initial_data.py                 |   2 +
 backend/tests/services/test_catalog_seed.py | 168 ++++++++++++++++
 3 files changed, 466 insertions(+)

## Diff
diff --git a/backend/app/catalog_seed.py b/backend/app/catalog_seed.py
new file mode 100644
index 0000000..6deef6b
--- /dev/null
+++ b/backend/app/catalog_seed.py
@@ -0,0 +1,296 @@
+from __future__ import annotations
+
+from collections.abc import Mapping
+from dataclasses import dataclass
+from types import MappingProxyType
+from typing import Any
+
+from sqlmodel import Session, select
+
+from app.models import ApiDefinition
+
+
+def _freeze(value: Any) -> Any:
+    if isinstance(value, dict):
+        return MappingProxyType(
+            {key: _freeze(nested) for key, nested in value.items()}
+        )
+    if isinstance(value, list):
+        return tuple(_freeze(nested) for nested in value)
+    return value
+
+
+def _thaw(value: Any) -> Any:
+    if isinstance(value, Mapping):
+        return {key: _thaw(nested) for key, nested in value.items()}
+    if isinstance(value, tuple):
+        return [_thaw(nested) for nested in value]
+    return value
+
+
+@dataclass(frozen=True, slots=True)
+class CatalogSeed:
+    slug: str
+    name: str
+    summary: str
+    category: str
+    method: str
+    path: str
+    auth_type: str
+    parameters: tuple[Mapping[str, Any], ...]
+    response_schema: Mapping[str, Any]
+    error_codes: tuple[Mapping[str, Any], ...]
+    examples: tuple[Mapping[str, Any], ...]
+    visibility: str
+    status: str
+    is_free: bool
+    source_label: str
+    adapter_name: str
+    provider_ref: str | None
+    cache_rules: Mapping[str, Any]
+
+    def model_kwargs(self) -> dict[str, Any]:
+        return {
+            "slug": self.slug,
+            "name": self.name,
+            "summary": self.summary,
+            "category": self.category,
+            "method": self.method,
+            "path": self.path,
+            "auth_type": self.auth_type,
+            "parameters": _thaw(self.parameters),
+            "response_schema": _thaw(self.response_schema),
+            "error_codes": _thaw(self.error_codes),
+            "examples": _thaw(self.examples),
+            "visibility": self.visibility,
+            "status": self.status,
+            "is_free": self.is_free,
+            "source_label": self.source_label,
+            "adapter_name": self.adapter_name,
+            "provider_ref": self.provider_ref,
+            "cache_rules": _thaw(self.cache_rules),
+        }
+
+
+_COMMON_ERROR_CODES = _freeze(
+    [
+        {
+            "status": 401,
+            "code": "API_KEY_REQUIRED",
+            "description": "请求必须提供 X-API-Key。",
+        },
+        {
+            "status": 401,
+            "code": "API_KEY_INVALID",
+            "description": "API Key 无效。",
+        },
+        {
+            "status": 401,
+            "code": "API_KEY_REVOKED",
+            "description": "API Key 已撤销。",
+        },
+        {
+            "status": 403,
+            "code": "ACCOUNT_UNVERIFIED",
+            "description": "API Key 所属账号尚未完成邮箱验证。",
+        },
+        {
+            "status": 403,
+            "code": "ACCOUNT_SUSPENDED",
+            "description": "API Key 所属账号已被停用。",
+        },
+        {
+            "status": 403,
+            "code": "IP_NOT_ALLOWED",
+            "description": "客户端 IP 不在允许范围内。",
+        },
+        {
+            "status": 403,
+            "code": "POLICY_DISABLED",
+            "description": "该 API 的调用策略已停用。",
+        },
+        {
+            "status": 422,
+            "code": "INVALID_PARAMETERS",
+            "description": "查询参数不符合接口约束。",
+        },
+        {
+            "status": 429,
+            "code": "MINUTE_LIMIT",
+            "description": "超过账号分钟调用限制。",
+        },
+        {
+            "status": 429,
+            "code": "IP_MINUTE_LIMIT",
+            "description": "超过客户端 IP 分钟调用限制。",
+        },
+        {
+            "status": 429,
+            "code": "DAILY_QUOTA_EXCEEDED",
+            "description": "超过每日调用额度。",
+        },
+        {
+            "status": 429,
+            "code": "CONCURRENCY_LIMIT",
+            "description": "超过并发调用限制。",
+        },
+        {
+            "status": 502,
+            "code": "UPSTREAM_ERROR",
+            "description": "执行适配器返回错误。",
+        },
+        {
+            "status": 503,
+            "code": "QUOTA_UNAVAILABLE",
+            "description": "配额服务暂时不可用。",
+        },
+        {
+            "status": 504,
+            "code": "UPSTREAM_TIMEOUT",
+            "description": "执行超过请求超时限制。",
+        },
+    ]
+)
+
+
+PUBLIC_CATALOG_SEEDS: tuple[CatalogSeed, ...] = (
+    CatalogSeed(
+        slug="time",
+        name="时间查询",
+        summary="按可选 IANA 时区返回当前 UTC、Unix 时间戳和本地时间。",
+        category="tools",
+        method="GET",
+        path="/v1/tools/time",
+        auth_type="api_key",
+        parameters=(
+            _freeze(
+                {
+                    "name": "timezone",
+                    "in": "query",
+                    "required": False,
+                    "description": "可选的 IANA 时区名称，省略时使用 UTC。",
+                    "schema": {
+                        "type": "string",
+                        "default": "UTC",
+                        "examples": ["UTC", "Asia/Shanghai"],
+                    },
+                }
+            ),
+        ),
+        response_schema=_freeze(
+            {
+                "type": "object",
+                "properties": {
+                    "utc": {"type": "string", "format": "date-time"},
+                    "unix_timestamp": {"type": "number"},
+                    "timezone": {"type": "string"},
+                    "local": {"type": "string", "format": "date-time"},
+                },
+                "required": ["utc", "unix_timestamp", "timezone", "local"],
+                "additionalProperties": False,
+            }
+        ),
+        error_codes=_COMMON_ERROR_CODES,
+        examples=(
+            _freeze(
+                {
+                    "language": "curl",
+                    "request": (
+                        "curl -G https://api.yeyubaka.top/v1/tools/time "
+                        "-H \"X-API-Key: <YOUR_API_KEY>\" "
+                        "--data-urlencode \"timezone=Asia/Shanghai\""
+                    ),
+                    "response": {
+                        "utc": "2026-01-01T00:00:00Z",
+                        "unix_timestamp": 1767225600,
+                        "timezone": "Asia/Shanghai",
+                        "local": "2026-01-01T08:00:00+08:00",
+                    },
+                }
+            ),
+        ),
+        visibility="public",
+        status="published",
+        is_free=True,
+        source_label="Yeyu API",
+        adapter_name="builtin-tools",
+        provider_ref="builtin-tools:time",
+        cache_rules=_freeze(
+            {
+                "cacheable": False,
+                "ttl_seconds": 0,
+                "stale_if_error": False,
+            }
+        ),
+    ),
+    CatalogSeed(
+        slug="uuid",
+        name="UUID v4 生成器",
+        summary="生成一个随机 UUID v4，不接受任何查询参数。",
+        category="tools",
+        method="GET",
+        path="/v1/tools/uuid",
+        auth_type="api_key",
+        parameters=(),
+        response_schema=_freeze(
+            {
+                "type": "object",
+                "properties": {
+                    "uuid": {"type": "string", "format": "uuid"},
+                    "version": {"type": "integer", "const": 4},
+                },
+                "required": ["uuid", "version"],
+                "additionalProperties": False,
+            }
+        ),
+        error_codes=_COMMON_ERROR_CODES,
+        examples=(
+            _freeze(
+                {
+                    "language": "curl",
+                    "request": (
+                        "curl https://api.yeyubaka.top/v1/tools/uuid "
+                        "-H \"X-API-Key: <YOUR_API_KEY>\""
+                    ),
+                    "response": {
+                        "uuid": "00000000-0000-4000-8000-000000000000",
+                        "version": 4,
+                    },
+                }
+            ),
+        ),
+        visibility="public",
+        status="published",
+        is_free=True,
+        source_label="Yeyu API",
+        adapter_name="builtin-tools",
+        provider_ref="builtin-tools:uuid",
+        cache_rules=_freeze(
+            {
+                "cacheable": False,
+                "ttl_seconds": 0,
+                "stale_if_error": False,
+            }
+        ),
+    ),
+)
+
+
+def seed_public_catalog(session: Session) -> None:
+    """Insert missing builtin catalog definitions without changing existing rows."""
+
+    added = False
+    for seed in PUBLIC_CATALOG_SEEDS:
+        existing = session.exec(
+            select(ApiDefinition).where(ApiDefinition.slug == seed.slug)
+        ).first()
+        if existing is not None:
+            continue
+        session.add(ApiDefinition(**seed.model_kwargs()))
+        added = True
+
+    if added:
+        session.commit()
+
+
+__all__ = ["CatalogSeed", "PUBLIC_CATALOG_SEEDS", "seed_public_catalog"]
diff --git a/backend/app/initial_data.py b/backend/app/initial_data.py
index d806c3d..388fd33 100644
--- a/backend/app/initial_data.py
+++ b/backend/app/initial_data.py
@@ -1,23 +1,25 @@
 import logging
 
 from sqlmodel import Session
 
+from app.catalog_seed import seed_public_catalog
 from app.core.db import engine, init_db
 
 logging.basicConfig(level=logging.INFO)
 logger = logging.getLogger(__name__)
 
 
 def init() -> None:
     with Session(engine) as session:
         init_db(session)
+        seed_public_catalog(session)
 
 
 def main() -> None:
     logger.info("Creating initial data")
     init()
     logger.info("Initial data created")
 
 
 if __name__ == "__main__":
     main()
diff --git a/backend/tests/services/test_catalog_seed.py b/backend/tests/services/test_catalog_seed.py
new file mode 100644
index 0000000..28425b8
--- /dev/null
+++ b/backend/tests/services/test_catalog_seed.py
@@ -0,0 +1,168 @@
+from __future__ import annotations
+
+import json
+from collections.abc import Iterator
+from dataclasses import FrozenInstanceError
+from datetime import datetime
+
+import pytest
+from sqlalchemy.pool import StaticPool
+from sqlmodel import Session, SQLModel, create_engine, select
+
+from app import initial_data
+from app.catalog_seed import PUBLIC_CATALOG_SEEDS, seed_public_catalog
+from app.models import ApiDefinition
+
+
+@pytest.fixture()
+def session() -> Iterator[Session]:
+    engine = create_engine(
+        "sqlite://",
+        connect_args={"check_same_thread": False},
+        poolclass=StaticPool,
+    )
+    SQLModel.metadata.create_all(engine)
+    with Session(engine) as db_session:
+        yield db_session
+
+
+def _definitions(session: Session) -> list[ApiDefinition]:
+    return list(
+        session.exec(select(ApiDefinition).order_by(ApiDefinition.slug)).all()
+    )
+
+
+def test_public_catalog_seed_creates_time_and_uuid_with_adapter_contract(
+    session: Session,
+) -> None:
+    seed_public_catalog(session)
+
+    definitions = _definitions(session)
+    assert [definition.slug for definition in definitions] == ["time", "uuid"]
+
+    for definition in definitions:
+        assert definition.method == "GET"
+        assert definition.auth_type == "api_key"
+        assert definition.adapter_name == "builtin-tools"
+        assert definition.visibility == "public"
+        assert definition.status in {"healthy", "published"}
+        assert definition.is_free is True
+        assert definition.path == f"/v1/tools/{definition.slug}"
+        assert definition.source_label == "Yeyu API"
+        assert definition.cache_rules["cacheable"] is False
+        assert definition.cache_rules["stale_if_error"] is False
+        assert "INVALID_PARAMETERS" in {
+            error["code"] for error in definition.error_codes
+        }
+
+        examples = json.dumps(definition.examples, ensure_ascii=False)
+        assert "<YOUR_API_KEY>" in examples
+        assert "sk-" not in examples
+
+    time_definition = definitions[0]
+    timezone_parameter = time_definition.parameters[0]
+    assert timezone_parameter["name"] == "timezone"
+    assert timezone_parameter["in"] == "query"
+    assert timezone_parameter["required"] is False
+    assert timezone_parameter["schema"]["default"] == "UTC"
+    assert set(time_definition.response_schema["properties"]) == {
+        "utc",
+        "unix_timestamp",
+        "timezone",
+        "local",
+    }
+
+    uuid_definition = definitions[1]
+    assert uuid_definition.parameters == []
+    assert uuid_definition.response_schema["properties"]["version"]["const"] == 4
+    assert set(uuid_definition.response_schema["required"]) == {"uuid", "version"}
+
+
+def test_public_catalog_seed_is_idempotent_and_preserves_admin_edits(
+    session: Session,
+) -> None:
+    seed_public_catalog(session)
+
+    time_definition = session.exec(
+        select(ApiDefinition).where(ApiDefinition.slug == "time")
+    ).one()
+    time_definition.summary = "管理员维护的时间工具说明"
+    time_definition.status = "healthy"
+    time_definition.examples = [
+        {"language": "text", "request": "管理员示例 <YOUR_API_KEY>"}
+    ]
+    time_definition.cache_rules = {
+        "cacheable": True,
+        "ttl_seconds": 7,
+        "stale_if_error": True,
+    }
+    time_definition.updated_at = datetime(2026, 10, 1, 12, 34, 56)
+    session.add(time_definition)
+    session.commit()
+    session.expire_all()
+
+    before = session.exec(
+        select(ApiDefinition).where(ApiDefinition.slug == "time")
+    ).one()
+    before_id = before.id
+    before_updated_at = before.updated_at
+
+    seed_public_catalog(session)
+    session.expire_all()
+
+    definitions = _definitions(session)
+    assert len(definitions) == 2
+    after = session.exec(
+        select(ApiDefinition).where(ApiDefinition.slug == "time")
+    ).one()
+    assert after.id == before_id
+    assert after.updated_at == before_updated_at
+    assert after.summary == "管理员维护的时间工具说明"
+    assert after.status == "healthy"
+    assert after.examples == [
+        {"language": "text", "request": "管理员示例 <YOUR_API_KEY>"}
+    ]
+    assert after.cache_rules == {
+        "cacheable": True,
+        "ttl_seconds": 7,
+        "stale_if_error": True,
+    }
+
+
+def test_public_catalog_seeds_are_deeply_immutable() -> None:
+    assert isinstance(PUBLIC_CATALOG_SEEDS, tuple)
+
+    with pytest.raises(TypeError):
+        PUBLIC_CATALOG_SEEDS[0] = PUBLIC_CATALOG_SEEDS[1]  # type: ignore[index]
+    with pytest.raises(FrozenInstanceError):
+        PUBLIC_CATALOG_SEEDS[0].slug = "changed"  # type: ignore[misc]
+    with pytest.raises(TypeError):
+        PUBLIC_CATALOG_SEEDS[0].parameters[0]["required"] = True  # type: ignore[index]
+
+
+def test_init_seeds_catalog_after_existing_init_db(monkeypatch: pytest.MonkeyPatch) -> None:
+    events: list[tuple[str, object]] = []
+
+    class SessionStub:
+        def __enter__(self) -> SessionStub:
+            return self
+
+        def __exit__(self, *_args: object) -> None:
+            return None
+
+    session = SessionStub()
+    monkeypatch.setattr(initial_data, "Session", lambda _engine: session)
+    monkeypatch.setattr(
+        initial_data,
+        "init_db",
+        lambda passed_session: events.append(("init_db", passed_session)),
+    )
+    monkeypatch.setattr(
+        initial_data,
+        "seed_public_catalog",
+        lambda passed_session: events.append(("seed", passed_session)),
+    )
+
+    initial_data.init()
+
+    assert events == [("init_db", session), ("seed", session)]
