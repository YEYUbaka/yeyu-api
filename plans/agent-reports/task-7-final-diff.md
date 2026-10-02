# Review package: 068092d..d56e495

## Commits
d56e495 docs: record task 3 catalog review
6d3c163 fix: close remaining catalog review findings
9c901eb fix: harden catalog examples and filters
04fcbd4 fix: close catalog review findings
ec82905 docs: record task 3 catalog implementation
a30e6e7 docs: record task 7-3 implementation report
c13adce feat: add public catalog and api detail pages
53b19fc docs: record task 2 shell review
e9efb91 docs: record task 7-2 repair report
673d806 fix: close public shell review findings
4c43285 docs: record task 7-2 implementation report
0acbfc3 feat: split public and protected web shells
e125ac2 docs: record task 1 catalog seed review
feb0136 feat: seed public builtin catalog

## Files changed
 backend/app/catalog_seed.py                        |  296 +++
 backend/app/initial_data.py                        |    2 +
 backend/tests/services/test_catalog_seed.py        |  168 ++
 frontend/package.json                              |    2 +-
 .../src/components/ApiCatalog/ApiDetailView.tsx    |  378 +++
 frontend/src/components/ApiCatalog/CatalogCard.tsx |   42 +
 .../src/components/ApiCatalog/CatalogFilters.tsx   |   72 +
 frontend/src/components/ApiCatalog/CatalogGrid.tsx |   19 +
 .../components/ApiCatalog/CatalogPagination.tsx    |   45 +
 .../src/components/ApiCatalog/CatalogSearch.tsx    |   53 +
 .../src/components/ApiCatalog/CatalogStates.tsx    |   64 +
 frontend/src/components/ApiCatalog/CodeExample.tsx |   67 +
 .../src/components/ApiCatalog/catalog-types.ts     |  220 ++
 frontend/src/components/Common/Footer.tsx          |   44 +-
 frontend/src/components/Common/Logo.tsx            |   55 +-
 .../src/components/PublicSite/PublicFooter.tsx     |   33 +
 .../src/components/PublicSite/PublicHeader.tsx     |   86 +
 .../src/components/PublicSite/PublicLayout.tsx     |   20 +
 frontend/src/components/Sidebar/AppSidebar.tsx     |    2 +-
 frontend/src/hooks/useAuth.ts                      |    2 +-
 frontend/src/index.css                             | 1160 +++++++++-
 frontend/src/routes/_layout.tsx                    |    7 +-
 frontend/src/routes/_layout/dashboard.tsx          |   34 +
 frontend/src/routes/_layout/index.tsx              |   31 -
 frontend/src/routes/catalog/$slug.tsx              |   48 +
 frontend/src/routes/catalog/index.tsx              |  223 ++
 frontend/src/routes/index.tsx                      |  210 ++
 frontend/src/routes/login.tsx                      |    6 +-
 frontend/tests/login.spec.ts                       |   33 +-
 frontend/tests/public-catalog.spec.ts              |  594 +++++
 plans/agent-reports/task-7-1-brief.md              |   37 +
 plans/agent-reports/task-7-1-diff.md               |  518 +++++
 plans/agent-reports/task-7-1-report.md             |   79 +
 plans/agent-reports/task-7-1-review.md             |   41 +
 plans/agent-reports/task-7-2-brief.md              |   52 +
 plans/agent-reports/task-7-2-diff.md               | 1574 +++++++++++++
 plans/agent-reports/task-7-2-fix-diff.md           |  261 +++
 plans/agent-reports/task-7-2-fix-review.md         |   36 +
 plans/agent-reports/task-7-2-report.md             |  172 ++
 plans/agent-reports/task-7-2-review.md             |   37 +
 plans/agent-reports/task-7-3-brief.md              |   58 +
 plans/agent-reports/task-7-3-diff.md               | 2409 ++++++++++++++++++++
 plans/agent-reports/task-7-3-fix-diff.md           | 1100 +++++++++
 plans/agent-reports/task-7-3-fix-review.md         |   39 +
 plans/agent-reports/task-7-3-report.md             |  264 +++
 plans/agent-reports/task-7-3-review.md             |   40 +
 plans/agent-reports/task-7-3-second-fix-diff.md    |  679 ++++++
 plans/agent-reports/task-7-3-second-fix-review.md  |   41 +
 plans/agent-reports/task-7-3-third-fix-diff.md     |  489 ++++
 plans/agent-reports/task-7-3-third-fix-review.md   |   24 +
 plans/fix-task-7-3-catalog-review-findings.md      |   67 +
 plans/fix-task-7-3-second-review-findings.md       |   26 +
 plans/task-7-public-catalog-ui.md                  |   88 +-
 53 files changed, 11986 insertions(+), 161 deletions(-)

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
diff --git a/frontend/package.json b/frontend/package.json
index 3a63aca..568862d 100644
--- a/frontend/package.json
+++ b/frontend/package.json
@@ -1,19 +1,19 @@
 {
   "name": "frontend",
   "private": true,
   "packageManager": "pnpm@10.28.2",
   "version": "0.0.0",
   "type": "module",
   "scripts": {
     "dev": "vite",
-    "build": "tsc -p tsconfig.build.json && vite build",
+    "build": "vite build && tsc -p tsconfig.build.json",
     "lint": "biome check --write --unsafe --no-errors-on-unmatched --files-ignore-unknown=true ./",
     "preview": "vite preview",
     "generate-client": "openapi-ts",
     "test": "pnpm exec playwright test",
     "test:ui": "pnpm exec playwright test --ui"
   },
   "dependencies": {
     "@hookform/resolvers": "^5.7.1",
     "@radix-ui/react-avatar": "^1.2.6",
     "@radix-ui/react-checkbox": "^1.3.11",
diff --git a/frontend/src/components/ApiCatalog/ApiDetailView.tsx b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
new file mode 100644
index 0000000..a650887
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
@@ -0,0 +1,378 @@
+import { Link } from "@tanstack/react-router"
+
+import type { ApiDetail } from "@/client"
+
+import CodeExample from "./CodeExample"
+import {
+  asRecord,
+  asText,
+  buildPublicApiUrl,
+  formatMetadata,
+  formatUpdatedAt,
+  normalizeInternalApiPath,
+  normalizeSafeQueryKey,
+  normalizeSafeQueryValue,
+  PUBLIC_API_AUTH_HEADER,
+  PUBLIC_API_BASE_URL,
+  responseProperties,
+  sanitizeMetadata,
+} from "./catalog-types"
+
+type QueryExample = {
+  name: string
+  value: string
+}
+
+function parameterExamples(detail: ApiDetail): QueryExample[] {
+  return detail.parameters.flatMap((parameter) => {
+    const safeParameter = asRecord(sanitizeMetadata(parameter))
+    if (!safeParameter || asText(safeParameter.in, "") !== "query") {
+      return []
+    }
+
+    const name = normalizeSafeQueryKey(safeParameter.name)
+    if (!name) return []
+
+    const schema = asRecord(safeParameter.schema)
+    const candidates = [
+      ...(Array.isArray(schema?.examples) ? schema.examples : []),
+      schema?.default,
+    ]
+    const value = candidates
+      .map((candidate) => normalizeSafeQueryValue(candidate))
+      .find((candidate): candidate is string => candidate !== undefined)
+    if (!value) return []
+
+    return [{ name, value }]
+  })
+}
+
+function quoteCurlArgument(value: string): string {
+  return `'${value.replaceAll("'", "'\\''")}'`
+}
+
+function buildCodeExamples(detail: ApiDetail) {
+  const candidateMethod = detail.method.toUpperCase()
+  const method = /^[A-Z]{1,16}$/.test(candidateMethod) ? candidateMethod : "GET"
+  const queryParameters = parameterExamples(detail)
+  const path = normalizeInternalApiPath(detail.path)
+  const absoluteUrl = buildPublicApiUrl(path)
+  if (!path || !absoluteUrl) {
+    const unavailable = "无法生成示例：目录路径不可用。"
+    return {
+      curl: unavailable,
+      javascript: unavailable,
+      python: unavailable,
+    }
+  }
+
+  const curlStart =
+    method === "GET"
+      ? `curl -G ${quoteCurlArgument(absoluteUrl)}`
+      : `curl -X ${method} ${quoteCurlArgument(absoluteUrl)}`
+  const curlLines = [
+    curlStart,
+    `  -H ${quoteCurlArgument(`${PUBLIC_API_AUTH_HEADER}: <YOUR_API_KEY>`)}`,
+  ]
+  for (const parameter of queryParameters) {
+    curlLines.push(
+      `  --data-urlencode ${quoteCurlArgument(`${parameter.name}=${parameter.value}`)}`,
+    )
+  }
+
+  const javascriptLines = [
+    `const endpoint = new URL(${JSON.stringify(path)}, ${JSON.stringify(PUBLIC_API_BASE_URL)});`,
+    ...queryParameters.map(
+      (parameter) =>
+        `endpoint.searchParams.set(${JSON.stringify(parameter.name)}, ${JSON.stringify(parameter.value)});`,
+    ),
+    "",
+    "const response = await fetch(endpoint, {",
+    `  method: ${JSON.stringify(method)},`,
+    "  headers: {",
+    `    ${JSON.stringify(PUBLIC_API_AUTH_HEADER)}: "<YOUR_API_KEY>",`,
+    "  },",
+    "});",
+    "const data = await response.json();",
+    "console.log(data);",
+  ]
+
+  const pythonLines = [
+    "import requests",
+    "",
+    "response = requests.request(",
+    `    ${JSON.stringify(method)},`,
+    `    ${JSON.stringify(absoluteUrl)},`,
+    `    headers={${JSON.stringify(PUBLIC_API_AUTH_HEADER)}: "<YOUR_API_KEY>"},`,
+    ...(queryParameters.length
+      ? [
+          `    params=${JSON.stringify(Object.fromEntries(queryParameters.map((parameter) => [parameter.name, parameter.value])))},`,
+        ]
+      : []),
+    "    timeout=10,",
+    ")",
+    "response.raise_for_status()",
+    "print(response.json())",
+  ]
+
+  return {
+    curl: curlLines.join(" \\\n"),
+    javascript: javascriptLines.join("\n"),
+    python: pythonLines.join("\n"),
+  }
+}
+
+function readableCacheKey(key: string) {
+  return key
+    .replaceAll("_", " ")
+    .replace(/\b\w/g, (character) => character.toUpperCase())
+}
+
+interface ApiDetailViewProps {
+  detail: ApiDetail
+}
+
+export function ApiDetailView({ detail }: ApiDetailViewProps) {
+  const authHeader = PUBLIC_API_AUTH_HEADER
+  const examples = buildCodeExamples(detail)
+  const responseFields = responseProperties(detail)
+  const safePath = normalizeInternalApiPath(detail.path)
+  const safeCacheRules = asRecord(sanitizeMetadata(detail.cache_rules)) ?? {}
+  const cacheEntries = Object.entries(safeCacheRules)
+
+  return (
+    <div className="api-detail-page">
+      <div className="api-detail-breadcrumbs">
+        <Link to="/catalog" className="public-text-link">
+          ← 返回公开目录
+        </Link>
+        <span aria-hidden="true">/</span>
+        <span>{detail.category}</span>
+      </div>
+
+      <header className="api-detail-header">
+        <div className="api-detail-path-row">
+          <span className="catalog-method-badge">{detail.method}</span>
+          <code>{safePath ?? "路径不可用"}</code>
+        </div>
+        <h1 className="api-detail-title">{detail.name}</h1>
+        <p className="api-detail-summary">{detail.summary}</p>
+        <div className="api-detail-tags">
+          {detail.is_free ? (
+            <span className="catalog-tag catalog-tag-free">免费</span>
+          ) : null}
+          <span className="catalog-tag catalog-tag-status">
+            {detail.status}
+          </span>
+          <time dateTime={detail.updated_at ?? undefined}>
+            更新于 {formatUpdatedAt(detail.updated_at)}
+          </time>
+        </div>
+      </header>
+
+      <div className="api-detail-layout">
+        <main className="api-detail-main">
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-auth-heading"
+          >
+            <p className="public-eyebrow">AUTHENTICATION</p>
+            <h2 id="api-auth-heading" className="api-detail-section-title">
+              API Key 鉴权
+            </h2>
+            <p className="api-detail-copy">
+              调用该接口时，请在 <code>{authHeader}</code> 请求头中提供你的 API
+              Key。浏览器登录 Cookie 不会替代 API Key。
+            </p>
+            <div className="api-auth-callout">
+              <span>请求头</span>
+              <code>{authHeader}: &lt;YOUR_API_KEY&gt;</code>
+            </div>
+          </section>
+
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-parameters-heading"
+          >
+            <p className="public-eyebrow">REQUEST</p>
+            <h2
+              id="api-parameters-heading"
+              className="api-detail-section-title"
+            >
+              参数
+            </h2>
+            {detail.parameters.length ? (
+              <div className="api-table-scroll">
+                <table className="api-detail-table">
+                  <thead>
+                    <tr>
+                      <th scope="col">名称</th>
+                      <th scope="col">位置</th>
+                      <th scope="col">必填</th>
+                      <th scope="col">类型 / 说明</th>
+                    </tr>
+                  </thead>
+                  <tbody>
+                    {detail.parameters.map((parameter, index) => {
+                      const safeParameter =
+                        asRecord(sanitizeMetadata(parameter)) ?? {}
+                      const schema = asRecord(safeParameter.schema)
+                      const name =
+                        normalizeSafeQueryKey(safeParameter.name) ??
+                        `参数 ${index + 1}`
+                      const schemaText = asText(schema?.type, "—")
+                      const description = asText(safeParameter.description, "")
+                      return (
+                        <tr
+                          key={`${name}-${asText(safeParameter.in, "unknown")}-${index}`}
+                        >
+                          <th scope="row">
+                            <code>{name}</code>
+                          </th>
+                          <td>{asText(safeParameter.in)}</td>
+                          <td>
+                            {safeParameter.required === true ? "是" : "否"}
+                          </td>
+                          <td>
+                            <span>{schemaText}</span>
+                            {description ? (
+                              <span className="api-table-note">
+                                {description}
+                              </span>
+                            ) : null}
+                          </td>
+                        </tr>
+                      )
+                    })}
+                  </tbody>
+                </table>
+              </div>
+            ) : (
+              <p className="api-detail-muted">该接口不接受参数。</p>
+            )}
+          </section>
+
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-response-heading"
+          >
+            <p className="public-eyebrow">RESPONSE</p>
+            <h2 id="api-response-heading" className="api-detail-section-title">
+              响应结构
+            </h2>
+            {responseFields.length ? (
+              <div className="api-response-fields">
+                {responseFields.map(([name, schema]) => (
+                  <div key={name} className="api-response-field">
+                    <code>{name}</code>
+                    <span>{asText(schema.type, "object")}</span>
+                    {schema.format ? (
+                      <span>{asText(schema.format)}</span>
+                    ) : null}
+                  </div>
+                ))}
+              </div>
+            ) : null}
+            <pre className="api-json-block">
+              <code>{formatMetadata(detail.response_schema)}</code>
+            </pre>
+          </section>
+
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-errors-heading"
+          >
+            <p className="public-eyebrow">ERRORS</p>
+            <h2 id="api-errors-heading" className="api-detail-section-title">
+              错误码
+            </h2>
+            {detail.errors.length ? (
+              <div className="api-table-scroll">
+                <table className="api-detail-table">
+                  <thead>
+                    <tr>
+                      <th scope="col">HTTP</th>
+                      <th scope="col">错误码</th>
+                      <th scope="col">说明</th>
+                    </tr>
+                  </thead>
+                  <tbody>
+                    {detail.errors.map((error, index) => {
+                      const safeError = asRecord(sanitizeMetadata(error)) ?? {}
+                      return (
+                        <tr key={`${asText(safeError.code, "error")}-${index}`}>
+                          <td>{asText(safeError.status)}</td>
+                          <th scope="row">
+                            <code>{asText(safeError.code)}</code>
+                          </th>
+                          <td>
+                            {asText(
+                              safeError.description,
+                              asText(safeError.message),
+                            )}
+                          </td>
+                        </tr>
+                      )
+                    })}
+                  </tbody>
+                </table>
+              </div>
+            ) : (
+              <p className="api-detail-muted">目录暂未提供错误码说明。</p>
+            )}
+          </section>
+
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-examples-heading"
+          >
+            <p className="public-eyebrow">EXAMPLES</p>
+            <h2 id="api-examples-heading" className="api-detail-section-title">
+              安全调用示例
+            </h2>
+            <p className="api-detail-copy">
+              示例只使用占位密钥，不会读取或保存浏览器中的真实凭据。
+            </p>
+            <div className="api-code-grid">
+              <CodeExample language="curl" code={examples.curl} />
+              <CodeExample language="JavaScript" code={examples.javascript} />
+              <CodeExample language="Python" code={examples.python} />
+            </div>
+          </section>
+        </main>
+
+        <aside className="api-detail-aside" aria-label="接口补充信息">
+          <section
+            className="api-aside-card"
+            aria-labelledby="api-source-heading"
+          >
+            <p className="public-eyebrow">SOURCE</p>
+            <h2 id="api-source-heading" className="api-aside-title">
+              来源
+            </h2>
+            <p className="api-aside-value">{detail.source}</p>
+          </section>
+          <section
+            className="api-aside-card"
+            aria-labelledby="api-cache-heading"
+          >
+            <p className="public-eyebrow">CACHE</p>
+            <h2 id="api-cache-heading" className="api-aside-title">
+              缓存规则
+            </h2>
+            <dl className="api-cache-list">
+              {cacheEntries.map(([key, value]) => (
+                <div key={key}>
+                  <dt>{readableCacheKey(key)}</dt>
+                  <dd>{formatMetadata(value)}</dd>
+                </div>
+              ))}
+            </dl>
+          </section>
+        </aside>
+      </div>
+    </div>
+  )
+}
+
+export default ApiDetailView
diff --git a/frontend/src/components/ApiCatalog/CatalogCard.tsx b/frontend/src/components/ApiCatalog/CatalogCard.tsx
new file mode 100644
index 0000000..5b3c94e
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogCard.tsx
@@ -0,0 +1,42 @@
+import { Link } from "@tanstack/react-router"
+
+import type { CatalogItem } from "@/client"
+
+import { formatUpdatedAt } from "./catalog-types"
+
+interface CatalogCardProps {
+  item: CatalogItem
+}
+
+export function CatalogCard({ item }: CatalogCardProps) {
+  return (
+    <article className="catalog-card" data-testid={`catalog-card-${item.slug}`}>
+      <div className="catalog-card-path">
+        <span className="catalog-method-badge">{item.method}</span>
+        <code>{item.path}</code>
+      </div>
+      <div className="catalog-card-content">
+        <Link
+          to="/catalog/$slug"
+          params={{ slug: item.slug }}
+          className="catalog-card-title"
+        >
+          {item.name}
+        </Link>
+        <p className="catalog-card-summary">{item.summary}</p>
+      </div>
+      <div className="catalog-card-meta">
+        <span className="catalog-tag">{item.category}</span>
+        {item.is_free ? (
+          <span className="catalog-tag catalog-tag-free">免费</span>
+        ) : null}
+        <span className="catalog-tag catalog-tag-status">{item.status}</span>
+        <time dateTime={item.updated_at ?? undefined}>
+          更新于 {formatUpdatedAt(item.updated_at)}
+        </time>
+      </div>
+    </article>
+  )
+}
+
+export default CatalogCard
diff --git a/frontend/src/components/ApiCatalog/CatalogFilters.tsx b/frontend/src/components/ApiCatalog/CatalogFilters.tsx
new file mode 100644
index 0000000..2df3a59
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogFilters.tsx
@@ -0,0 +1,72 @@
+import type { CatalogItem } from "@/client"
+
+import { uniqueCatalogValues } from "./catalog-types"
+
+interface CatalogFiltersProps {
+  items: CatalogItem[]
+  category?: string
+  status?: string
+  onCategoryChange: (value: string) => void
+  onStatusChange: (value: string) => void
+}
+
+export function CatalogFilters({
+  items,
+  category,
+  status,
+  onCategoryChange,
+  onStatusChange,
+}: CatalogFiltersProps) {
+  const categories = uniqueCatalogValues(items, "category", category)
+  const statuses = uniqueCatalogValues(items, "status", status)
+
+  return (
+    <section
+      className="catalog-filters"
+      aria-labelledby="catalog-filter-heading"
+    >
+      <div>
+        <p className="public-eyebrow">筛选</p>
+        <h2 id="catalog-filter-heading" className="catalog-filter-title">
+          缩小公开接口范围
+        </h2>
+      </div>
+      <div className="catalog-filter-controls">
+        <div className="catalog-filter-field">
+          <label htmlFor="catalog-category">分类</label>
+          <select
+            id="catalog-category"
+            aria-label="分类"
+            value={category ?? ""}
+            onChange={(event) => onCategoryChange(event.target.value)}
+          >
+            <option value="">全部分类</option>
+            {categories.map((value) => (
+              <option key={value} value={value}>
+                {value}
+              </option>
+            ))}
+          </select>
+        </div>
+        <div className="catalog-filter-field">
+          <label htmlFor="catalog-status">状态</label>
+          <select
+            id="catalog-status"
+            aria-label="状态"
+            value={status ?? ""}
+            onChange={(event) => onStatusChange(event.target.value)}
+          >
+            <option value="">全部状态</option>
+            {statuses.map((value) => (
+              <option key={value} value={value}>
+                {value}
+              </option>
+            ))}
+          </select>
+        </div>
+      </div>
+    </section>
+  )
+}
+
+export default CatalogFilters
diff --git a/frontend/src/components/ApiCatalog/CatalogGrid.tsx b/frontend/src/components/ApiCatalog/CatalogGrid.tsx
new file mode 100644
index 0000000..86425a4
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogGrid.tsx
@@ -0,0 +1,19 @@
+import type { CatalogItem } from "@/client"
+
+import CatalogCard from "./CatalogCard"
+
+interface CatalogGridProps {
+  items: CatalogItem[]
+}
+
+export function CatalogGrid({ items }: CatalogGridProps) {
+  return (
+    <div className="catalog-grid" data-testid="catalog-grid">
+      {items.map((item) => (
+        <CatalogCard key={item.slug} item={item} />
+      ))}
+    </div>
+  )
+}
+
+export default CatalogGrid
diff --git a/frontend/src/components/ApiCatalog/CatalogPagination.tsx b/frontend/src/components/ApiCatalog/CatalogPagination.tsx
new file mode 100644
index 0000000..b530923
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogPagination.tsx
@@ -0,0 +1,45 @@
+interface CatalogPaginationProps {
+  count: number
+  page: number
+  pageSize: number
+  isFetching?: boolean
+  onPageChange: (page: number) => void
+}
+
+export function CatalogPagination({
+  count,
+  page,
+  pageSize,
+  isFetching = false,
+  onPageChange,
+}: CatalogPaginationProps) {
+  const safePageSize = Math.max(1, pageSize)
+  const totalPages = Math.max(1, Math.ceil(count / safePageSize))
+  if (totalPages <= 1) return null
+
+  return (
+    <nav className="catalog-pagination" aria-label="目录分页">
+      <button
+        type="button"
+        className="public-inline-button"
+        disabled={isFetching || page <= 1}
+        onClick={() => onPageChange(page - 1)}
+      >
+        上一页
+      </button>
+      <span aria-live="polite">
+        第 {page} / {totalPages} 页
+      </span>
+      <button
+        type="button"
+        className="public-inline-button"
+        disabled={isFetching || page >= totalPages}
+        onClick={() => onPageChange(page + 1)}
+      >
+        下一页
+      </button>
+    </nav>
+  )
+}
+
+export default CatalogPagination
diff --git a/frontend/src/components/ApiCatalog/CatalogSearch.tsx b/frontend/src/components/ApiCatalog/CatalogSearch.tsx
new file mode 100644
index 0000000..a625b17
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogSearch.tsx
@@ -0,0 +1,53 @@
+import { Search, X } from "lucide-react"
+
+interface CatalogSearchProps {
+  value: string
+  onChange: (value: string) => void
+}
+
+export function CatalogSearch({ value, onChange }: CatalogSearchProps) {
+  return (
+    <section
+      className="catalog-search-panel"
+      aria-labelledby="catalog-search-heading"
+    >
+      <div className="catalog-search-heading">
+        <div>
+          <p className="public-eyebrow">搜索优先</p>
+          <h2 id="catalog-search-heading" className="catalog-search-title">
+            先按接口名、简介或路径查找
+          </h2>
+        </div>
+        <p className="catalog-search-hint">输入停止后约 400ms 更新目录</p>
+      </div>
+      <div className="catalog-search-control">
+        <Search aria-hidden="true" className="catalog-search-icon" />
+        <label className="sr-only" htmlFor="catalog-search-input">
+          搜索公开 API
+        </label>
+        <input
+          id="catalog-search-input"
+          data-testid="catalog-search-input"
+          className="catalog-search-input"
+          type="search"
+          value={value}
+          onChange={(event) => onChange(event.target.value)}
+          placeholder="例如：时间、UUID、工具"
+          autoComplete="off"
+        />
+        {value ? (
+          <button
+            type="button"
+            className="catalog-search-clear"
+            aria-label="清除搜索"
+            onClick={() => onChange("")}
+          >
+            <X aria-hidden="true" />
+          </button>
+        ) : null}
+      </div>
+    </section>
+  )
+}
+
+export default CatalogSearch
diff --git a/frontend/src/components/ApiCatalog/CatalogStates.tsx b/frontend/src/components/ApiCatalog/CatalogStates.tsx
new file mode 100644
index 0000000..760889d
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogStates.tsx
@@ -0,0 +1,64 @@
+interface CatalogErrorStateProps {
+  onRetry: () => void
+}
+
+export function CatalogLoadingState() {
+  return (
+    <div
+      className="catalog-state catalog-skeleton-list"
+      data-testid="catalog-loading"
+      role="status"
+      aria-label="正在加载公开目录"
+    >
+      <span className="catalog-skeleton-line catalog-skeleton-line-wide" />
+      <span className="catalog-skeleton-line" />
+      <span className="catalog-skeleton-line catalog-skeleton-line-short" />
+      <span className="sr-only">正在读取真实目录……</span>
+    </div>
+  )
+}
+
+export function CatalogErrorState({ onRetry }: CatalogErrorStateProps) {
+  return (
+    <div
+      className="catalog-state catalog-state-error"
+      data-testid="catalog-error"
+      role="alert"
+    >
+      <div>
+        <p className="catalog-state-kicker">目录读取失败</p>
+        <p>公开目录暂时无法读取，请稍后重试。</p>
+      </div>
+      <button type="button" className="public-inline-button" onClick={onRetry}>
+        重试
+      </button>
+    </div>
+  )
+}
+
+export function CatalogEmptyState() {
+  return (
+    <div className="catalog-state" data-testid="catalog-empty" role="status">
+      <p className="catalog-state-kicker">没有匹配结果</p>
+      <p>没有找到匹配的公开接口，请换一个关键词或清除筛选。</p>
+    </div>
+  )
+}
+
+export function CatalogDetailErrorState({ onRetry }: CatalogErrorStateProps) {
+  return (
+    <div
+      className="catalog-state catalog-state-error"
+      data-testid="catalog-detail-error"
+      role="alert"
+    >
+      <div>
+        <p className="catalog-state-kicker">详情读取失败</p>
+        <p>该接口可能已下线，或目录服务暂时不可用。</p>
+      </div>
+      <button type="button" className="public-inline-button" onClick={onRetry}>
+        重试
+      </button>
+    </div>
+  )
+}
diff --git a/frontend/src/components/ApiCatalog/CodeExample.tsx b/frontend/src/components/ApiCatalog/CodeExample.tsx
new file mode 100644
index 0000000..bcec275
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CodeExample.tsx
@@ -0,0 +1,67 @@
+import { Check, Copy } from "lucide-react"
+import { useState } from "react"
+
+interface CodeExampleProps {
+  language: string
+  code: string
+}
+
+function codeId(language: string) {
+  return language.toLowerCase().replace(/[^a-z0-9]+/g, "-")
+}
+
+export function CodeExample({ language, code }: CodeExampleProps) {
+  const [copyState, setCopyState] = useState<"idle" | "success" | "error">(
+    "idle",
+  )
+  const headingId = `code-example-${codeId(language)}`
+
+  const copyCode = async () => {
+    if (!navigator.clipboard) {
+      setCopyState("error")
+      return
+    }
+
+    try {
+      await navigator.clipboard.writeText(code)
+      setCopyState("success")
+    } catch {
+      setCopyState("error")
+    }
+  }
+
+  const buttonLabel = copyState === "success" ? "已复制" : "复制"
+
+  return (
+    <section className="code-example" aria-labelledby={headingId}>
+      <div className="code-example-header">
+        <h3 id={headingId}>{language}</h3>
+        <button
+          type="button"
+          className="code-copy-button"
+          aria-label={`复制 ${language} 示例`}
+          onClick={() => void copyCode()}
+        >
+          {copyState === "success" ? (
+            <Check aria-hidden="true" />
+          ) : (
+            <Copy aria-hidden="true" />
+          )}
+          <span>{buttonLabel}</span>
+        </button>
+      </div>
+      <pre className="code-example-block">
+        <code>{code}</code>
+      </pre>
+      <p className="code-example-feedback" aria-live="polite">
+        {copyState === "success"
+          ? `${language} 示例已复制到剪贴板。`
+          : copyState === "error"
+            ? "复制失败，请手动选择代码。"
+            : ""}
+      </p>
+    </section>
+  )
+}
+
+export default CodeExample
diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
new file mode 100644
index 0000000..ed14c2e
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/catalog-types.ts
@@ -0,0 +1,220 @@
+import type { ApiDetail, CatalogItem } from "@/client"
+
+export type CatalogSearchParams = {
+  query?: string
+  category?: string
+  status?: string
+  page: number
+}
+
+export type CatalogMetadata = Record<string, unknown>
+
+export type CatalogFacetResult =
+  | {
+      items: CatalogItem[]
+      complete: true
+    }
+  | {
+      items: []
+      complete: false
+      reason: "page-limit"
+    }
+
+export const PUBLIC_API_BASE_URL = "https://api.yeyubaka.top"
+export const PUBLIC_API_AUTH_HEADER = "X-API-Key"
+
+const SENSITIVE_METADATA_KEY_PARTS = [
+  "token",
+  "secret",
+  "password",
+  "authorization",
+  "cookie",
+  "apikey",
+  "credential",
+  "privatekey",
+  "providerref",
+]
+const SAFE_QUERY_KEY_PATTERN = /^[A-Za-z][A-Za-z0-9_.-]{0,63}$/
+const SAFE_QUERY_VALUE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/+:-]{0,127}$/
+const QUERY_VALUE_SCHEME_PATTERN = /^[A-Za-z][A-Za-z0-9+.-]*:/
+const SENSITIVE_QUERY_VALUE_PATTERN =
+  /(token|secret|password|authorization|cookie|api[-_]?key|credential|private[-_]?key|bearer)/i
+const JWT_LIKE_PATTERN =
+  /^[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}$/
+
+function normalizedMetadataKey(key: string): string {
+  return key.toLowerCase().replace(/[^a-z0-9]/g, "")
+}
+
+function isSensitiveMetadataKey(key: string): boolean {
+  const normalized = normalizedMetadataKey(key)
+  return SENSITIVE_METADATA_KEY_PARTS.some((part) => normalized.includes(part))
+}
+
+export function normalizeSearchValue(value: unknown): string | undefined {
+  if (typeof value !== "string") return undefined
+  const normalized = value.trim()
+  return normalized || undefined
+}
+
+export function normalizeSafeQueryKey(value: unknown): string | undefined {
+  return typeof value === "string" &&
+    SAFE_QUERY_KEY_PATTERN.test(value) &&
+    !isSensitiveMetadataKey(value)
+    ? value
+    : undefined
+}
+
+export function normalizeSafeQueryValue(value: unknown): string | undefined {
+  const text =
+    typeof value === "string"
+      ? value
+      : typeof value === "number" && Number.isFinite(value)
+        ? String(value)
+        : typeof value === "boolean"
+          ? String(value)
+          : undefined
+
+  if (
+    !text ||
+    text !== text.trim() ||
+    !SAFE_QUERY_VALUE_PATTERN.test(text) ||
+    text.includes("://") ||
+    QUERY_VALUE_SCHEME_PATTERN.test(text) ||
+    SENSITIVE_QUERY_VALUE_PATTERN.test(text) ||
+    JWT_LIKE_PATTERN.test(text)
+  ) {
+    return undefined
+  }
+
+  return text
+}
+
+export function normalizePage(value: unknown): number {
+  const page =
+    typeof value === "number"
+      ? value
+      : typeof value === "string" && value.trim()
+        ? Number(value)
+        : Number.NaN
+
+  return Number.isSafeInteger(page) && page > 0 ? page : 1
+}
+
+export function normalizeInternalApiPath(value: unknown): string | undefined {
+  if (typeof value !== "string") return undefined
+
+  const normalized = value.trim()
+  if (!normalized) return undefined
+
+  if (
+    !normalized.startsWith("/") ||
+    normalized.startsWith("//") ||
+    normalized.includes("//") ||
+    /https?:/i.test(normalized) ||
+    normalized.includes("\\") ||
+    /[?#%]/.test(normalized) ||
+    normalized.includes("..")
+  ) {
+    return undefined
+  }
+
+  return normalized
+}
+
+export function buildPublicApiUrl(value: unknown): string | undefined {
+  const path = normalizeInternalApiPath(value)
+  return path ? `${PUBLIC_API_BASE_URL}${path}` : undefined
+}
+
+export function parseCatalogSearch(
+  search: Record<string, unknown>,
+): CatalogSearchParams {
+  return {
+    query: normalizeSearchValue(search.query),
+    category: normalizeSearchValue(search.category),
+    status: normalizeSearchValue(search.status),
+    page: normalizePage(search.page),
+  }
+}
+
+export function formatUpdatedAt(value?: string | null): string {
+  if (!value) return "更新时间待补充"
+
+  const timestamp = Date.parse(value)
+  if (Number.isNaN(timestamp)) return value
+
+  return new Intl.DateTimeFormat("zh-HK", {
+    dateStyle: "medium",
+  }).format(new Date(timestamp))
+}
+
+export function asRecord(value: unknown): CatalogMetadata | undefined {
+  if (typeof value !== "object" || value === null || Array.isArray(value)) {
+    return undefined
+  }
+  return value as CatalogMetadata
+}
+
+export function asText(value: unknown, fallback = "—"): string {
+  if (typeof value === "string") return value
+  if (typeof value === "number" || typeof value === "boolean") {
+    return String(value)
+  }
+  return fallback
+}
+
+export function sanitizeMetadata(value: unknown): unknown {
+  if (Array.isArray(value)) {
+    return value.map((item) => sanitizeMetadata(item))
+  }
+
+  if (typeof value !== "object" || value === null) return value
+
+  const sanitized: CatalogMetadata = {}
+  for (const [key, nestedValue] of Object.entries(value)) {
+    if (isSensitiveMetadataKey(key)) continue
+    sanitized[key] = sanitizeMetadata(nestedValue)
+  }
+  return sanitized
+}
+
+export function formatMetadata(value: unknown): string {
+  const sanitized = sanitizeMetadata(value)
+  if (sanitized === null || sanitized === undefined) return "—"
+  if (typeof sanitized === "string") return sanitized
+  if (typeof sanitized === "number" || typeof sanitized === "boolean") {
+    return String(sanitized)
+  }
+
+  try {
+    return JSON.stringify(sanitized, null, 2) ?? "无法展示"
+  } catch {
+    return "无法展示"
+  }
+}
+
+export function responseProperties(
+  detail: ApiDetail,
+): Array<[string, CatalogMetadata]> {
+  const safeResponseSchema = asRecord(sanitizeMetadata(detail.response_schema))
+  const properties = safeResponseSchema?.properties
+  if (!properties || typeof properties !== "object") return []
+
+  return Object.entries(properties)
+    .map(
+      ([name, value]) =>
+        [name, asRecord(value) ?? {}] as [string, CatalogMetadata],
+    )
+    .sort(([left], [right]) => left.localeCompare(right))
+}
+
+export function uniqueCatalogValues(
+  items: CatalogItem[],
+  field: "category" | "status",
+  currentValue?: string,
+): string[] {
+  const values = new Set(items.map((item) => item[field]).filter(Boolean))
+  if (currentValue) values.add(currentValue)
+  return Array.from(values).sort((left, right) => left.localeCompare(right))
+}
diff --git a/frontend/src/components/Common/Footer.tsx b/frontend/src/components/Common/Footer.tsx
index 279e1e7..5687a91 100644
--- a/frontend/src/components/Common/Footer.tsx
+++ b/frontend/src/components/Common/Footer.tsx
@@ -1,44 +1,30 @@
-import { FaGithub, FaLinkedinIn } from "react-icons/fa"
-import { FaXTwitter } from "react-icons/fa6"
-
-const socialLinks = [
-  {
-    icon: FaGithub,
-    href: "https://github.com/fastapi/fastapi",
-    label: "GitHub",
-  },
-  { icon: FaXTwitter, href: "https://x.com/fastapi", label: "X" },
-  {
-    icon: FaLinkedinIn,
-    href: "https://linkedin.com/company/fastapi",
-    label: "LinkedIn",
-  },
-]
+import { Link } from "@tanstack/react-router"
 
 export function Footer() {
   const currentYear = new Date().getFullYear()
 
   return (
     <footer className="border-t py-4 px-6">
       <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
         <p className="text-muted-foreground text-sm">
-          Full Stack FastAPI Template - {currentYear}
+          Yeyu API 公益平台 - {currentYear}
         </p>
         <div className="flex items-center gap-4">
-          {socialLinks.map(({ icon: Icon, href, label }) => (
-            <a
-              key={label}
-              href={href}
-              target="_blank"
-              rel="noopener noreferrer"
-              aria-label={label}
-              className="text-muted-foreground hover:text-foreground transition-colors"
-            >
-              <Icon className="h-5 w-5" />
-            </a>
-          ))}
+          <Link
+            to="/"
+            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
+          >
+            返回公共首页
+          </Link>
+          <Link
+            to="/"
+            hash="usage"
+            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
+          >
+            使用规范
+          </Link>
         </div>
       </div>
     </footer>
   )
 }
diff --git a/frontend/src/components/Common/Logo.tsx b/frontend/src/components/Common/Logo.tsx
index 05c299f..d574f16 100644
--- a/frontend/src/components/Common/Logo.tsx
+++ b/frontend/src/components/Common/Logo.tsx
@@ -1,60 +1,61 @@
 import { Link } from "@tanstack/react-router"
 
-import { useTheme } from "@/components/theme-provider"
 import { cn } from "@/lib/utils"
-import icon from "/assets/images/fastapi-icon.svg"
-import iconLight from "/assets/images/fastapi-icon-light.svg"
-import logo from "/assets/images/fastapi-logo.svg"
-import logoLight from "/assets/images/fastapi-logo-light.svg"
 
 interface LogoProps {
   variant?: "full" | "icon" | "responsive"
   className?: string
   asLink?: boolean
 }
 
 export function Logo({
   variant = "full",
   className,
   asLink = true,
 }: LogoProps) {
-  const { resolvedTheme } = useTheme()
-  const isDark = resolvedTheme === "dark"
-
-  const fullLogo = isDark ? logoLight : logo
-  const iconLogo = isDark ? iconLight : icon
-
   const content =
     variant === "responsive" ? (
       <>
-        <img
-          src={fullLogo}
-          alt="FastAPI"
+        <span
+          aria-hidden="true"
           className={cn(
-            "h-6 w-auto group-data-[collapsible=icon]:hidden",
+            "inline-flex h-7 items-center gap-1.5 text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden",
             className,
           )}
-        />
-        <img
-          src={iconLogo}
-          alt="FastAPI"
+        >
+          <span className="logo-mark">Y</span>
+          <span>Yeyu API</span>
+        </span>
+        <span
+          aria-hidden="true"
           className={cn(
-            "size-5 hidden group-data-[collapsible=icon]:block",
+            "logo-mark hidden size-7 items-center justify-center text-sm group-data-[collapsible=icon]:inline-flex",
             className,
           )}
-        />
+        >
+          Y
+        </span>
       </>
     ) : (
-      <img
-        src={variant === "full" ? fullLogo : iconLogo}
-        alt="FastAPI"
-        className={cn(variant === "full" ? "h-6 w-auto" : "size-5", className)}
-      />
+      <span
+        aria-hidden="true"
+        className={cn(
+          "inline-flex items-center gap-2 text-lg font-semibold tracking-tight",
+          className,
+        )}
+      >
+        <span className="logo-mark">Y</span>
+        {variant === "full" ? <span>Yeyu API</span> : null}
+      </span>
     )
 
   if (!asLink) {
     return content
   }
 
-  return <Link to="/">{content}</Link>
+  return (
+    <Link to="/" aria-label="Yeyu API 首页" className="inline-flex">
+      {content}
+    </Link>
+  )
 }
diff --git a/frontend/src/components/PublicSite/PublicFooter.tsx b/frontend/src/components/PublicSite/PublicFooter.tsx
new file mode 100644
index 0000000..192e8b8
--- /dev/null
+++ b/frontend/src/components/PublicSite/PublicFooter.tsx
@@ -0,0 +1,33 @@
+import { Link } from "@tanstack/react-router"
+
+export function PublicFooter() {
+  const currentYear = new Date().getFullYear()
+
+  return (
+    <footer className="public-footer">
+      <div className="public-container flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
+        <div>
+          <p className="font-semibold text-[var(--yeyu-ink)]">
+            Yeyu API 公益平台
+          </p>
+          <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
+            面向学生与个人开发者的公开工具目录 · {currentYear}
+          </p>
+        </div>
+        <nav aria-label="页脚导航" className="flex flex-wrap gap-4 text-sm">
+          <Link className="public-footer-link" to="/catalog">
+            API 目录
+          </Link>
+          <Link className="public-footer-link" to="/" hash="usage">
+            使用规范
+          </Link>
+          <Link className="public-footer-link" to="/login">
+            登录
+          </Link>
+        </nav>
+      </div>
+    </footer>
+  )
+}
+
+export default PublicFooter
diff --git a/frontend/src/components/PublicSite/PublicHeader.tsx b/frontend/src/components/PublicSite/PublicHeader.tsx
new file mode 100644
index 0000000..4a2d6d2
--- /dev/null
+++ b/frontend/src/components/PublicSite/PublicHeader.tsx
@@ -0,0 +1,86 @@
+import { Link } from "@tanstack/react-router"
+import { Menu, X } from "lucide-react"
+import { useState } from "react"
+
+import { Logo } from "@/components/Common/Logo"
+import { isLoggedIn } from "@/hooks/useAuth"
+
+interface NavigationLinksProps {
+  onNavigate?: () => void
+}
+
+function NavigationLinks({ onNavigate }: NavigationLinksProps) {
+  const linkClassName =
+    "public-nav-link rounded-md px-3 py-2 text-sm font-medium"
+
+  return (
+    <>
+      <Link to="/" className={linkClassName} onClick={onNavigate}>
+        首页
+      </Link>
+      <Link to="/catalog" className={linkClassName} onClick={onNavigate}>
+        API 目录
+      </Link>
+      <Link to="/" hash="usage" className={linkClassName} onClick={onNavigate}>
+        使用规范
+      </Link>
+      {isLoggedIn() ? (
+        <Link
+          to="/dashboard"
+          className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
+          onClick={onNavigate}
+        >
+          控制台
+        </Link>
+      ) : (
+        <Link
+          to="/login"
+          className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
+          onClick={onNavigate}
+        >
+          登录
+        </Link>
+      )}
+    </>
+  )
+}
+
+export function PublicHeader() {
+  const [menuOpen, setMenuOpen] = useState(true)
+  const toggleMenu = () => setMenuOpen((open) => !open)
+  const closeMenu = () => setMenuOpen(false)
+
+  return (
+    <header className="public-header">
+      <div className="public-container public-header-inner">
+        <Logo variant="full" className="h-8" />
+
+        <nav aria-label="公共导航" className="public-nav">
+          <div className="hidden items-center gap-1 md:flex">
+            <NavigationLinks />
+          </div>
+          <button
+            type="button"
+            className="public-menu-button md:hidden"
+            aria-controls="public-mobile-navigation"
+            aria-expanded={menuOpen}
+            aria-label={menuOpen ? "收起菜单" : "打开菜单"}
+            onClick={toggleMenu}
+          >
+            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
+          </button>
+          {menuOpen ? (
+            <div
+              id="public-mobile-navigation"
+              className="public-mobile-navigation md:hidden"
+            >
+              <NavigationLinks onNavigate={closeMenu} />
+            </div>
+          ) : null}
+        </nav>
+      </div>
+    </header>
+  )
+}
+
+export default PublicHeader
diff --git a/frontend/src/components/PublicSite/PublicLayout.tsx b/frontend/src/components/PublicSite/PublicLayout.tsx
new file mode 100644
index 0000000..7bb6666
--- /dev/null
+++ b/frontend/src/components/PublicSite/PublicLayout.tsx
@@ -0,0 +1,20 @@
+import type { ReactNode } from "react"
+
+import PublicFooter from "./PublicFooter"
+import PublicHeader from "./PublicHeader"
+
+interface PublicLayoutProps {
+  children: ReactNode
+}
+
+export function PublicLayout({ children }: PublicLayoutProps) {
+  return (
+    <div className="public-site flex min-h-svh flex-col">
+      <PublicHeader />
+      <main className="min-w-0 flex-1">{children}</main>
+      <PublicFooter />
+    </div>
+  )
+}
+
+export default PublicLayout
diff --git a/frontend/src/components/Sidebar/AppSidebar.tsx b/frontend/src/components/Sidebar/AppSidebar.tsx
index 8502bcb..0442aa0 100644
--- a/frontend/src/components/Sidebar/AppSidebar.tsx
+++ b/frontend/src/components/Sidebar/AppSidebar.tsx
@@ -6,21 +6,21 @@ import {
   Sidebar,
   SidebarContent,
   SidebarFooter,
   SidebarHeader,
 } from "@/components/ui/sidebar"
 import useAuth from "@/hooks/useAuth"
 import { type Item, Main } from "./Main"
 import { User } from "./User"
 
 const baseItems: Item[] = [
-  { icon: Home, title: "Dashboard", path: "/" },
+  { icon: Home, title: "Dashboard", path: "/dashboard" },
   { icon: Briefcase, title: "Items", path: "/items" },
 ]
 
 export function AppSidebar() {
   const { user: currentUser } = useAuth()
 
   const items = currentUser?.is_superuser
     ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
     : baseItems
 
diff --git a/frontend/src/hooks/useAuth.ts b/frontend/src/hooks/useAuth.ts
index 9c6cfc7..ba37f06 100644
--- a/frontend/src/hooks/useAuth.ts
+++ b/frontend/src/hooks/useAuth.ts
@@ -45,21 +45,21 @@ const useAuth = () => {
   const login = async (data: AccessToken) => {
     const response = await LoginService.loginAccessToken({
       body: data,
     })
     localStorage.setItem("access_token", response.data.access_token)
   }
 
   const loginMutation = useMutation({
     mutationFn: login,
     onSuccess: () => {
-      navigate({ to: "/" })
+      navigate({ to: "/dashboard" })
     },
     onError: handleError.bind(showErrorToast),
   })
 
   const logout = () => {
     void client
       .post({ url: "/api/v1/auth/logout", throwOnError: true })
       .finally(() => {
         localStorage.removeItem("access_token")
         localStorage.removeItem("session_authenticated")
diff --git a/frontend/src/index.css b/frontend/src/index.css
index 47e5696..eff80a1 100644
--- a/frontend/src/index.css
+++ b/frontend/src/index.css
@@ -36,38 +36,46 @@
   --color-sidebar-primary: var(--sidebar-primary);
   --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
   --color-sidebar-accent: var(--sidebar-accent);
   --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
   --color-sidebar-border: var(--sidebar-border);
   --color-sidebar-ring: var(--sidebar-ring);
 }
 
 :root {
   --radius: 0.625rem;
-  --background: oklch(1 0 0);
-  --foreground: oklch(0.145 0 0);
-  --card: oklch(1 0 0);
-  --card-foreground: oklch(0.145 0 0);
-  --popover: oklch(1 0 0);
-  --popover-foreground: oklch(0.145 0 0);
-  --primary: oklch(0.5982 0.10687 182.4689);
-  --primary-foreground: oklch(0.985 0 0);
-  --secondary: oklch(0.97 0 0);
-  --secondary-foreground: oklch(0.205 0 0);
-  --muted: oklch(0.97 0 0);
-  --muted-foreground: oklch(0.556 0 0);
-  --accent: oklch(0.97 0 0);
-  --accent-foreground: oklch(0.205 0 0);
-  --destructive: oklch(0.577 0.245 27.325);
-  --border: oklch(0.922 0 0);
-  --input: oklch(0.922 0 0);
-  --ring: oklch(0.708 0 0);
+  --yeyu-paper: #f4f3ee;
+  --yeyu-paper-strong: #fffdf8;
+  --yeyu-ink: #17211f;
+  --yeyu-muted: #53635f;
+  --yeyu-teal: #197c72;
+  --yeyu-mint: #ddede7;
+  --yeyu-amber: #b45309;
+  --yeyu-line: #cbd8d3;
+  --background: var(--yeyu-paper);
+  --foreground: var(--yeyu-ink);
+  --card: var(--yeyu-paper-strong);
+  --card-foreground: var(--yeyu-ink);
+  --popover: var(--yeyu-paper-strong);
+  --popover-foreground: var(--yeyu-ink);
+  --primary: var(--yeyu-teal);
+  --primary-foreground: #ffffff;
+  --secondary: var(--yeyu-mint);
+  --secondary-foreground: var(--yeyu-ink);
+  --muted: #e8eee9;
+  --muted-foreground: var(--yeyu-muted);
+  --accent: #e6f0ec;
+  --accent-foreground: var(--yeyu-ink);
+  --destructive: #b42318;
+  --border: var(--yeyu-line);
+  --input: var(--yeyu-line);
+  --ring: var(--yeyu-teal);
   --chart-1: oklch(0.646 0.222 41.116);
   --chart-2: oklch(0.6 0.118 184.704);
   --chart-3: oklch(0.398 0.07 227.392);
   --chart-4: oklch(0.828 0.189 84.429);
   --chart-5: oklch(0.769 0.188 70.08);
   --sidebar: oklch(0.985 0 0);
   --sidebar-foreground: oklch(0.145 0 0);
   --sidebar-primary: oklch(0.5982 0.10687 182.4689);
   --sidebar-primary-foreground: oklch(0.985 0 0);
   --sidebar-accent: oklch(0.97 0 0);
@@ -107,18 +115,1134 @@
   --sidebar-accent: oklch(0.269 0 0);
   --sidebar-accent-foreground: oklch(0.985 0 0);
   --sidebar-border: oklch(1 0 0 / 10%);
   --sidebar-ring: oklch(0.556 0 0);
 }
 
 @layer base {
   * {
     @apply border-border outline-ring/50;
   }
+
   body {
     @apply bg-background text-foreground;
+    min-width: 320px;
+    overflow-x: hidden;
+    font-family:
+      ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
+      "Microsoft YaHei", sans-serif;
   }
+
   button,
   [role="button"] {
     cursor: pointer;
   }
+
+  :where(a, button, input, select, textarea):focus-visible {
+    outline: 3px solid var(--yeyu-teal);
+    outline-offset: 3px;
+  }
+}
+
+.public-site {
+  --background: var(--yeyu-paper);
+  --foreground: var(--yeyu-ink);
+  --card: var(--yeyu-paper-strong);
+  --card-foreground: var(--yeyu-ink);
+  --popover: var(--yeyu-paper-strong);
+  --popover-foreground: var(--yeyu-ink);
+  --primary: var(--yeyu-teal);
+  --primary-foreground: #ffffff;
+  --secondary: var(--yeyu-mint);
+  --secondary-foreground: var(--yeyu-ink);
+  --muted: #e8eee9;
+  --muted-foreground: var(--yeyu-muted);
+  --accent: #e6f0ec;
+  --accent-foreground: var(--yeyu-ink);
+  --border: var(--yeyu-line);
+  --input: var(--yeyu-line);
+  --ring: var(--yeyu-teal);
+  background: var(--yeyu-paper);
+  color: var(--yeyu-ink);
+  color-scheme: light;
+}
+
+.public-container {
+  width: min(calc(100% - 2rem), 72rem);
+  margin-inline: auto;
+}
+
+.public-header {
+  position: relative;
+  z-index: 20;
+  border-bottom: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper);
+}
+
+.public-header-inner {
+  display: flex;
+  min-height: 4.5rem;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+}
+
+.public-nav {
+  position: relative;
+  margin-left: auto;
+}
+
+.public-nav-link {
+  color: var(--yeyu-muted);
+  text-decoration: none;
+  transition:
+    background-color 160ms ease,
+    color 160ms ease;
+}
+
+.public-nav-link:hover {
+  background: var(--yeyu-mint);
+  color: var(--yeyu-ink);
+}
+
+.public-nav-link-primary {
+  background: var(--yeyu-teal);
+  color: #ffffff;
+}
+
+.public-nav-link-primary:hover {
+  background: #12665e;
+  color: #ffffff;
+}
+
+.public-menu-button {
+  display: inline-flex;
+  height: 2.5rem;
+  width: 2.5rem;
+  align-items: center;
+  justify-content: center;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.375rem;
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-ink);
+}
+
+.public-mobile-navigation {
+  position: absolute;
+  top: calc(100% + 0.75rem);
+  right: 0;
+  z-index: 30;
+  min-width: 14rem;
+  gap: 0.25rem;
+  padding: 0.5rem;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.5rem;
+  background: var(--yeyu-paper-strong);
+  box-shadow: 0 12px 30px rgb(23 33 31 / 12%);
+}
+
+.public-mobile-navigation > * {
+  display: block;
+  width: 100%;
+}
+
+.public-hero {
+  display: grid;
+  gap: 2rem;
+  padding-block: clamp(3.5rem, 9vw, 7rem);
+}
+
+.public-hero-copy {
+  max-width: 48rem;
+}
+
+.public-eyebrow {
+  margin: 0;
+  color: var(--yeyu-teal);
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  font-size: 0.75rem;
+  font-weight: 700;
+  letter-spacing: 0.16em;
+  line-height: 1.5;
+  text-transform: uppercase;
+}
+
+.public-hero-title {
+  max-width: 13ch;
+  margin-top: 1rem;
+  color: var(--yeyu-ink);
+  font-size: clamp(2.5rem, 7vw, 5.5rem);
+  font-weight: 700;
+  letter-spacing: -0.055em;
+  line-height: 0.98;
+}
+
+.public-hero-lede {
+  max-width: 42rem;
+  margin-top: 1.5rem;
+  color: var(--yeyu-muted);
+  font-size: clamp(1rem, 2vw, 1.2rem);
+  line-height: 1.8;
+}
+
+.public-search-form {
+  display: flex;
+  max-width: 44rem;
+  flex-wrap: wrap;
+  gap: 0.75rem;
+  margin-top: 2rem;
+}
+
+.public-search-input {
+  min-width: 0;
+  flex: 1 1 16rem;
+  height: 3rem;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.375rem;
+  background: var(--yeyu-paper-strong);
+  padding-inline: 1rem;
+  color: var(--yeyu-ink);
+}
+
+.public-search-input::placeholder {
+  color: var(--yeyu-muted);
+  opacity: 0.8;
+}
+
+.public-primary-button {
+  display: inline-flex;
+  min-height: 3rem;
+  align-items: center;
+  justify-content: center;
+  gap: 0.5rem;
+  border: 0;
+  border-radius: 0.375rem;
+  background: var(--yeyu-teal);
+  padding: 0.75rem 1.1rem;
+  color: #ffffff;
+  font-size: 0.9rem;
+  font-weight: 700;
+  text-decoration: none;
+  transition:
+    background-color 160ms ease,
+    transform 160ms ease;
+}
+
+.public-primary-button:hover {
+  background: #12665e;
+  transform: translateY(-1px);
+}
+
+.public-hero-links {
+  display: flex;
+  flex-wrap: wrap;
+  gap: 1.25rem;
+  margin-top: 1.25rem;
+}
+
+.public-text-link,
+.public-footer-link {
+  color: var(--yeyu-teal);
+  font-size: 0.9rem;
+  font-weight: 700;
+  text-underline-offset: 0.25rem;
+}
+
+.public-text-link:hover,
+.public-footer-link:hover {
+  text-decoration: underline;
+}
+
+.public-boundary-note {
+  align-self: end;
+  max-width: 28rem;
+  padding: 1.5rem;
+  border-left: 4px solid var(--yeyu-amber);
+  background: var(--yeyu-mint);
+}
+
+.public-note-title {
+  margin-top: 0.75rem;
+  color: var(--yeyu-ink);
+  font-size: 1.5rem;
+  font-weight: 700;
+  letter-spacing: -0.02em;
+}
+
+.public-note-copy,
+.public-section-copy {
+  margin-top: 0.75rem;
+  color: var(--yeyu-muted);
+  line-height: 1.75;
+}
+
+.public-note-rule {
+  height: 1px;
+  margin-block: 1.25rem;
+  background: var(--yeyu-line);
+}
+
+.public-note-label {
+  color: var(--yeyu-muted);
+  font-size: 0.75rem;
+  font-weight: 700;
+  letter-spacing: 0.12em;
+  text-transform: uppercase;
+}
+
+.public-code-chip,
+.public-path-line,
+.public-path-line code {
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+}
+
+.public-code-chip {
+  display: inline-block;
+  margin-top: 0.5rem;
+  padding: 0.35rem 0.5rem;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.25rem;
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-ink);
+  font-size: 0.85rem;
+}
+
+.public-section {
+  padding-block: clamp(3rem, 7vw, 5.5rem);
+  border-top: 1px solid var(--yeyu-line);
+}
+
+.public-section-heading {
+  display: flex;
+  align-items: end;
+  justify-content: space-between;
+  gap: 1.5rem;
+}
+
+.public-section-title {
+  margin-top: 0.75rem;
+  color: var(--yeyu-ink);
+  font-size: clamp(1.75rem, 4vw, 3rem);
+  font-weight: 700;
+  letter-spacing: -0.04em;
+  line-height: 1.05;
+}
+
+.public-catalog-list {
+  display: grid;
+  gap: 0.75rem;
+  margin-top: 2rem;
+  padding: 0;
+  list-style: none;
+}
+
+.public-catalog-row {
+  display: grid;
+  grid-template-columns: minmax(12rem, 0.8fr) minmax(0, 1.6fr) auto;
+  gap: 1rem;
+  align-items: center;
+  padding: 1rem;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.375rem;
+  background: var(--yeyu-paper-strong);
+}
+
+.public-path-line {
+  display: flex;
+  min-width: 0;
+  align-items: center;
+  gap: 0.65rem;
+  color: var(--yeyu-ink);
+  font-size: 0.85rem;
+  overflow-x: auto;
+  white-space: nowrap;
+}
+
+.public-method-badge {
+  flex: 0 0 auto;
+  color: var(--yeyu-teal);
+  font-size: 0.72rem;
+  font-weight: 800;
+  letter-spacing: 0.08em;
+}
+
+.public-catalog-meta {
+  display: flex;
+  flex-wrap: wrap;
+  justify-content: flex-end;
+  gap: 0.5rem 0.75rem;
+  color: var(--yeyu-muted);
+  font-size: 0.78rem;
+  text-align: right;
+}
+
+.public-state {
+  margin-top: 2rem;
+  padding: 1.25rem;
+  border: 1px dashed var(--yeyu-line);
+  border-radius: 0.375rem;
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-muted);
+  line-height: 1.7;
+}
+
+.public-state-error {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+  border-color: var(--yeyu-amber);
+}
+
+.public-inline-button {
+  flex: 0 0 auto;
+  color: var(--yeyu-teal);
+  font-weight: 700;
+  text-decoration: underline;
+  text-underline-offset: 0.25rem;
+}
+
+.public-usage-section {
+  display: grid;
+  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
+  gap: 2rem;
+}
+
+.public-usage-grid {
+  display: grid;
+  gap: 1rem;
+  color: var(--yeyu-muted);
+  line-height: 1.75;
+}
+
+.public-usage-grid p {
+  padding-left: 1rem;
+  border-left: 2px solid var(--yeyu-teal);
+}
+
+.public-bottom-cta {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+  padding-block: 2rem 4rem;
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.public-footer {
+  border-top: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+}
+
+.public-footer-link {
+  color: var(--yeyu-muted);
+  font-weight: 600;
+}
+
+.logo-mark {
+  display: inline-flex;
+  height: 1.75rem;
+  width: 1.75rem;
+  align-items: center;
+  justify-content: center;
+  border-radius: 0.25rem;
+  background: var(--yeyu-teal);
+  color: #ffffff;
+  font-size: 0.85em;
+  font-weight: 800;
+}
+
+.public-catalog-title-link {
+  color: inherit;
+  text-decoration: none;
+  text-underline-offset: 0.2rem;
+}
+
+.public-catalog-title-link:hover {
+  color: var(--yeyu-teal);
+  text-decoration: underline;
+}
+
+.catalog-page-shell,
+.catalog-detail-shell {
+  padding-block: clamp(3rem, 7vw, 6rem);
+}
+
+.catalog-page-header {
+  max-width: 48rem;
+  padding-bottom: 2.5rem;
+}
+
+.catalog-page-title {
+  margin-top: 0.85rem;
+  color: var(--yeyu-ink);
+  font-size: clamp(2.75rem, 7vw, 5.25rem);
+  font-weight: 700;
+  letter-spacing: -0.06em;
+  line-height: 0.98;
+}
+
+.catalog-page-lede {
+  max-width: 42rem;
+  margin-top: 1.25rem;
+  color: var(--yeyu-muted);
+  font-size: 1.05rem;
+  line-height: 1.8;
+}
+
+.catalog-search-panel,
+.catalog-filters {
+  display: grid;
+  gap: 1.25rem;
+  padding: 1.25rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+}
+
+.catalog-search-panel {
+  margin-top: 0.5rem;
+}
+
+.catalog-search-heading,
+.catalog-results-heading {
+  display: flex;
+  align-items: end;
+  justify-content: space-between;
+  gap: 1rem;
+}
+
+.catalog-search-title,
+.catalog-filter-title,
+.catalog-results-title {
+  margin-top: 0.45rem;
+  color: var(--yeyu-ink);
+  font-size: 1.25rem;
+  font-weight: 700;
+  letter-spacing: -0.025em;
+}
+
+.catalog-search-hint,
+.catalog-results-count,
+.catalog-refreshing {
+  color: var(--yeyu-muted);
+  font-size: 0.8rem;
+}
+
+.catalog-search-control {
+  display: flex;
+  min-width: 0;
+  align-items: center;
+  gap: 0.7rem;
+  min-height: 3.25rem;
+  padding-inline: 1rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper);
+}
+
+.catalog-search-icon {
+  flex: 0 0 auto;
+  color: var(--yeyu-teal);
+}
+
+.catalog-search-input {
+  min-width: 0;
+  flex: 1;
+  border: 0;
+  outline: 0;
+  background: transparent;
+  color: var(--yeyu-ink);
+}
+
+.catalog-search-input::placeholder {
+  color: var(--yeyu-muted);
+}
+
+.catalog-search-clear {
+  display: inline-flex;
+  height: 2rem;
+  width: 2rem;
+  flex: 0 0 auto;
+  align-items: center;
+  justify-content: center;
+  border: 1px solid var(--yeyu-line);
+  color: var(--yeyu-muted);
+}
+
+.catalog-search-clear svg {
+  height: 1rem;
+  width: 1rem;
+}
+
+.catalog-filters {
+  grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr);
+  margin-top: 1rem;
+  background: var(--yeyu-mint);
+}
+
+.catalog-filter-controls {
+  display: grid;
+  grid-template-columns: repeat(2, minmax(0, 1fr));
+  gap: 0.75rem;
+}
+
+.catalog-filter-field {
+  display: grid;
+  gap: 0.35rem;
+}
+
+.catalog-filter-field label {
+  color: var(--yeyu-muted);
+  font-size: 0.78rem;
+  font-weight: 700;
+}
+
+.catalog-filter-field select {
+  min-height: 2.75rem;
+  min-width: 0;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.25rem;
+  background: var(--yeyu-paper-strong);
+  padding-inline: 0.75rem;
+  color: var(--yeyu-ink);
+}
+
+.catalog-results {
+  margin-top: clamp(3rem, 6vw, 5rem);
+  padding-top: 2rem;
+  border-top: 1px solid var(--yeyu-line);
+}
+
+.catalog-refreshing {
+  margin-top: 1rem;
+}
+
+.catalog-grid {
+  display: grid;
+  grid-template-columns: repeat(2, minmax(0, 1fr));
+  gap: 1rem;
+  margin-top: 1.25rem;
+}
+
+.catalog-pagination {
+  display: flex;
+  align-items: center;
+  justify-content: center;
+  gap: 1rem;
+  margin-top: 1.5rem;
+  color: var(--yeyu-muted);
+  font-size: 0.85rem;
+}
+
+.catalog-pagination button:disabled {
+  cursor: not-allowed;
+  opacity: 0.45;
+}
+
+.catalog-card {
+  display: grid;
+  min-width: 0;
+  gap: 1.1rem;
+  padding: 1.25rem;
+  border: 1px solid var(--yeyu-line);
+  border-top: 3px solid var(--yeyu-teal);
+  background: var(--yeyu-paper-strong);
+  transition:
+    border-color 160ms ease,
+    box-shadow 160ms ease,
+    transform 160ms ease;
+}
+
+.catalog-card:hover {
+  border-color: var(--yeyu-teal);
+  box-shadow: 0 10px 24px rgb(23 33 31 / 8%);
+  transform: translateY(-2px);
+}
+
+.catalog-card-path,
+.api-detail-path-row {
+  display: flex;
+  min-width: 0;
+  align-items: center;
+  gap: 0.65rem;
+  overflow-x: auto;
+  color: var(--yeyu-ink);
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  font-size: 0.85rem;
+  white-space: nowrap;
+}
+
+.catalog-card-path code,
+.api-detail-path-row code {
+  overflow: visible;
+}
+
+.catalog-method-badge {
+  flex: 0 0 auto;
+  color: var(--yeyu-teal);
+  font-size: 0.72rem;
+  font-weight: 800;
+  letter-spacing: 0.08em;
+}
+
+.catalog-card-content {
+  min-width: 0;
+}
+
+.catalog-card-title {
+  display: inline-block;
+  max-width: 100%;
+  overflow: hidden;
+  color: var(--yeyu-ink);
+  font-size: 1.2rem;
+  font-weight: 700;
+  text-overflow: ellipsis;
+  text-decoration: none;
+  white-space: nowrap;
+}
+
+.catalog-card-title:hover {
+  color: var(--yeyu-teal);
+  text-decoration: underline;
+  text-underline-offset: 0.2rem;
+}
+
+.catalog-card-summary {
+  margin-top: 0.5rem;
+  color: var(--yeyu-muted);
+  line-height: 1.65;
+}
+
+.catalog-card-meta,
+.api-detail-tags {
+  display: flex;
+  flex-wrap: wrap;
+  align-items: center;
+  gap: 0.45rem 0.6rem;
+  color: var(--yeyu-muted);
+  font-size: 0.76rem;
+}
+
+.catalog-tag {
+  display: inline-flex;
+  align-items: center;
+  min-height: 1.65rem;
+  padding-inline: 0.5rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper);
+  color: var(--yeyu-muted);
+  font-size: 0.72rem;
+  font-weight: 700;
+}
+
+.catalog-tag-free {
+  border-color: var(--yeyu-teal);
+  color: var(--yeyu-teal);
+}
+
+.catalog-tag-status {
+  border-color: rgb(180 83 9 / 38%);
+  color: var(--yeyu-amber);
+}
+
+.catalog-state {
+  display: grid;
+  gap: 0.35rem;
+  margin-top: 1.25rem;
+  padding: 1.25rem;
+  border: 1px dashed var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-muted);
+  line-height: 1.65;
+}
+
+.catalog-state-error {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+  border-color: var(--yeyu-amber);
+}
+
+.catalog-state-kicker {
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.catalog-skeleton-list {
+  min-height: 12rem;
+  align-content: center;
+}
+
+.catalog-skeleton-line {
+  display: block;
+  width: 68%;
+  height: 0.8rem;
+  background: var(--yeyu-mint);
+}
+
+.catalog-skeleton-line-wide {
+  width: 92%;
+  height: 1.4rem;
+}
+
+.catalog-skeleton-line-short {
+  width: 42%;
+}
+
+.catalog-detail-shell {
+  max-width: 86rem;
+}
+
+.api-detail-page {
+  min-width: 0;
+}
+
+.api-detail-breadcrumbs {
+  display: flex;
+  flex-wrap: wrap;
+  align-items: center;
+  gap: 0.65rem;
+  color: var(--yeyu-muted);
+  font-size: 0.82rem;
+}
+
+.api-detail-header {
+  max-width: 58rem;
+  padding-block: 2.25rem 3rem;
+}
+
+.api-detail-title {
+  margin-top: 1rem;
+  color: var(--yeyu-ink);
+  font-size: clamp(2.35rem, 6vw, 4.75rem);
+  font-weight: 700;
+  letter-spacing: -0.055em;
+  line-height: 1;
+}
+
+.api-detail-summary {
+  max-width: 48rem;
+  margin-top: 1rem;
+  color: var(--yeyu-muted);
+  font-size: 1.05rem;
+  line-height: 1.8;
+}
+
+.api-detail-tags {
+  margin-top: 1.25rem;
+}
+
+.api-detail-layout {
+  display: grid;
+  grid-template-columns: minmax(0, 1fr) minmax(15rem, 20rem);
+  gap: clamp(2rem, 6vw, 5rem);
+  align-items: start;
+}
+
+.api-detail-main {
+  min-width: 0;
+}
+
+.api-detail-section {
+  min-width: 0;
+  padding-block: 2.25rem;
+  border-top: 1px solid var(--yeyu-line);
+}
+
+.api-detail-section-title {
+  margin-top: 0.55rem;
+  color: var(--yeyu-ink);
+  font-size: 1.5rem;
+  font-weight: 700;
+  letter-spacing: -0.03em;
+}
+
+.api-detail-copy {
+  max-width: 52rem;
+  margin-top: 0.85rem;
+  color: var(--yeyu-muted);
+  line-height: 1.75;
+}
+
+.api-auth-callout {
+  display: flex;
+  flex-wrap: wrap;
+  align-items: center;
+  justify-content: space-between;
+  gap: 0.75rem;
+  margin-top: 1.25rem;
+  padding: 0.85rem 1rem;
+  border-left: 3px solid var(--yeyu-amber);
+  background: var(--yeyu-mint);
+  color: var(--yeyu-muted);
+  font-size: 0.82rem;
+}
+
+.api-auth-callout code {
+  overflow-x: auto;
+  color: var(--yeyu-ink);
+  white-space: nowrap;
+}
+
+.api-table-scroll {
+  max-width: 100%;
+  margin-top: 1.25rem;
+  overflow-x: auto;
+  border: 1px solid var(--yeyu-line);
+}
+
+.api-detail-table {
+  width: 100%;
+  min-width: 38rem;
+  border-collapse: collapse;
+  color: var(--yeyu-muted);
+  font-size: 0.86rem;
+  text-align: left;
+}
+
+.api-detail-table th,
+.api-detail-table td {
+  padding: 0.85rem 1rem;
+  border-bottom: 1px solid var(--yeyu-line);
+  vertical-align: top;
+}
+
+.api-detail-table thead th {
+  background: var(--yeyu-mint);
+  color: var(--yeyu-ink);
+  font-size: 0.75rem;
+  font-weight: 800;
+  letter-spacing: 0.05em;
+}
+
+.api-detail-table tbody th {
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.api-detail-table tr:last-child th,
+.api-detail-table tr:last-child td {
+  border-bottom: 0;
+}
+
+.api-table-note {
+  display: block;
+  max-width: 28rem;
+  margin-top: 0.35rem;
+  line-height: 1.55;
+}
+
+.api-detail-muted {
+  margin-top: 1rem;
+  color: var(--yeyu-muted);
+}
+
+.api-response-fields {
+  display: grid;
+  grid-template-columns: repeat(2, minmax(0, 1fr));
+  gap: 0.5rem;
+  margin-top: 1.25rem;
+}
+
+.api-response-field {
+  display: flex;
+  min-width: 0;
+  flex-wrap: wrap;
+  gap: 0.5rem;
+  align-items: center;
+  justify-content: space-between;
+  padding: 0.7rem 0.8rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-muted);
+  font-size: 0.8rem;
+}
+
+.api-response-field code {
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.api-json-block,
+.code-example-block {
+  max-width: 100%;
+  margin-top: 1rem;
+  overflow-x: auto;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-ink);
+  padding: 1rem;
+  color: #eaf5f0;
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  font-size: 0.78rem;
+  line-height: 1.7;
+  white-space: pre;
+}
+
+.api-detail-aside {
+  display: grid;
+  gap: 1rem;
+  position: sticky;
+  top: 1.5rem;
+}
+
+.api-aside-card {
+  padding: 1.25rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+}
+
+.api-aside-title {
+  margin-top: 0.55rem;
+  color: var(--yeyu-ink);
+  font-size: 1.1rem;
+  font-weight: 700;
+}
+
+.api-aside-value {
+  margin-top: 0.85rem;
+  color: var(--yeyu-teal);
+  font-weight: 700;
+}
+
+.api-cache-list {
+  display: grid;
+  gap: 0.75rem;
+  margin-top: 1rem;
+}
+
+.api-cache-list > div {
+  display: flex;
+  justify-content: space-between;
+  gap: 0.75rem;
+  padding-top: 0.75rem;
+  border-top: 1px solid var(--yeyu-line);
+  color: var(--yeyu-muted);
+  font-size: 0.8rem;
+}
+
+.api-cache-list dt {
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.api-cache-list dd {
+  max-width: 9rem;
+  overflow-wrap: anywhere;
+  text-align: right;
+}
+
+.api-code-grid {
+  display: grid;
+  gap: 1rem;
+  margin-top: 1.25rem;
+}
+
+.code-example {
+  min-width: 0;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+}
+
+.code-example-header {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+  padding: 0.75rem 1rem;
+  border-bottom: 1px solid var(--yeyu-line);
+}
+
+.code-example-header h3 {
+  color: var(--yeyu-ink);
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  font-size: 0.82rem;
+  font-weight: 800;
+}
+
+.code-copy-button {
+  display: inline-flex;
+  min-height: 2.25rem;
+  align-items: center;
+  gap: 0.4rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper);
+  padding: 0.4rem 0.65rem;
+  color: var(--yeyu-teal);
+  font-size: 0.78rem;
+  font-weight: 700;
+}
+
+.code-copy-button svg {
+  height: 0.9rem;
+  width: 0.9rem;
+}
+
+.code-example-block {
+  margin-top: 0;
+  border: 0;
+}
+
+.code-example-feedback {
+  min-height: 1.5rem;
+  padding: 0 1rem 0.65rem;
+  color: var(--yeyu-teal);
+  font-size: 0.75rem;
+}
+
+@media (min-width: 768px) {
+  .public-hero {
+    grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.65fr);
+    align-items: end;
+  }
+}
+
+@media (max-width: 767px) {
+  .public-section-heading,
+  .catalog-search-heading,
+  .catalog-results-heading,
+  .public-bottom-cta {
+    align-items: flex-start;
+    flex-direction: column;
+  }
+
+  .public-catalog-row,
+  .public-usage-section,
+  .catalog-filters,
+  .catalog-filter-controls,
+  .api-detail-layout {
+    grid-template-columns: 1fr;
+  }
+
+  .catalog-grid,
+  .api-response-fields {
+    grid-template-columns: 1fr;
+  }
+
+  .catalog-search-hint {
+    margin-top: -0.5rem;
+  }
+
+  .public-catalog-meta {
+    justify-content: flex-start;
+    text-align: left;
+  }
+
+  .api-detail-aside {
+    position: static;
+  }
+
+  .api-auth-callout {
+    align-items: flex-start;
+    flex-direction: column;
+  }
+}
+
+@media (prefers-reduced-motion: reduce) {
+  *,
+  *::before,
+  *::after {
+    scroll-behavior: auto;
+    transition: none;
+    animation: none;
+  }
 }
diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
index 7bafdf7..9d9f7c3 100644
--- a/frontend/src/routes/_layout.tsx
+++ b/frontend/src/routes/_layout.tsx
@@ -19,22 +19,25 @@ export const Route = createFileRoute("/_layout")({
     }
   },
 })
 
 function Layout() {
   return (
     <SidebarProvider>
       <AppSidebar />
       <SidebarInset>
         <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
-          <SidebarTrigger className="-ml-1 text-muted-foreground" />
+          <SidebarTrigger
+            className="-ml-1 text-muted-foreground"
+            aria-label="切换侧边栏"
+          />
         </header>
-        <main className="flex-1 p-6 md:p-8">
+        <main id="main-content" className="flex-1 p-6 md:p-8">
           <div className="mx-auto max-w-7xl">
             <Outlet />
           </div>
         </main>
         <Footer />
       </SidebarInset>
     </SidebarProvider>
   )
 }
diff --git a/frontend/src/routes/_layout/dashboard.tsx b/frontend/src/routes/_layout/dashboard.tsx
new file mode 100644
index 0000000..436dd2b
--- /dev/null
+++ b/frontend/src/routes/_layout/dashboard.tsx
@@ -0,0 +1,34 @@
+import { createFileRoute } from "@tanstack/react-router"
+
+import useAuth from "@/hooks/useAuth"
+
+export const Route = createFileRoute("/_layout/dashboard")({
+  component: Dashboard,
+  head: () => ({
+    meta: [
+      {
+        title: "Yeyu API 控制台",
+      },
+    ],
+  }),
+})
+
+function Dashboard() {
+  const { user: currentUser } = useAuth()
+  const displayName = currentUser?.full_name || currentUser?.email || "开发者"
+
+  return (
+    <section className="flex flex-col gap-3" data-testid="dashboard-page">
+      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
+        Yeyu API / 控制台
+      </p>
+      <h1 className="max-w-2xl truncate text-3xl font-semibold tracking-tight">
+        Yeyu API 控制台
+      </h1>
+      <p className="text-lg text-muted-foreground">你好，{displayName}。</p>
+      <p className="max-w-2xl text-muted-foreground">
+        在这里管理你的账户、API Key 和调用设置。公共目录仍然可以从站点首页查看。
+      </p>
+    </section>
+  )
+}
diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
deleted file mode 100644
index 3e640cb..0000000
--- a/frontend/src/routes/_layout/index.tsx
+++ /dev/null
@@ -1,31 +0,0 @@
-import { createFileRoute } from "@tanstack/react-router"
-
-import useAuth from "@/hooks/useAuth"
-
-export const Route = createFileRoute("/_layout/")({
-  component: Dashboard,
-  head: () => ({
-    meta: [
-      {
-        title: "Dashboard - FastAPI Template",
-      },
-    ],
-  }),
-})
-
-function Dashboard() {
-  const { user: currentUser } = useAuth()
-
-  return (
-    <div>
-      <div>
-        <h1 className="text-2xl truncate max-w-sm">
-          Hi, {currentUser?.full_name || currentUser?.email} 👋
-        </h1>
-        <p className="text-muted-foreground">
-          Welcome back, nice to see you again!!!
-        </p>
-      </div>
-    </div>
-  )
-}
diff --git a/frontend/src/routes/catalog/$slug.tsx b/frontend/src/routes/catalog/$slug.tsx
new file mode 100644
index 0000000..30c0fa2
--- /dev/null
+++ b/frontend/src/routes/catalog/$slug.tsx
@@ -0,0 +1,48 @@
+import { useQuery } from "@tanstack/react-query"
+import { createFileRoute } from "@tanstack/react-router"
+
+import { CatalogService } from "@/client"
+import ApiDetailView from "@/components/ApiCatalog/ApiDetailView"
+import {
+  CatalogDetailErrorState,
+  CatalogLoadingState,
+} from "@/components/ApiCatalog/CatalogStates"
+import PublicLayout from "@/components/PublicSite/PublicLayout"
+
+export const Route = createFileRoute("/catalog/$slug")({
+  component: CatalogDetailRoute,
+  head: () => ({
+    meta: [
+      {
+        title: "API 详情 - Yeyu API",
+      },
+    ],
+  }),
+})
+
+function CatalogDetailRoute() {
+  const { slug } = Route.useParams()
+  const detailQuery = useQuery({
+    queryKey: ["public-catalog-detail", slug],
+    queryFn: async () => {
+      const response = await CatalogService.getCatalogDetail({
+        path: { slug },
+      })
+      return response.data
+    },
+  })
+
+  return (
+    <PublicLayout>
+      <div className="public-container catalog-detail-shell">
+        {detailQuery.isPending ? (
+          <CatalogLoadingState />
+        ) : detailQuery.isError ? (
+          <CatalogDetailErrorState onRetry={() => void detailQuery.refetch()} />
+        ) : detailQuery.data ? (
+          <ApiDetailView detail={detailQuery.data} />
+        ) : null}
+      </div>
+    </PublicLayout>
+  )
+}
diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
new file mode 100644
index 0000000..fa2b395
--- /dev/null
+++ b/frontend/src/routes/catalog/index.tsx
@@ -0,0 +1,223 @@
+import { useQuery } from "@tanstack/react-query"
+import { createFileRoute } from "@tanstack/react-router"
+import { useEffect, useState } from "react"
+
+import { type CatalogItem, type CatalogPage, CatalogService } from "@/client"
+import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
+import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
+import CatalogPagination from "@/components/ApiCatalog/CatalogPagination"
+import CatalogSearch from "@/components/ApiCatalog/CatalogSearch"
+import {
+  CatalogEmptyState,
+  CatalogErrorState,
+  CatalogLoadingState,
+} from "@/components/ApiCatalog/CatalogStates"
+import {
+  type CatalogFacetResult,
+  type CatalogSearchParams,
+  normalizeSearchValue,
+  parseCatalogSearch,
+} from "@/components/ApiCatalog/catalog-types"
+import PublicLayout from "@/components/PublicSite/PublicLayout"
+
+const FACET_PAGE_SIZE = 100
+const MAX_FACET_PAGES = 100
+
+async function fetchCatalogFacetItems(): Promise<CatalogFacetResult> {
+  const items: CatalogItem[] = []
+
+  for (let page = 1; page <= MAX_FACET_PAGES; page += 1) {
+    const response = await CatalogService.searchCatalog({
+      query: {
+        page,
+        page_size: FACET_PAGE_SIZE,
+      },
+    })
+    const catalogPage = response.data
+    items.push(...catalogPage.data)
+
+    if (items.length >= catalogPage.count || catalogPage.data.length === 0) {
+      return { items, complete: true }
+    }
+  }
+
+  return { items: [], complete: false, reason: "page-limit" }
+}
+
+export const Route = createFileRoute("/catalog/")({
+  validateSearch: (search): CatalogSearchParams => parseCatalogSearch(search),
+  component: CatalogRoutePage,
+  head: () => ({
+    meta: [
+      {
+        title: "API 目录 - Yeyu API",
+      },
+    ],
+  }),
+})
+
+function CatalogRoutePage() {
+  const search = Route.useSearch()
+  const navigate = Route.useNavigate()
+  const [draftQuery, setDraftQuery] = useState(search.query ?? "")
+
+  useEffect(() => {
+    setDraftQuery(search.query ?? "")
+  }, [search.query])
+
+  useEffect(() => {
+    const normalizedQuery = normalizeSearchValue(draftQuery)
+    if (normalizedQuery === search.query) return
+
+    const timeoutId = window.setTimeout(() => {
+      void navigate({
+        search: (previous) => ({
+          ...previous,
+          query: normalizedQuery,
+          page: 1,
+        }),
+        replace: true,
+      })
+    }, 400)
+
+    return () => window.clearTimeout(timeoutId)
+  }, [draftQuery, navigate, search.query])
+
+  const catalogQuery = useQuery<CatalogPage>({
+    queryKey: [
+      "public-catalog",
+      search.query ?? "",
+      search.category ?? "",
+      search.status ?? "",
+      search.page,
+    ],
+    queryFn: async () => {
+      const response = await CatalogService.searchCatalog({
+        query: {
+          query: search.query,
+          category: search.category,
+          status: search.status,
+          page: search.page,
+          page_size: 20,
+        },
+      })
+      return response.data
+    },
+  })
+
+  const catalogFacetQuery = useQuery<CatalogFacetResult>({
+    queryKey: ["public-catalog-facets"],
+    queryFn: fetchCatalogFacetItems,
+    staleTime: 60_000,
+  })
+
+  const items = catalogQuery.data?.data ?? []
+  const filterItems = catalogFacetQuery.data
+    ? catalogFacetQuery.data.complete
+      ? catalogFacetQuery.data.items
+      : []
+    : items
+  const updateFilter = (key: "category" | "status", value: string) => {
+    void navigate({
+      search: (previous) => ({
+        ...previous,
+        [key]: normalizeSearchValue(value),
+        page: 1,
+      }),
+      replace: true,
+    })
+  }
+
+  return (
+    <PublicLayout>
+      <div className="public-container catalog-page-shell">
+        <header className="catalog-page-header">
+          <p className="public-eyebrow">公开目录 / REAL DATA</p>
+          <h1 className="catalog-page-title">API 目录</h1>
+          <p className="catalog-page-lede">
+            只展示后端公开、健康或已发布的真实接口。先搜索，再阅读完整调用契约。
+          </p>
+        </header>
+
+        <CatalogSearch value={draftQuery} onChange={setDraftQuery} />
+        <CatalogFilters
+          items={filterItems}
+          category={search.category}
+          status={search.status}
+          onCategoryChange={(value) => updateFilter("category", value)}
+          onStatusChange={(value) => updateFilter("status", value)}
+        />
+        {catalogFacetQuery.data && !catalogFacetQuery.data.complete ? (
+          <p
+            className="catalog-facets-incomplete"
+            data-testid="catalog-facets-incomplete"
+            role="status"
+          >
+            筛选选项未完整加载，已隐藏未确认的部分结果。
+          </p>
+        ) : null}
+        {catalogFacetQuery.isError && !catalogQuery.isError ? (
+          <CatalogErrorState onRetry={() => void catalogFacetQuery.refetch()} />
+        ) : null}
+
+        <section
+          className="catalog-results"
+          aria-labelledby="catalog-results-heading"
+        >
+          <div className="catalog-results-heading">
+            <div>
+              <p className="public-eyebrow">RESULTS</p>
+              <h2
+                id="catalog-results-heading"
+                className="catalog-results-title"
+              >
+                可用接口
+              </h2>
+            </div>
+            {catalogQuery.data ? (
+              <p className="catalog-results-count">
+                共 {catalogQuery.data.count} 条
+              </p>
+            ) : null}
+          </div>
+
+          {catalogQuery.isFetching && !catalogQuery.isPending ? (
+            <p className="catalog-refreshing" role="status">
+              正在更新目录……
+            </p>
+          ) : null}
+          {catalogQuery.isPending ? <CatalogLoadingState /> : null}
+          {catalogQuery.isError ? (
+            <CatalogErrorState onRetry={() => void catalogQuery.refetch()} />
+          ) : null}
+          {!catalogQuery.isPending &&
+          !catalogQuery.isError &&
+          items.length === 0 ? (
+            <CatalogEmptyState />
+          ) : null}
+          {!catalogQuery.isPending &&
+          !catalogQuery.isError &&
+          items.length > 0 ? (
+            <CatalogGrid items={items} />
+          ) : null}
+          {!catalogQuery.isPending &&
+          !catalogQuery.isError &&
+          catalogQuery.data ? (
+            <CatalogPagination
+              count={catalogQuery.data.count}
+              page={search.page}
+              pageSize={catalogQuery.data.page_size}
+              isFetching={catalogQuery.isFetching}
+              onPageChange={(page) =>
+                void navigate({
+                  search: (previous) => ({ ...previous, page }),
+                  replace: true,
+                })
+              }
+            />
+          ) : null}
+        </section>
+      </div>
+    </PublicLayout>
+  )
+}
diff --git a/frontend/src/routes/index.tsx b/frontend/src/routes/index.tsx
new file mode 100644
index 0000000..2067555
--- /dev/null
+++ b/frontend/src/routes/index.tsx
@@ -0,0 +1,210 @@
+import { useQuery } from "@tanstack/react-query"
+import { createFileRoute, Link } from "@tanstack/react-router"
+
+import { CatalogService } from "@/client"
+import { formatUpdatedAt } from "@/components/ApiCatalog/catalog-types"
+import PublicLayout from "@/components/PublicSite/PublicLayout"
+
+export const Route = createFileRoute("/")({
+  component: PublicHome,
+  head: () => ({
+    meta: [
+      {
+        title: "Yeyu API 公益工具箱",
+      },
+    ],
+  }),
+})
+
+function CatalogPreview() {
+  const catalogQuery = useQuery({
+    queryKey: ["public-catalog-preview"],
+    queryFn: async () => {
+      const response = await CatalogService.searchCatalog({
+        query: {
+          page: 1,
+          page_size: 4,
+        },
+      })
+      return response.data
+    },
+  })
+
+  const items = catalogQuery.data?.data ?? []
+
+  return (
+    <section
+      id="catalog"
+      className="public-section public-catalog-section"
+      aria-labelledby="catalog-heading"
+    >
+      <div className="public-section-heading">
+        <div>
+          <p className="public-eyebrow">目录入口</p>
+          <h2 id="catalog-heading" className="public-section-title">
+            从真实目录开始
+          </h2>
+          <p className="public-section-copy">
+            这里展示后端公开目录中的接口，不展示虚构卡片或调用统计。
+          </p>
+        </div>
+        <Link className="public-text-link" to="/catalog">
+          搜索完整目录 <span aria-hidden="true">→</span>
+        </Link>
+      </div>
+
+      {catalogQuery.isPending ? (
+        <p className="public-state" role="status">
+          正在读取真实目录……
+        </p>
+      ) : null}
+
+      {catalogQuery.isError ? (
+        <div className="public-state public-state-error" role="alert">
+          <p>目录暂时无法读取，请稍后重试。</p>
+          <button
+            type="button"
+            className="public-inline-button"
+            onClick={() => void catalogQuery.refetch()}
+          >
+            重试
+          </button>
+        </div>
+      ) : null}
+
+      {!catalogQuery.isPending &&
+      !catalogQuery.isError &&
+      items.length === 0 ? (
+        <p className="public-state">当前没有可公开的接口，请稍后再来查看。</p>
+      ) : null}
+
+      {!catalogQuery.isPending && !catalogQuery.isError && items.length > 0 ? (
+        <ul className="public-catalog-list" data-testid="catalog-preview-list">
+          {items.map((item) => (
+            <li key={item.slug} className="public-catalog-row">
+              <div className="public-path-line">
+                <span className="public-method-badge">{item.method}</span>
+                <code>{item.path}</code>
+              </div>
+              <div className="min-w-0">
+                <h3 className="truncate text-base font-semibold text-[var(--yeyu-ink)]">
+                  <Link
+                    to="/catalog/$slug"
+                    params={{ slug: item.slug }}
+                    className="public-catalog-title-link"
+                  >
+                    {item.name}
+                  </Link>
+                </h3>
+                <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
+                  {item.summary}
+                </p>
+              </div>
+              <div className="public-catalog-meta">
+                <span>{item.category}</span>
+                {item.is_free ? <span>免费</span> : null}
+                <span>{item.status}</span>
+                <time dateTime={item.updated_at ?? undefined}>
+                  {formatUpdatedAt(item.updated_at)}
+                </time>
+              </div>
+            </li>
+          ))}
+        </ul>
+      ) : null}
+    </section>
+  )
+}
+
+function PublicHome() {
+  return (
+    <PublicLayout>
+      <div className="public-container">
+        <section className="public-hero" aria-labelledby="home-heading">
+          <div className="public-hero-copy">
+            <p className="public-eyebrow">YEYU API / 公益工具箱</p>
+            <h1 id="home-heading" className="public-hero-title">
+              给学生和个人开发者的免费 API 工具箱
+            </h1>
+            <p className="public-hero-lede">
+              从清楚的接口文档开始，按公开规范调用稳定、可核验的自营工具。
+            </p>
+            <form className="public-search-form" action="/catalog" method="get">
+              <label className="sr-only" htmlFor="catalog-query">
+                搜索 API 目录
+              </label>
+              <input
+                id="catalog-query"
+                name="query"
+                className="public-search-input"
+                placeholder="搜索时间、UUID 等公开接口……"
+                type="search"
+              />
+              <button className="public-primary-button" type="submit">
+                搜索 API 目录
+              </button>
+            </form>
+            <nav className="public-hero-links" aria-label="快速入口">
+              <a className="public-text-link" href="/catalog">
+                浏览公开目录 <span aria-hidden="true">↗</span>
+              </a>
+              <a className="public-text-link" href="#usage">
+                阅读使用规范 <span aria-hidden="true">↓</span>
+              </a>
+            </nav>
+          </div>
+
+          <aside
+            className="public-boundary-note"
+            aria-labelledby="boundary-heading"
+          >
+            <p className="public-eyebrow">调用边界</p>
+            <h2 id="boundary-heading" className="public-note-title">
+              先看清楚，再开始调用
+            </h2>
+            <p className="public-note-copy">
+              公共页面只负责发现和阅读目录。真正的工具调用需要独立 API
+              Key，浏览器登录状态不会替代它。
+            </p>
+            <div className="public-note-rule" aria-hidden="true" />
+            <p className="public-note-label">示例凭据</p>
+            <code className="public-code-chip">&lt;YOUR_API_KEY&gt;</code>
+          </aside>
+        </section>
+
+        <CatalogPreview />
+
+        <section
+          id="usage"
+          className="public-section public-usage-section"
+          aria-labelledby="usage-heading"
+        >
+          <div>
+            <p className="public-eyebrow">使用规范</p>
+            <h2 id="usage-heading" className="public-section-title">
+              公益服务也需要清楚的边界
+            </h2>
+          </div>
+          <div className="public-usage-grid">
+            <p>
+              只调用目录中公开、已发布的接口；参数、缓存和来源以对应文档为准。
+            </p>
+            <p>
+              请保管好自己的 API Key，不要把密钥提交到代码仓库或分享给他人。
+            </p>
+            <p>
+              发现异常或文档问题时，请停止重试并通过项目渠道反馈，给公共资源留下余量。
+            </p>
+          </div>
+        </section>
+
+        <div className="public-bottom-cta">
+          <p>准备好查找一个清楚、可用的接口了吗？</p>
+          <Link className="public-primary-button" to="/login">
+            登录并进入控制台
+          </Link>
+        </div>
+      </div>
+    </PublicLayout>
+  )
+}
diff --git a/frontend/src/routes/login.tsx b/frontend/src/routes/login.tsx
index 3f075c5..c2c02e2 100644
--- a/frontend/src/routes/login.tsx
+++ b/frontend/src/routes/login.tsx
@@ -39,45 +39,45 @@ type FormData = z.infer<typeof formSchema>
 const searchSchema = z.object({
   oauth: z.enum(["github"]).optional(),
 })
 
 export const Route = createFileRoute("/login")({
   component: Login,
   validateSearch: searchSchema,
   beforeLoad: async ({ search }) => {
     if (isLoggedIn() && search.oauth !== "github") {
       throw redirect({
-        to: "/",
+        to: "/dashboard",
       })
     }
   },
   head: () => ({
     meta: [
       {
-        title: "Log In - FastAPI Template",
+        title: "登录 - Yeyu API",
       },
     ],
   }),
 })
 
 function Login() {
   const { loginMutation } = useAuth()
   const navigate = Route.useNavigate()
   const search = Route.useSearch()
   const [oauthError, setOauthError] = useState<string | null>(null)
 
   useEffect(() => {
     if (search.oauth !== "github") return
     UsersService.readUserMe()
       .then(() => {
         localStorage.setItem("session_authenticated", "1")
-        void navigate({ to: "/" })
+        void navigate({ to: "/dashboard" })
       })
       .catch(() => {
         localStorage.removeItem("session_authenticated")
         setOauthError("GitHub 登录未完成，请先验证邮箱后再绑定 GitHub。")
       })
   }, [navigate, search.oauth])
   const form = useForm<FormData>({
     resolver: zodResolver(formSchema),
     mode: "onBlur",
     criteriaMode: "all",
diff --git a/frontend/tests/login.spec.ts b/frontend/tests/login.spec.ts
index 8072ddc..05ef6ea 100644
--- a/frontend/tests/login.spec.ts
+++ b/frontend/tests/login.spec.ts
@@ -36,24 +36,24 @@ test("Forgot Password link is visible", async ({ page }) => {
     page.getByRole("link", { name: "Forgot your password?" }),
   ).toBeVisible()
 })
 
 test("Log in with valid email and password ", async ({ page }) => {
   await page.goto("/login")
 
   await fillForm(page, firstSuperuser, firstSuperuserPassword)
   await page.getByRole("button", { name: "Log In" }).click()
 
-  await page.waitForURL("/")
+  await page.waitForURL("/dashboard")
 
   await expect(
-    page.getByText("Welcome back, nice to see you again!"),
+    page.getByRole("heading", { name: "Yeyu API 控制台" }),
   ).toBeVisible()
 })
 
 test("Log in with invalid email", async ({ page }) => {
   await page.goto("/login")
 
   await fillForm(page, "invalidemail", firstSuperuserPassword)
   await page.getByRole("button", { name: "Log In" }).click()
 
   await expect(page.getByText("Invalid email address")).toBeVisible()
@@ -68,50 +68,71 @@ test("Log in with invalid password", async ({ page }) => {
 
   await expect(page.getByText("Incorrect email or password")).toBeVisible()
 })
 
 test("Successful log out", async ({ page }) => {
   await page.goto("/login")
 
   await fillForm(page, firstSuperuser, firstSuperuserPassword)
   await page.getByRole("button", { name: "Log In" }).click()
 
-  await page.waitForURL("/")
+  await page.waitForURL("/dashboard")
 
   await expect(
-    page.getByText("Welcome back, nice to see you again!"),
+    page.getByRole("heading", { name: "Yeyu API 控制台" }),
   ).toBeVisible()
 
   await page.getByTestId("user-menu").click()
   await page.getByRole("menuitem", { name: "Log out" }).click()
   await page.waitForURL("/login")
 })
 
 test("Logged-out user cannot access protected routes", async ({ page }) => {
   await page.goto("/login")
 
   await fillForm(page, firstSuperuser, firstSuperuserPassword)
   await page.getByRole("button", { name: "Log In" }).click()
 
-  await page.waitForURL("/")
+  await page.waitForURL("/dashboard")
 
   await expect(
-    page.getByText("Welcome back, nice to see you again!"),
+    page.getByRole("heading", { name: "Yeyu API 控制台" }),
   ).toBeVisible()
 
   await page.getByTestId("user-menu").click()
   await page.getByRole("menuitem", { name: "Log out" }).click()
   await page.waitForURL("/login")
 
   await page.goto("/settings")
   await page.waitForURL("/login")
 })
 
+test("Anonymous users are redirected to login from items", async ({ page }) => {
+  await page.goto("/items")
+
+  await page.waitForURL("/login")
+  await expect(page).toHaveURL("/login")
+})
+
+test("Logged-in users are redirected from login to dashboard", async ({
+  page,
+}) => {
+  await page.goto("/login")
+
+  await fillForm(page, firstSuperuser, firstSuperuserPassword)
+  await page.getByRole("button", { name: "Log In" }).click()
+  await page.waitForURL("/dashboard")
+
+  await page.goto("/login")
+  await page.waitForURL("/dashboard")
+  await expect(page).toHaveURL("/dashboard")
+})
+
 test("Redirects to /login when token is wrong", async ({ page }) => {
   await page.goto("/settings")
   await page.evaluate(() => {
     localStorage.setItem("access_token", "invalid_token")
   })
   await page.goto("/settings")
   await page.waitForURL("/login")
   await expect(page).toHaveURL("/login")
 })
diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
new file mode 100644
index 0000000..0c1c438
--- /dev/null
+++ b/frontend/tests/public-catalog.spec.ts
@@ -0,0 +1,594 @@
+import { expect, type Page, test } from "@playwright/test"
+
+test.use({ storageState: { cookies: [], origins: [] } })
+
+const timeItem = {
+  slug: "time",
+  name: "时间查询",
+  summary: "按可选 IANA 时区返回当前 UTC、Unix 时间戳和本地时间。",
+  category: "tools",
+  method: "GET",
+  path: "/v1/tools/time",
+  auth_type: "api_key",
+  is_free: true,
+  status: "published",
+  updated_at: "2026-10-02T00:00:00Z",
+}
+
+const uuidItem = {
+  slug: "uuid",
+  name: "UUID v4 生成器",
+  summary: "生成一个随机 UUID v4，不接受任何查询参数。",
+  category: "tools",
+  method: "GET",
+  path: "/v1/tools/uuid",
+  auth_type: "api_key",
+  is_free: true,
+  status: "published",
+  updated_at: "2026-10-02T00:00:00Z",
+}
+
+const lateFacetItem = {
+  ...uuidItem,
+  slug: "late-facet",
+  name: "后分页接口",
+  category: "data",
+  status: "deprecated",
+  path: "/v1/data/late-facet",
+}
+
+const facetPageOneItems = Array.from({ length: 100 }, (_, index) => ({
+  ...timeItem,
+  slug: `time-${index}`,
+}))
+
+const timeDetail = {
+  ...timeItem,
+  auth: { type: "api_key", header: "X-API-Key" },
+  parameters: [
+    {
+      name: "timezone",
+      in: "query",
+      required: false,
+      description: "可选的 IANA 时区名称，省略时使用 UTC。",
+      schema: {
+        type: "string",
+        default: "UTC",
+        examples: ["UTC", "Asia/Shanghai"],
+      },
+    },
+  ],
+  response_schema: {
+    type: "object",
+    properties: {
+      utc: { type: "string", format: "date-time" },
+      unix_timestamp: { type: "number" },
+      timezone: { type: "string" },
+      local: { type: "string", format: "date-time" },
+    },
+    required: ["utc", "unix_timestamp", "timezone", "local"],
+  },
+  errors: [
+    {
+      status: 401,
+      code: "API_KEY_REQUIRED",
+      description: "请求必须提供 X-API-Key。",
+    },
+    { status: 404, code: "API_NOT_FOUND", description: "接口不存在或未公开。" },
+  ],
+  examples: [
+    {
+      language: "curl",
+      request:
+        'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
+    },
+  ],
+  source: "Yeyu API",
+  cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
+}
+
+const sensitiveQueryParameters = [
+  { name: "apiKey", value: "1234567890" },
+  { name: "API_KEY", value: "1234567891" },
+  { name: "api-key", value: "1234567892" },
+  { name: "access_token", value: "1234567893" },
+  { name: "Access-Token", value: "1234567894" },
+  { name: "ACCESS.TOKEN", value: "1234567895" },
+  { name: "client_secret", value: "1234567896" },
+  { name: "Client-Secret", value: "1234567897" },
+  { name: "CLIENT.SECRET", value: "1234567898" },
+] as const
+
+const unsafeDetail = {
+  ...timeDetail,
+  auth: {
+    type: "api_key",
+    header: 'X-Evil-Header: "<NON_SECRET_TEST_VALUE>"',
+  },
+  path: "https://evil.example/redirect?token=<NON_SECRET_TEST_VALUE>",
+  parameters: [
+    ...timeDetail.parameters,
+    {
+      name: 'bad"name`$()',
+      in: "query",
+      required: false,
+      description: "恶意参数",
+      schema: {
+        type: "string",
+        examples: ["$(whoami)\n`id`"],
+        default: "<NON_SECRET_TEST_VALUE>",
+      },
+    },
+    {
+      name: "unsafe-value",
+      in: "query",
+      required: false,
+      description: "恶意默认值",
+      schema: {
+        type: "string",
+        examples: [
+          " https://evil.example/?next=<NON_SECRET_TEST_VALUE> ",
+          '"quoted"',
+          "percent%20",
+          "query?next=evil",
+          "hash#evil",
+          "back\\slash",
+          "Asia/Shanghai",
+        ],
+        default: "secret-token-<NON_SECRET_TEST_VALUE>",
+      },
+    },
+  ],
+  response_schema: {
+    ...timeDetail.response_schema,
+    token: "<NON_SECRET_TEST_VALUE>",
+    properties: {
+      ...timeDetail.response_schema.properties,
+      api_key: {
+        type: "string",
+        private_key: "<NON_SECRET_TEST_VALUE>",
+      },
+    },
+  },
+  errors: [
+    ...timeDetail.errors,
+    {
+      status: 500,
+      code: "SAFE_ERROR",
+      description: "可见错误描述",
+      authorization: "<NON_SECRET_TEST_VALUE>",
+    },
+  ],
+  cache_rules: {
+    ...timeDetail.cache_rules,
+    "provider-ref": "<NON_SECRET_TEST_VALUE>",
+    safe: { nested_password: "<NON_SECRET_TEST_VALUE>" },
+  },
+}
+
+const unsafeExamplesDetail = {
+  ...unsafeDetail,
+  path: "/v1/tools/time",
+  parameters: [
+    ...unsafeDetail.parameters,
+    ...sensitiveQueryParameters.map(({ name, value }) => ({
+      name,
+      in: "query",
+      required: false,
+      description: "敏感查询参数测试",
+      schema: { type: "string", default: value },
+    })),
+  ],
+}
+
+type CatalogPage = {
+  data: (typeof timeItem)[]
+  count: number
+  page: number
+  page_size: number
+}
+
+const catalogListUrl = /\/api\/v1\/catalog(?:\?.*)?$/
+const catalogTimeDetailUrl = /\/api\/v1\/catalog\/time(?:\?.*)?$/
+
+async function mockCatalogApi(page: Page, detail = timeDetail) {
+  await page.route(catalogTimeDetailUrl, async (route) => {
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify(detail),
+    })
+  })
+
+  await page.route(catalogListUrl, async (route) => {
+    const url = new URL(route.request().url())
+    const query = url.searchParams.get("query") ?? ""
+    const category = url.searchParams.get("category")
+    const status = url.searchParams.get("status")
+    const pageNumber = Number(url.searchParams.get("page") ?? "1")
+    const data =
+      query === "missing"
+        ? []
+        : query === "uuid"
+          ? [uuidItem]
+          : [timeItem, uuidItem]
+    const filtered = data.filter(
+      (item) =>
+        (!category || item.category === category) &&
+        (!status || item.status === status),
+    )
+    const response: CatalogPage = {
+      data: filtered,
+      count: filtered.length,
+      page: pageNumber,
+      page_size: 20,
+    }
+
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify(response),
+    })
+  })
+}
+
+test("Anonymous users can browse the real public catalog", async ({ page }) => {
+  await mockCatalogApi(page)
+  await page.goto("/catalog")
+
+  await expect(page).toHaveURL("/catalog")
+  await expect(page.getByRole("heading", { name: "API 目录" })).toBeVisible()
+  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
+  await expect(page.getByTestId("catalog-card-time")).toContainText(
+    "/v1/tools/time",
+  )
+  await expect(page.getByText("免费", { exact: true }).first()).toBeVisible()
+  await expect(
+    page.getByText("published", { exact: true }).first(),
+  ).toBeVisible()
+  await expect(page.getByRole("link", { name: /时间查询/ })).toHaveAttribute(
+    "href",
+    "/catalog/time",
+  )
+})
+
+test("Catalog search is debounced and filters are shareable in the URL", async ({
+  page,
+}) => {
+  const catalogRequests: string[] = []
+  await page.route(catalogListUrl, async (route) => {
+    const url = new URL(route.request().url())
+    catalogRequests.push(url.search)
+    const item = url.searchParams.get("query") === "uuid" ? uuidItem : timeItem
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify({ data: [item], count: 1, page: 1, page_size: 20 }),
+    })
+  })
+
+  await page.goto("/catalog?page=2")
+  const searchInput = page.getByRole("searchbox", { name: "搜索公开 API" })
+  await searchInput.fill("uuid")
+  await page.waitForTimeout(150)
+  expect(
+    catalogRequests.filter((request) => request.includes("query=uuid")),
+  ).toHaveLength(0)
+  await expect
+    .poll(() => new URL(page.url()).searchParams.get("page"))
+    .toBe("1")
+  await expect
+    .poll(() => new URL(page.url()).searchParams.get("query"))
+    .toBe("uuid")
+  await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
+
+  await page.getByLabel("分类").selectOption("tools")
+  await expect
+    .poll(() => new URL(page.url()).searchParams.get("page"))
+    .toBe("1")
+  await expect(page).toHaveURL(/query=uuid.*category=tools/)
+  await page.getByLabel("状态").selectOption("published")
+  await expect
+    .poll(() => new URL(page.url()).searchParams.get("page"))
+    .toBe("1")
+  await expect(page).toHaveURL(/query=uuid.*category=tools.*status=published/)
+})
+
+test("Catalog pagination preserves search filters and requests the selected page", async ({
+  page,
+}) => {
+  const catalogRequests: URL[] = []
+  const facetRequests: URL[] = []
+  await page.route(catalogListUrl, async (route) => {
+    const url = new URL(route.request().url())
+    const isFacetRequest =
+      url.searchParams.get("page_size") === "100" &&
+      !url.searchParams.has("query") &&
+      !url.searchParams.has("category") &&
+      !url.searchParams.has("status")
+    if (isFacetRequest) {
+      facetRequests.push(url)
+      const pageNumber = Number(url.searchParams.get("page") ?? "1")
+      const response: CatalogPage = {
+        data: pageNumber === 1 ? facetPageOneItems : [lateFacetItem],
+        count: 101,
+        page: pageNumber,
+        page_size: 100,
+      }
+      await route.fulfill({
+        status: 200,
+        contentType: "application/json",
+        body: JSON.stringify(response),
+      })
+      return
+    }
+
+    catalogRequests.push(url)
+    const pageNumber = Number(url.searchParams.get("page") ?? "1")
+    const response: CatalogPage = {
+      data: pageNumber === 2 ? [uuidItem] : [timeItem],
+      count: 21,
+      page: pageNumber,
+      page_size: 20,
+    }
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify(response),
+    })
+  })
+
+  await page.goto("/catalog?query=time&category=tools&status=published")
+  await expect(page.getByTestId("catalog-card-time")).toBeVisible()
+  await expect
+    .poll(() =>
+      facetRequests.some((request) => request.searchParams.get("page") === "2"),
+    )
+    .toBe(true)
+  expect(
+    facetRequests.every(
+      (request) => request.searchParams.get("query") === null,
+    ),
+  ).toBe(true)
+  expect(
+    facetRequests.every(
+      (request) => request.searchParams.get("category") === null,
+    ),
+  ).toBe(true)
+  expect(
+    facetRequests.every(
+      (request) => request.searchParams.get("status") === null,
+    ),
+  ).toBe(true)
+  await expect(page.getByLabel("分类").locator("option")).toContainText("data")
+  await expect(page.getByLabel("状态").locator("option")).toContainText(
+    "deprecated",
+  )
+  await expect(page.getByRole("button", { name: "下一页" })).toBeEnabled()
+
+  await page.getByRole("button", { name: "下一页" }).click()
+  await expect(page).toHaveURL(
+    /query=time.*category=tools.*status=published.*page=2/,
+  )
+  await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
+
+  const secondRequest = catalogRequests.at(-1)
+  expect(secondRequest?.searchParams.get("page")).toBe("2")
+  expect(secondRequest?.searchParams.get("page_size")).toBe("20")
+
+  await page.getByRole("button", { name: "上一页" }).click()
+  await expect(page).toHaveURL(
+    /query=time.*category=tools.*status=published.*page=1/,
+  )
+})
+
+test("Catalog marks facet options incomplete after the page safety limit", async ({
+  page,
+}) => {
+  const facetRequests: URL[] = []
+  await page.route(catalogListUrl, async (route) => {
+    const url = new URL(route.request().url())
+    const isFacetRequest =
+      url.searchParams.get("page_size") === "100" &&
+      !url.searchParams.has("query") &&
+      !url.searchParams.has("category") &&
+      !url.searchParams.has("status")
+    if (isFacetRequest) {
+      facetRequests.push(url)
+      const pageNumber = Number(url.searchParams.get("page") ?? "1")
+      await route.fulfill({
+        status: 200,
+        contentType: "application/json",
+        body: JSON.stringify({
+          data: pageNumber === 100 ? [lateFacetItem] : [timeItem],
+          count: 10_001,
+          page: pageNumber,
+          page_size: 100,
+        }),
+      })
+      return
+    }
+
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify({
+        data: [timeItem],
+        count: 1,
+        page: 1,
+        page_size: 20,
+      }),
+    })
+  })
+
+  await page.goto("/catalog")
+
+  await expect(page.getByTestId("catalog-facets-incomplete")).toBeVisible()
+  await expect(
+    page.getByText("筛选选项未完整加载", { exact: false }),
+  ).toBeVisible()
+  await expect(page.getByLabel("分类").locator("option")).toHaveText([
+    "全部分类",
+  ])
+  await expect(page.getByLabel("状态").locator("option")).toHaveText([
+    "全部状态",
+  ])
+  await expect.poll(() => facetRequests.length).toBe(100)
+  expect(facetRequests.at(-1)?.searchParams.get("page")).toBe("100")
+})
+
+test("Catalog displays an explicit empty state for an empty result", async ({
+  page,
+}) => {
+  await mockCatalogApi(page)
+  await page.goto("/catalog?query=missing")
+
+  await expect(page.getByTestId("catalog-empty")).toBeVisible()
+  await expect(page.getByText("没有找到匹配的公开接口")).toBeVisible()
+  await expect(page.getByTestId("catalog-grid")).not.toBeVisible()
+})
+
+test("Time detail documents the request contract and safe code examples", async ({
+  page,
+}) => {
+  await mockCatalogApi(page)
+  await page.goto("/catalog/time")
+
+  await expect(page).toHaveURL("/catalog/time")
+  await expect(page.getByRole("heading", { name: "时间查询" })).toBeVisible()
+  await expect(page.getByText("/v1/tools/time", { exact: true })).toBeVisible()
+  await expect(page.getByText("GET", { exact: true }).first()).toBeVisible()
+  await expect(
+    page.getByText("API Key", { exact: false }).first(),
+  ).toBeVisible()
+  await expect(page.getByText("timezone", { exact: true })).toBeVisible()
+  await expect(page.getByText("utc", { exact: true })).toBeVisible()
+  await expect(page.getByText("unix_timestamp", { exact: true })).toBeVisible()
+  await expect(
+    page.getByText("API_KEY_REQUIRED", { exact: true }),
+  ).toBeVisible()
+  await expect(page.getByText("Yeyu API", { exact: true })).toBeVisible()
+  await expect(page.getByRole("heading", { name: "curl" })).toBeVisible()
+  await expect(page.getByRole("heading", { name: "JavaScript" })).toBeVisible()
+  await expect(page.getByRole("heading", { name: "Python" })).toBeVisible()
+  await expect(
+    page.locator("code").filter({ hasText: "<YOUR_API_KEY>" }).first(),
+  ).toBeVisible()
+  await expect(
+    page.locator("code").filter({ hasText: "api.yeyubaka.top" }).first(),
+  ).toBeVisible()
+
+  const copyButton = page.getByRole("button", { name: "复制 curl 示例" })
+  await expect(copyButton).toBeVisible()
+  await copyButton.click()
+  await expect(copyButton).toContainText("已复制")
+})
+
+test("Detail rejects unsafe paths and hides sensitive metadata values", async ({
+  page,
+}) => {
+  await mockCatalogApi(page, unsafeDetail)
+  await page.goto("/catalog/time")
+
+  await expect(page.getByText("路径不可用", { exact: true })).toBeVisible()
+  await expect(page.locator("body")).not.toContainText("evil.example")
+  await expect(page.locator("body")).not.toContainText(
+    "<NON_SECRET_TEST_VALUE>",
+  )
+  await expect(page.getByText("可见错误描述", { exact: true })).toBeVisible()
+})
+
+test("Detail omits unsafe parameter examples from every code sample", async ({
+  page,
+}) => {
+  await mockCatalogApi(page, unsafeExamplesDetail)
+  await page.goto("/catalog/time")
+
+  const codeSamples = await page
+    .locator(".code-example-block code")
+    .allTextContents()
+  expect(codeSamples).toHaveLength(3)
+
+  const renderedExamples = codeSamples.join("\n")
+  expect(renderedExamples).toContain("Asia/Shanghai")
+  expect(renderedExamples).toContain("X-API-Key")
+  expect(renderedExamples).toContain("<YOUR_API_KEY>")
+  expect(renderedExamples).not.toContain('bad"name`$()')
+  expect(renderedExamples).not.toContain(
+    "https://evil.example/?next=<NON_SECRET_TEST_VALUE>",
+  )
+  expect(renderedExamples).not.toContain("$(whoami)")
+  expect(renderedExamples).not.toContain("`id`")
+  expect(renderedExamples).not.toContain("secret-token-<NON_SECRET_TEST_VALUE>")
+  expect(renderedExamples).not.toContain("X-Evil-Header")
+  for (const { name, value } of sensitiveQueryParameters) {
+    expect(renderedExamples).not.toContain(name)
+    expect(renderedExamples).not.toContain(value)
+  }
+})
+
+test("Detail errors do not render stale detail data", async ({ page }) => {
+  let detailRequestCount = 0
+  await page.route(catalogTimeDetailUrl, async (route) => {
+    detailRequestCount += 1
+    if (detailRequestCount === 1) {
+      await route.fulfill({
+        status: 200,
+        contentType: "application/json",
+        body: JSON.stringify(timeDetail),
+      })
+      return
+    }
+
+    await route.fulfill({
+      status: 503,
+      contentType: "application/json",
+      body: JSON.stringify({ detail: "unavailable" }),
+    })
+  })
+  await page.route(catalogListUrl, async (route) => {
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify({
+        data: [timeItem],
+        count: 1,
+        page: 1,
+        page_size: 20,
+      }),
+    })
+  })
+
+  await page.goto("/catalog/time")
+  await expect(page.getByRole("heading", { name: "时间查询" })).toBeVisible()
+  await page.getByRole("link", { name: /返回公开目录/ }).click()
+  await expect(page).toHaveURL("/catalog")
+  await page.getByRole("link", { name: /时间查询/ }).click()
+
+  await expect(page.getByTestId("catalog-detail-error")).toBeVisible()
+  await expect(
+    page.getByRole("heading", { name: "时间查询" }),
+  ).not.toBeVisible()
+})
+
+test("Public navigation remains keyboard accessible on mobile", async ({
+  page,
+}) => {
+  await page.setViewportSize({ width: 390, height: 844 })
+  await mockCatalogApi(page)
+  await page.goto("/")
+
+  const navigation = page.getByRole("navigation", { name: "公共导航" })
+  const menuButton = navigation.getByRole("button", { name: /菜单/ })
+
+  await expect(navigation).toBeVisible()
+  await expect(menuButton).toHaveAttribute("aria-expanded", "true")
+
+  await menuButton.press("Enter")
+  await expect(menuButton).toHaveAttribute("aria-expanded", "false")
+
+  await menuButton.press("Space")
+  await expect(menuButton).toHaveAttribute("aria-expanded", "true")
+  await expect(navigation.getByRole("link", { name: "API 目录" })).toBeVisible()
+  await expect(navigation.getByRole("link", { name: "登录" })).toBeVisible()
+})
diff --git a/plans/agent-reports/task-7-1-brief.md b/plans/agent-reports/task-7-1-brief.md
new file mode 100644
index 0000000..007c384
--- /dev/null
+++ b/plans/agent-reports/task-7-1-brief.md
@@ -0,0 +1,37 @@
+## Task 1: Add Idempotent Public Catalog Seeds
+
+**Files:**
+
+- Create E:\AI_projects\yeyu-api\backend\app\catalog_seed.py
+- Modify E:\AI_projects\yeyu-api\backend\app\initial_data.py
+- Create E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py
+
+### Implementation
+
+- [ ] 在测试中构造 SQLite 或项目现有测试 session，验证初次调用 seed_public_catalog(session) 会创建且只创建 time、uuid 两条 ApiDefinition。
+- [ ] 在测试中验证两次调用结果完全幂等，第二次不增加记录、不重置 updated_at、不覆盖管理员已经修改的 summary、status、examples 或 cache_rules。
+- [ ] 在测试中验证种子数据的 adapter_name 只能是 builtin-tools，visibility 为 public，status 为 published 或 healthy，auth_type 为 api_key，is_free 为真，路径分别为 /v1/tools/time 与 /v1/tools/uuid。
+- [ ] 在测试中验证示例请求不包含真实密钥，示例只出现 <YOUR_API_KEY> 占位符；验证 time 具有可选 timezone 参数，uuid 不允许参数。
+- [ ] 在 catalog_seed.py 暴露不可变的 PUBLIC_CATALOG_SEEDS 和 seed_public_catalog(session)，使用显式 slug 查询缺失记录后新增，不调用会覆盖已有字段的批量 upsert。
+- [ ] 为 time 和 uuid 填写面向开发者的中文 name、summary、category、method、path、parameters、response_schema、error_codes、examples、source_label、cache_rules；元数据必须与实际 builtin adapter 返回值一致。
+- [ ] 在 initial_data.init() 的现有 init_db(session) 之后调用 seed_public_catalog(session)，保留原有超级用户初始化行为。
+- [ ] 不在种子文件中读取环境变量中的密钥，不调用第三方网络，不写日志中的敏感信息。
+
+### Verification
+
+- [ ] 使用项目 conda 环境 yeyu-api 执行：
+
+~~~powershell
+conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q
+~~~
+
+- [ ] 使用项目 conda 环境执行：
+
+~~~powershell
+conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app\catalog_seed.py E:\AI_projects\yeyu-api\backend\app\initial_data.py E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py
+~~~
+
+- [ ] 记录 pytest 和 ruff 的真实输出；若数据库依赖导致环境阻塞，只记录阻塞原因，不将未运行结果标为通过。
+- [ ] 独立只读子代理检查种子幂等性、适配器字段一致性、敏感数据边界和测试充分性，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md。
+- [ ] 处理审查报告中的 Critical 或 Important 问题后重新运行上述测试，再创建提交 feat: seed public builtin catalog 并推送 origin/main。
+
diff --git a/plans/agent-reports/task-7-1-diff.md b/plans/agent-reports/task-7-1-diff.md
new file mode 100644
index 0000000..9e511c9
--- /dev/null
+++ b/plans/agent-reports/task-7-1-diff.md
@@ -0,0 +1,518 @@
+# Review package: 068092dbe64bed983f9c8614a389546159edc682..feb0136be09b0c3ddaed37af62b40b518f159c40
+
+## Commits
+feb0136 feat: seed public builtin catalog
+
+## Files changed
+ backend/app/catalog_seed.py                 | 296 ++++++++++++++++++++++++++++
+ backend/app/initial_data.py                 |   2 +
+ backend/tests/services/test_catalog_seed.py | 168 ++++++++++++++++
+ 3 files changed, 466 insertions(+)
+
+## Diff
+diff --git a/backend/app/catalog_seed.py b/backend/app/catalog_seed.py
+new file mode 100644
+index 0000000..6deef6b
+--- /dev/null
++++ b/backend/app/catalog_seed.py
+@@ -0,0 +1,296 @@
++from __future__ import annotations
++
++from collections.abc import Mapping
++from dataclasses import dataclass
++from types import MappingProxyType
++from typing import Any
++
++from sqlmodel import Session, select
++
++from app.models import ApiDefinition
++
++
++def _freeze(value: Any) -> Any:
++    if isinstance(value, dict):
++        return MappingProxyType(
++            {key: _freeze(nested) for key, nested in value.items()}
++        )
++    if isinstance(value, list):
++        return tuple(_freeze(nested) for nested in value)
++    return value
++
++
++def _thaw(value: Any) -> Any:
++    if isinstance(value, Mapping):
++        return {key: _thaw(nested) for key, nested in value.items()}
++    if isinstance(value, tuple):
++        return [_thaw(nested) for nested in value]
++    return value
++
++
++@dataclass(frozen=True, slots=True)
++class CatalogSeed:
++    slug: str
++    name: str
++    summary: str
++    category: str
++    method: str
++    path: str
++    auth_type: str
++    parameters: tuple[Mapping[str, Any], ...]
++    response_schema: Mapping[str, Any]
++    error_codes: tuple[Mapping[str, Any], ...]
++    examples: tuple[Mapping[str, Any], ...]
++    visibility: str
++    status: str
++    is_free: bool
++    source_label: str
++    adapter_name: str
++    provider_ref: str | None
++    cache_rules: Mapping[str, Any]
++
++    def model_kwargs(self) -> dict[str, Any]:
++        return {
++            "slug": self.slug,
++            "name": self.name,
++            "summary": self.summary,
++            "category": self.category,
++            "method": self.method,
++            "path": self.path,
++            "auth_type": self.auth_type,
++            "parameters": _thaw(self.parameters),
++            "response_schema": _thaw(self.response_schema),
++            "error_codes": _thaw(self.error_codes),
++            "examples": _thaw(self.examples),
++            "visibility": self.visibility,
++            "status": self.status,
++            "is_free": self.is_free,
++            "source_label": self.source_label,
++            "adapter_name": self.adapter_name,
++            "provider_ref": self.provider_ref,
++            "cache_rules": _thaw(self.cache_rules),
++        }
++
++
++_COMMON_ERROR_CODES = _freeze(
++    [
++        {
++            "status": 401,
++            "code": "API_KEY_REQUIRED",
++            "description": "请求必须提供 X-API-Key。",
++        },
++        {
++            "status": 401,
++            "code": "API_KEY_INVALID",
++            "description": "API Key 无效。",
++        },
++        {
++            "status": 401,
++            "code": "API_KEY_REVOKED",
++            "description": "API Key 已撤销。",
++        },
++        {
++            "status": 403,
++            "code": "ACCOUNT_UNVERIFIED",
++            "description": "API Key 所属账号尚未完成邮箱验证。",
++        },
++        {
++            "status": 403,
++            "code": "ACCOUNT_SUSPENDED",
++            "description": "API Key 所属账号已被停用。",
++        },
++        {
++            "status": 403,
++            "code": "IP_NOT_ALLOWED",
++            "description": "客户端 IP 不在允许范围内。",
++        },
++        {
++            "status": 403,
++            "code": "POLICY_DISABLED",
++            "description": "该 API 的调用策略已停用。",
++        },
++        {
++            "status": 422,
++            "code": "INVALID_PARAMETERS",
++            "description": "查询参数不符合接口约束。",
++        },
++        {
++            "status": 429,
++            "code": "MINUTE_LIMIT",
++            "description": "超过账号分钟调用限制。",
++        },
++        {
++            "status": 429,
++            "code": "IP_MINUTE_LIMIT",
++            "description": "超过客户端 IP 分钟调用限制。",
++        },
++        {
++            "status": 429,
++            "code": "DAILY_QUOTA_EXCEEDED",
++            "description": "超过每日调用额度。",
++        },
++        {
++            "status": 429,
++            "code": "CONCURRENCY_LIMIT",
++            "description": "超过并发调用限制。",
++        },
++        {
++            "status": 502,
++            "code": "UPSTREAM_ERROR",
++            "description": "执行适配器返回错误。",
++        },
++        {
++            "status": 503,
++            "code": "QUOTA_UNAVAILABLE",
++            "description": "配额服务暂时不可用。",
++        },
++        {
++            "status": 504,
++            "code": "UPSTREAM_TIMEOUT",
++            "description": "执行超过请求超时限制。",
++        },
++    ]
++)
++
++
++PUBLIC_CATALOG_SEEDS: tuple[CatalogSeed, ...] = (
++    CatalogSeed(
++        slug="time",
++        name="时间查询",
++        summary="按可选 IANA 时区返回当前 UTC、Unix 时间戳和本地时间。",
++        category="tools",
++        method="GET",
++        path="/v1/tools/time",
++        auth_type="api_key",
++        parameters=(
++            _freeze(
++                {
++                    "name": "timezone",
++                    "in": "query",
++                    "required": False,
++                    "description": "可选的 IANA 时区名称，省略时使用 UTC。",
++                    "schema": {
++                        "type": "string",
++                        "default": "UTC",
++                        "examples": ["UTC", "Asia/Shanghai"],
++                    },
++                }
++            ),
++        ),
++        response_schema=_freeze(
++            {
++                "type": "object",
++                "properties": {
++                    "utc": {"type": "string", "format": "date-time"},
++                    "unix_timestamp": {"type": "number"},
++                    "timezone": {"type": "string"},
++                    "local": {"type": "string", "format": "date-time"},
++                },
++                "required": ["utc", "unix_timestamp", "timezone", "local"],
++                "additionalProperties": False,
++            }
++        ),
++        error_codes=_COMMON_ERROR_CODES,
++        examples=(
++            _freeze(
++                {
++                    "language": "curl",
++                    "request": (
++                        "curl -G https://api.yeyubaka.top/v1/tools/time "
++                        "-H \"X-API-Key: <YOUR_API_KEY>\" "
++                        "--data-urlencode \"timezone=Asia/Shanghai\""
++                    ),
++                    "response": {
++                        "utc": "2026-01-01T00:00:00Z",
++                        "unix_timestamp": 1767225600,
++                        "timezone": "Asia/Shanghai",
++                        "local": "2026-01-01T08:00:00+08:00",
++                    },
++                }
++            ),
++        ),
++        visibility="public",
++        status="published",
++        is_free=True,
++        source_label="Yeyu API",
++        adapter_name="builtin-tools",
++        provider_ref="builtin-tools:time",
++        cache_rules=_freeze(
++            {
++                "cacheable": False,
++                "ttl_seconds": 0,
++                "stale_if_error": False,
++            }
++        ),
++    ),
++    CatalogSeed(
++        slug="uuid",
++        name="UUID v4 生成器",
++        summary="生成一个随机 UUID v4，不接受任何查询参数。",
++        category="tools",
++        method="GET",
++        path="/v1/tools/uuid",
++        auth_type="api_key",
++        parameters=(),
++        response_schema=_freeze(
++            {
++                "type": "object",
++                "properties": {
++                    "uuid": {"type": "string", "format": "uuid"},
++                    "version": {"type": "integer", "const": 4},
++                },
++                "required": ["uuid", "version"],
++                "additionalProperties": False,
++            }
++        ),
++        error_codes=_COMMON_ERROR_CODES,
++        examples=(
++            _freeze(
++                {
++                    "language": "curl",
++                    "request": (
++                        "curl https://api.yeyubaka.top/v1/tools/uuid "
++                        "-H \"X-API-Key: <YOUR_API_KEY>\""
++                    ),
++                    "response": {
++                        "uuid": "00000000-0000-4000-8000-000000000000",
++                        "version": 4,
++                    },
++                }
++            ),
++        ),
++        visibility="public",
++        status="published",
++        is_free=True,
++        source_label="Yeyu API",
++        adapter_name="builtin-tools",
++        provider_ref="builtin-tools:uuid",
++        cache_rules=_freeze(
++            {
++                "cacheable": False,
++                "ttl_seconds": 0,
++                "stale_if_error": False,
++            }
++        ),
++    ),
++)
++
++
++def seed_public_catalog(session: Session) -> None:
++    """Insert missing builtin catalog definitions without changing existing rows."""
++
++    added = False
++    for seed in PUBLIC_CATALOG_SEEDS:
++        existing = session.exec(
++            select(ApiDefinition).where(ApiDefinition.slug == seed.slug)
++        ).first()
++        if existing is not None:
++            continue
++        session.add(ApiDefinition(**seed.model_kwargs()))
++        added = True
++
++    if added:
++        session.commit()
++
++
++__all__ = ["CatalogSeed", "PUBLIC_CATALOG_SEEDS", "seed_public_catalog"]
+diff --git a/backend/app/initial_data.py b/backend/app/initial_data.py
+index d806c3d..388fd33 100644
+--- a/backend/app/initial_data.py
++++ b/backend/app/initial_data.py
+@@ -1,23 +1,25 @@
+ import logging
+ 
+ from sqlmodel import Session
+ 
++from app.catalog_seed import seed_public_catalog
+ from app.core.db import engine, init_db
+ 
+ logging.basicConfig(level=logging.INFO)
+ logger = logging.getLogger(__name__)
+ 
+ 
+ def init() -> None:
+     with Session(engine) as session:
+         init_db(session)
++        seed_public_catalog(session)
+ 
+ 
+ def main() -> None:
+     logger.info("Creating initial data")
+     init()
+     logger.info("Initial data created")
+ 
+ 
+ if __name__ == "__main__":
+     main()
+diff --git a/backend/tests/services/test_catalog_seed.py b/backend/tests/services/test_catalog_seed.py
+new file mode 100644
+index 0000000..28425b8
+--- /dev/null
++++ b/backend/tests/services/test_catalog_seed.py
+@@ -0,0 +1,168 @@
++from __future__ import annotations
++
++import json
++from collections.abc import Iterator
++from dataclasses import FrozenInstanceError
++from datetime import datetime
++
++import pytest
++from sqlalchemy.pool import StaticPool
++from sqlmodel import Session, SQLModel, create_engine, select
++
++from app import initial_data
++from app.catalog_seed import PUBLIC_CATALOG_SEEDS, seed_public_catalog
++from app.models import ApiDefinition
++
++
++@pytest.fixture()
++def session() -> Iterator[Session]:
++    engine = create_engine(
++        "sqlite://",
++        connect_args={"check_same_thread": False},
++        poolclass=StaticPool,
++    )
++    SQLModel.metadata.create_all(engine)
++    with Session(engine) as db_session:
++        yield db_session
++
++
++def _definitions(session: Session) -> list[ApiDefinition]:
++    return list(
++        session.exec(select(ApiDefinition).order_by(ApiDefinition.slug)).all()
++    )
++
++
++def test_public_catalog_seed_creates_time_and_uuid_with_adapter_contract(
++    session: Session,
++) -> None:
++    seed_public_catalog(session)
++
++    definitions = _definitions(session)
++    assert [definition.slug for definition in definitions] == ["time", "uuid"]
++
++    for definition in definitions:
++        assert definition.method == "GET"
++        assert definition.auth_type == "api_key"
++        assert definition.adapter_name == "builtin-tools"
++        assert definition.visibility == "public"
++        assert definition.status in {"healthy", "published"}
++        assert definition.is_free is True
++        assert definition.path == f"/v1/tools/{definition.slug}"
++        assert definition.source_label == "Yeyu API"
++        assert definition.cache_rules["cacheable"] is False
++        assert definition.cache_rules["stale_if_error"] is False
++        assert "INVALID_PARAMETERS" in {
++            error["code"] for error in definition.error_codes
++        }
++
++        examples = json.dumps(definition.examples, ensure_ascii=False)
++        assert "<YOUR_API_KEY>" in examples
++        assert "sk-" not in examples
++
++    time_definition = definitions[0]
++    timezone_parameter = time_definition.parameters[0]
++    assert timezone_parameter["name"] == "timezone"
++    assert timezone_parameter["in"] == "query"
++    assert timezone_parameter["required"] is False
++    assert timezone_parameter["schema"]["default"] == "UTC"
++    assert set(time_definition.response_schema["properties"]) == {
++        "utc",
++        "unix_timestamp",
++        "timezone",
++        "local",
++    }
++
++    uuid_definition = definitions[1]
++    assert uuid_definition.parameters == []
++    assert uuid_definition.response_schema["properties"]["version"]["const"] == 4
++    assert set(uuid_definition.response_schema["required"]) == {"uuid", "version"}
++
++
++def test_public_catalog_seed_is_idempotent_and_preserves_admin_edits(
++    session: Session,
++) -> None:
++    seed_public_catalog(session)
++
++    time_definition = session.exec(
++        select(ApiDefinition).where(ApiDefinition.slug == "time")
++    ).one()
++    time_definition.summary = "管理员维护的时间工具说明"
++    time_definition.status = "healthy"
++    time_definition.examples = [
++        {"language": "text", "request": "管理员示例 <YOUR_API_KEY>"}
++    ]
++    time_definition.cache_rules = {
++        "cacheable": True,
++        "ttl_seconds": 7,
++        "stale_if_error": True,
++    }
++    time_definition.updated_at = datetime(2026, 10, 1, 12, 34, 56)
++    session.add(time_definition)
++    session.commit()
++    session.expire_all()
++
++    before = session.exec(
++        select(ApiDefinition).where(ApiDefinition.slug == "time")
++    ).one()
++    before_id = before.id
++    before_updated_at = before.updated_at
++
++    seed_public_catalog(session)
++    session.expire_all()
++
++    definitions = _definitions(session)
++    assert len(definitions) == 2
++    after = session.exec(
++        select(ApiDefinition).where(ApiDefinition.slug == "time")
++    ).one()
++    assert after.id == before_id
++    assert after.updated_at == before_updated_at
++    assert after.summary == "管理员维护的时间工具说明"
++    assert after.status == "healthy"
++    assert after.examples == [
++        {"language": "text", "request": "管理员示例 <YOUR_API_KEY>"}
++    ]
++    assert after.cache_rules == {
++        "cacheable": True,
++        "ttl_seconds": 7,
++        "stale_if_error": True,
++    }
++
++
++def test_public_catalog_seeds_are_deeply_immutable() -> None:
++    assert isinstance(PUBLIC_CATALOG_SEEDS, tuple)
++
++    with pytest.raises(TypeError):
++        PUBLIC_CATALOG_SEEDS[0] = PUBLIC_CATALOG_SEEDS[1]  # type: ignore[index]
++    with pytest.raises(FrozenInstanceError):
++        PUBLIC_CATALOG_SEEDS[0].slug = "changed"  # type: ignore[misc]
++    with pytest.raises(TypeError):
++        PUBLIC_CATALOG_SEEDS[0].parameters[0]["required"] = True  # type: ignore[index]
++
++
++def test_init_seeds_catalog_after_existing_init_db(monkeypatch: pytest.MonkeyPatch) -> None:
++    events: list[tuple[str, object]] = []
++
++    class SessionStub:
++        def __enter__(self) -> SessionStub:
++            return self
++
++        def __exit__(self, *_args: object) -> None:
++            return None
++
++    session = SessionStub()
++    monkeypatch.setattr(initial_data, "Session", lambda _engine: session)
++    monkeypatch.setattr(
++        initial_data,
++        "init_db",
++        lambda passed_session: events.append(("init_db", passed_session)),
++    )
++    monkeypatch.setattr(
++        initial_data,
++        "seed_public_catalog",
++        lambda passed_session: events.append(("seed", passed_session)),
++    )
++
++    initial_data.init()
++
++    assert events == [("init_db", session), ("seed", session)]
diff --git a/plans/agent-reports/task-7-1-report.md b/plans/agent-reports/task-7-1-report.md
new file mode 100644
index 0000000..6ccdc5d
--- /dev/null
+++ b/plans/agent-reports/task-7-1-report.md
@@ -0,0 +1,79 @@
+# Task 7-1 交付报告：公共 builtin-tools 目录种子
+
+## Status
+
+DONE_WITH_CONCERNS。实现、任务级 SQLite 测试和 Ruff 已通过；按简报原命令运行时，项目全局 PostgreSQL fixture 因本机认证环境阻塞。代码已提交，未执行线上操作。
+
+## 实现内容
+
+- 新增不可变的 `PUBLIC_CATALOG_SEEDS`，包含 `time` 与 `uuid` 两条公开目录定义。
+- 复用 `ApiDefinition` 字段和 builtin-tools 约束：GET、`api_key`、`builtin-tools`、public、published、`/v1/tools/<slug>`、免费。
+- time 元数据描述可选 `timezone`（默认 UTC），响应为 `utc`、`unix_timestamp`、`timezone`、`local`；uuid 元数据描述无参数且返回 `uuid`、`version=4`。
+- 示例仅使用 `<YOUR_API_KEY>` 占位符；种子不读取环境密钥、不访问网络、不输出日志。
+- `seed_public_catalog(session)` 对每个 slug 显式查询，只新增缺失记录；已有记录完全跳过，不覆盖管理员的 `summary`、`status`、`examples`、`cache_rules` 或 `updated_at`。
+- `initial_data.init()` 保留原有 `init_db(session)`，并在其后使用同一 session 调用种子函数。
+
+## 文件
+
+- `E:\AI_projects\yeyu-api\backend\app\catalog_seed.py`
+- `E:\AI_projects\yeyu-api\backend\app\initial_data.py`
+- `E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py`
+- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-report.md`
+- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md`
+
+## TDD RED
+
+1. 简报原命令：
+
+   `conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q`
+
+   原始结果：测试收集阶段失败，`Settings()` 缺少 `SECRET_KEY`、`PROJECT_NAME`、`DATABASE_URL`、`FIRST_SUPERUSER`、`FIRST_SUPERUSER_PASSWORD` 五项配置。
+
+2. 在不落盘的测试配置下、隔离项目全局数据库 fixture 的 RED 命令：
+
+   `conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\services`
+
+   原始结果：`ModuleNotFoundError: No module named 'app.catalog_seed'`，4 个测试均未进入断言。
+
+## GREEN
+
+命令：
+
+`conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\services`
+
+实际输出：
+
+`....                                                                     [100%]`
+
+`4 passed in 0.79s`
+
+Ruff 命令：
+
+`conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app\catalog_seed.py E:\AI_projects\yeyu-api\backend\app\initial_data.py E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py`
+
+实际输出：`All checks passed!`
+
+## 其他测试
+
+- `test_catalog.py`：`5 passed in 0.68s`。
+- `test_execution.py`：`51 passed in 0.26s`。
+- `git diff --check`：无 whitespace 错误。
+
+## 阻塞与未解决风险
+
+- 简报原始 pytest 命令会加载 `backend\tests\conftest.py` 的 session 级 PostgreSQL fixture；使用仅限当前进程的非生产测试配置运行时，数据库连接在认证阶段失败，得到 4 个 setup errors，未进入本任务测试。未修改数据库、环境文件或线上服务。
+- 独立只读 `codex review --uncommitted` 进程已启动，但按用户要求中止，未返回审查结论；因此 `task-7-1-review.md` 只记录审查未完成，不能把独立审查说成通过。已完成本地 diff、字段契约、敏感数据边界和测试覆盖的自审。
+- 尚未做真实 PostgreSQL/生产初始化验收；本任务没有 DNS、Nginx、服务器或线上变更。
+
+## 提交
+
+提交主题：`feat: seed public builtin catalog`
+
+提交 SHA：`feb0136be09b0c3ddaed37af62b40b518f159c40`
+
+## Self-review
+
+- 变更范围仅涉及简报列出的种子、初始化调用、任务测试及交付记录。
+- 种子元数据通过递归冻结并在写入模型前复制解冻，避免常量被修改，也避免共享可变 JSON 对象污染数据库记录。
+- 重复调用没有更新路径；只有发现缺失记录时才 commit。
+- 测试覆盖初次创建、完整公共字段、time/uuid 参数与响应契约、API Key 占位符、深层不可变性、幂等性、管理员编辑保留和初始化调用顺序。
diff --git a/plans/agent-reports/task-7-1-review.md b/plans/agent-reports/task-7-1-review.md
new file mode 100644
index 0000000..48bc8ae
--- /dev/null
+++ b/plans/agent-reports/task-7-1-review.md
@@ -0,0 +1,41 @@
+# Task 7-1 独立只读审查报告
+
+## Spec Compliance
+
+- ✅ PUBLIC_CATALOG_SEEDS 仅包含 time、uuid，字段与约束正确；catalog_seed.py:156-273。
+- ✅ 按 slug 查询并仅新增缺失记录，不覆盖已有字段；catalog_seed.py:279-293。
+- ✅ 初始化顺序正确；initial_data.py:14-15。
+- ✅ 适配器契约一致：time 的 timezone 与四个返回字段、uuid 的无参数及返回字段均匹配；backend/app/services/execution/adapters/tools.py:35-60,74-80。
+- ✅ 测试覆盖真实 SQLite、幂等及管理员字段保留、敏感示例边界、初始化顺序；test_catalog_seed.py:17-29,35-130,143-168。
+- ⚠️ 无法从 diff 独立验证实现报告中的实际运行输出、其他测试结果及 PostgreSQL fixture 认证失败；报告文字记录了这些结果，测试数量与代码覆盖和 4 passed 一致。
+
+## Strengths
+
+- 使用显式 slug 查询和条件提交，重复运行不会覆盖管理员编辑或更新时间。
+- 通过递归冻结种子数据，并在写入模型前解冻，避免共享可变对象。
+- 示例只使用 <YOUR_API_KEY>，未发现密钥、环境变量读取、网络调用或敏感日志。
+
+## Issues
+
+### Critical (Must Fix)
+
+- 无。
+
+### Important (Should Fix)
+
+- 无。
+
+### Minor (Nice to Have)
+
+- 无。
+
+## Assessment
+
+**Task quality:** Approved
+
+**Reasoning:** diff 和适配器最小范围核查均符合任务约束，测试覆盖了要求的核心行为。运行报告中的环境阻塞仍需后续独立验证，但不构成当前实现缺陷。
+
+## Review Boundary
+
+- 独立审查代理只读检查了基线 068092d 到提交 feb0136 的完整 diff 包，没有修改源码、索引、HEAD、分支或线上服务。
+- 项目完整 pytest 的 PostgreSQL fixture 认证阻塞仍为未验证事项，不被本审查报告标记为通过。
diff --git a/plans/agent-reports/task-7-2-brief.md b/plans/agent-reports/task-7-2-brief.md
new file mode 100644
index 0000000..963e9d9
--- /dev/null
+++ b/plans/agent-reports/task-7-2-brief.md
@@ -0,0 +1,52 @@
+## Task 2: Split Public and Protected Route Shells
+
+**Files:**
+
+- Create E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\routes\_layout\dashboard.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicLayout.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicFooter.tsx
+- Delete E:\AI_projects\yeyu-api\frontend\src\routes\_layout\index.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\routes\_layout.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\hooks\useAuth.ts
+- Modify E:\AI_projects\yeyu-api\frontend\src\routes\login.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\components\Sidebar\AppSidebar.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\components\Common\Logo.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\components\Common\Footer.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\index.css
+- Create or modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+- Modify E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts
+
+### Implementation
+
+- [ ] 先更新 Playwright 断言：匿名访问 / 不跳转 /login；匿名访问 /catalog 不跳转 /login；登录成功后的目标为 /dashboard；受保护的 /items 仍在未登录时跳转 /login。
+- [ ] 实现 PublicLayout、PublicHeader、PublicFooter，导航至少包含首页、API 目录、登录；移动端提供可访问的折叠菜单或等价的键盘可用导航；登录状态下显示控制台入口。
+- [ ] 将受保护根页面从 _layout/index.tsx 迁移为 _layout/dashboard.tsx，路由标题改为 Yeyu API 控制台，保留当前用户欢迎信息，不把公共首页内容复制到控制台。
+- [ ] 将 useAuth 登录成功跳转、GitHub callback 成功跳转和 login.tsx 的已登录重定向统一改为 /dashboard；登录失败、回调失败和登出行为保持现有语义。
+- [ ] 将侧边栏 Dashboard 链接改为 /dashboard，避免继续指向公共首页；更新 Logo 和 Footer，移除 FastAPI Template 品牌、链接和文案，替换为 Yeyu API 公益平台信息。
+- [ ] 让 E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx 使用 PublicLayout 作为公共首页入口，首页只渲染真实目录数据、搜索入口、公益说明和使用规范入口；数据加载失败时显示明确的错误状态，不伪造接口卡片。
+- [ ] 修改 index.css 建立设计变量：纸白背景、墨色正文、青绿色主色、浅青绿色表面、琥珀色警示色和可见焦点环；保留 Tailwind/shadcn 现有组件可用，不引入远程 CSS。
+- [ ] 保证公共壳层的 main、导航、按钮、表单控件有语义标签、键盘焦点、可读颜色和移动端溢出处理。
+
+### Verification
+
+- [ ] 执行前端格式与类型构建：
+
+~~~powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
+pnpm build
+~~~
+
+- [ ] 执行只覆盖路由边界的 Playwright 测试：
+
+~~~powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec playwright test tests/public-catalog.spec.ts tests/login.spec.ts
+~~~
+
+- [ ] 记录构建、Biome 和 Playwright 的实际结果；没有运行 Docker 依赖时标明具体阻塞。
+- [ ] 独立只读子代理检查路由树迁移是否完整、匿名/登录边界、键盘可用性、品牌残留和是否误触及旧项目，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-2-review.md。
+- [ ] 处理审查问题后重新构建和运行边界测试，创建提交 feat: split public and protected web shells 并推送 origin/main。
+
diff --git a/plans/agent-reports/task-7-2-diff.md b/plans/agent-reports/task-7-2-diff.md
new file mode 100644
index 0000000..44ba5ab
--- /dev/null
+++ b/plans/agent-reports/task-7-2-diff.md
@@ -0,0 +1,1574 @@
+# Review package: e125ac2..4c43285
+
+## Commits
+4c43285 docs: record task 7-2 implementation report
+0acbfc3 feat: split public and protected web shells
+
+## Files changed
+ frontend/src/components/Common/Footer.tsx          |  44 +-
+ frontend/src/components/Common/Logo.tsx            |  55 +--
+ .../src/components/PublicSite/PublicFooter.tsx     |  33 ++
+ .../src/components/PublicSite/PublicHeader.tsx     |  86 ++++
+ .../src/components/PublicSite/PublicLayout.tsx     |  20 +
+ frontend/src/components/Sidebar/AppSidebar.tsx     |   2 +-
+ frontend/src/hooks/useAuth.ts                      |   2 +-
+ frontend/src/index.css                             | 500 ++++++++++++++++++++-
+ frontend/src/routes/_layout.tsx                    |   7 +-
+ frontend/src/routes/_layout/dashboard.tsx          |  34 ++
+ frontend/src/routes/_layout/index.tsx              |  31 --
+ frontend/src/routes/index.tsx                      | 212 +++++++++
+ frontend/src/routes/login.tsx                      |   6 +-
+ frontend/tests/login.spec.ts                       |  29 +-
+ frontend/tests/public-catalog.spec.ts              |  39 ++
+ plans/agent-reports/task-7-2-report.md             | 106 +++++
+ 16 files changed, 1090 insertions(+), 116 deletions(-)
+
+## Diff
+diff --git a/frontend/src/components/Common/Footer.tsx b/frontend/src/components/Common/Footer.tsx
+index 279e1e7..5687a91 100644
+--- a/frontend/src/components/Common/Footer.tsx
++++ b/frontend/src/components/Common/Footer.tsx
+@@ -1,44 +1,30 @@
+-import { FaGithub, FaLinkedinIn } from "react-icons/fa"
+-import { FaXTwitter } from "react-icons/fa6"
+-
+-const socialLinks = [
+-  {
+-    icon: FaGithub,
+-    href: "https://github.com/fastapi/fastapi",
+-    label: "GitHub",
+-  },
+-  { icon: FaXTwitter, href: "https://x.com/fastapi", label: "X" },
+-  {
+-    icon: FaLinkedinIn,
+-    href: "https://linkedin.com/company/fastapi",
+-    label: "LinkedIn",
+-  },
+-]
++import { Link } from "@tanstack/react-router"
+ 
+ export function Footer() {
+   const currentYear = new Date().getFullYear()
+ 
+   return (
+     <footer className="border-t py-4 px-6">
+       <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
+         <p className="text-muted-foreground text-sm">
+-          Full Stack FastAPI Template - {currentYear}
++          Yeyu API 公益平台 - {currentYear}
+         </p>
+         <div className="flex items-center gap-4">
+-          {socialLinks.map(({ icon: Icon, href, label }) => (
+-            <a
+-              key={label}
+-              href={href}
+-              target="_blank"
+-              rel="noopener noreferrer"
+-              aria-label={label}
+-              className="text-muted-foreground hover:text-foreground transition-colors"
+-            >
+-              <Icon className="h-5 w-5" />
+-            </a>
+-          ))}
++          <Link
++            to="/"
++            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
++          >
++            返回公共首页
++          </Link>
++          <Link
++            to="/"
++            hash="usage"
++            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
++          >
++            使用规范
++          </Link>
+         </div>
+       </div>
+     </footer>
+   )
+ }
+diff --git a/frontend/src/components/Common/Logo.tsx b/frontend/src/components/Common/Logo.tsx
+index 05c299f..d574f16 100644
+--- a/frontend/src/components/Common/Logo.tsx
++++ b/frontend/src/components/Common/Logo.tsx
+@@ -1,60 +1,61 @@
+ import { Link } from "@tanstack/react-router"
+ 
+-import { useTheme } from "@/components/theme-provider"
+ import { cn } from "@/lib/utils"
+-import icon from "/assets/images/fastapi-icon.svg"
+-import iconLight from "/assets/images/fastapi-icon-light.svg"
+-import logo from "/assets/images/fastapi-logo.svg"
+-import logoLight from "/assets/images/fastapi-logo-light.svg"
+ 
+ interface LogoProps {
+   variant?: "full" | "icon" | "responsive"
+   className?: string
+   asLink?: boolean
+ }
+ 
+ export function Logo({
+   variant = "full",
+   className,
+   asLink = true,
+ }: LogoProps) {
+-  const { resolvedTheme } = useTheme()
+-  const isDark = resolvedTheme === "dark"
+-
+-  const fullLogo = isDark ? logoLight : logo
+-  const iconLogo = isDark ? iconLight : icon
+-
+   const content =
+     variant === "responsive" ? (
+       <>
+-        <img
+-          src={fullLogo}
+-          alt="FastAPI"
++        <span
++          aria-hidden="true"
+           className={cn(
+-            "h-6 w-auto group-data-[collapsible=icon]:hidden",
++            "inline-flex h-7 items-center gap-1.5 text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden",
+             className,
+           )}
+-        />
+-        <img
+-          src={iconLogo}
+-          alt="FastAPI"
++        >
++          <span className="logo-mark">Y</span>
++          <span>Yeyu API</span>
++        </span>
++        <span
++          aria-hidden="true"
+           className={cn(
+-            "size-5 hidden group-data-[collapsible=icon]:block",
++            "logo-mark hidden size-7 items-center justify-center text-sm group-data-[collapsible=icon]:inline-flex",
+             className,
+           )}
+-        />
++        >
++          Y
++        </span>
+       </>
+     ) : (
+-      <img
+-        src={variant === "full" ? fullLogo : iconLogo}
+-        alt="FastAPI"
+-        className={cn(variant === "full" ? "h-6 w-auto" : "size-5", className)}
+-      />
++      <span
++        aria-hidden="true"
++        className={cn(
++          "inline-flex items-center gap-2 text-lg font-semibold tracking-tight",
++          className,
++        )}
++      >
++        <span className="logo-mark">Y</span>
++        {variant === "full" ? <span>Yeyu API</span> : null}
++      </span>
+     )
+ 
+   if (!asLink) {
+     return content
+   }
+ 
+-  return <Link to="/">{content}</Link>
++  return (
++    <Link to="/" aria-label="Yeyu API 首页" className="inline-flex">
++      {content}
++    </Link>
++  )
+ }
+diff --git a/frontend/src/components/PublicSite/PublicFooter.tsx b/frontend/src/components/PublicSite/PublicFooter.tsx
+new file mode 100644
+index 0000000..15a05ca
+--- /dev/null
++++ b/frontend/src/components/PublicSite/PublicFooter.tsx
+@@ -0,0 +1,33 @@
++import { Link } from "@tanstack/react-router"
++
++export function PublicFooter() {
++  const currentYear = new Date().getFullYear()
++
++  return (
++    <footer className="public-footer">
++      <div className="public-container flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
++        <div>
++          <p className="font-semibold text-[var(--yeyu-ink)]">
++            Yeyu API 公益平台
++          </p>
++          <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
++            面向学生与个人开发者的公开工具目录 · {currentYear}
++          </p>
++        </div>
++        <nav aria-label="页脚导航" className="flex flex-wrap gap-4 text-sm">
++          <a className="public-footer-link" href="/catalog">
++            API 目录
++          </a>
++          <Link className="public-footer-link" to="/" hash="usage">
++            使用规范
++          </Link>
++          <Link className="public-footer-link" to="/login">
++            登录
++          </Link>
++        </nav>
++      </div>
++    </footer>
++  )
++}
++
++export default PublicFooter
+diff --git a/frontend/src/components/PublicSite/PublicHeader.tsx b/frontend/src/components/PublicSite/PublicHeader.tsx
+new file mode 100644
+index 0000000..e6daf45
+--- /dev/null
++++ b/frontend/src/components/PublicSite/PublicHeader.tsx
+@@ -0,0 +1,86 @@
++import { Link } from "@tanstack/react-router"
++import { Menu, X } from "lucide-react"
++import { useState } from "react"
++
++import { Logo } from "@/components/Common/Logo"
++import { isLoggedIn } from "@/hooks/useAuth"
++
++interface NavigationLinksProps {
++  onNavigate?: () => void
++}
++
++function NavigationLinks({ onNavigate }: NavigationLinksProps) {
++  const linkClassName =
++    "public-nav-link rounded-md px-3 py-2 text-sm font-medium"
++
++  return (
++    <>
++      <Link to="/" className={linkClassName} onClick={onNavigate}>
++        首页
++      </Link>
++      <a href="/catalog" className={linkClassName} onClick={onNavigate}>
++        API 目录
++      </a>
++      <Link to="/" hash="usage" className={linkClassName} onClick={onNavigate}>
++        使用规范
++      </Link>
++      {isLoggedIn() ? (
++        <Link
++          to="/dashboard"
++          className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
++          onClick={onNavigate}
++        >
++          控制台
++        </Link>
++      ) : (
++        <Link
++          to="/login"
++          className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
++          onClick={onNavigate}
++        >
++          登录
++        </Link>
++      )}
++    </>
++  )
++}
++
++export function PublicHeader() {
++  const [menuOpen, setMenuOpen] = useState(true)
++  const toggleMenu = () => setMenuOpen((open) => !open)
++  const closeMenu = () => setMenuOpen(false)
++
++  return (
++    <header className="public-header">
++      <div className="public-container public-header-inner">
++        <Logo variant="full" className="h-8" />
++
++        <nav aria-label="公共导航" className="public-nav">
++          <div className="hidden items-center gap-1 md:flex">
++            <NavigationLinks />
++          </div>
++          <button
++            type="button"
++            className="public-menu-button md:hidden"
++            aria-controls="public-mobile-navigation"
++            aria-expanded={menuOpen}
++            aria-label={menuOpen ? "收起菜单" : "打开菜单"}
++            onClick={toggleMenu}
++          >
++            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
++          </button>
++          {menuOpen ? (
++            <div
++              id="public-mobile-navigation"
++              className="public-mobile-navigation md:hidden"
++            >
++              <NavigationLinks onNavigate={closeMenu} />
++            </div>
++          ) : null}
++        </nav>
++      </div>
++    </header>
++  )
++}
++
++export default PublicHeader
+diff --git a/frontend/src/components/PublicSite/PublicLayout.tsx b/frontend/src/components/PublicSite/PublicLayout.tsx
+new file mode 100644
+index 0000000..7bb6666
+--- /dev/null
++++ b/frontend/src/components/PublicSite/PublicLayout.tsx
+@@ -0,0 +1,20 @@
++import type { ReactNode } from "react"
++
++import PublicFooter from "./PublicFooter"
++import PublicHeader from "./PublicHeader"
++
++interface PublicLayoutProps {
++  children: ReactNode
++}
++
++export function PublicLayout({ children }: PublicLayoutProps) {
++  return (
++    <div className="public-site flex min-h-svh flex-col">
++      <PublicHeader />
++      <main className="min-w-0 flex-1">{children}</main>
++      <PublicFooter />
++    </div>
++  )
++}
++
++export default PublicLayout
+diff --git a/frontend/src/components/Sidebar/AppSidebar.tsx b/frontend/src/components/Sidebar/AppSidebar.tsx
+index 8502bcb..0442aa0 100644
+--- a/frontend/src/components/Sidebar/AppSidebar.tsx
++++ b/frontend/src/components/Sidebar/AppSidebar.tsx
+@@ -6,21 +6,21 @@ import {
+   Sidebar,
+   SidebarContent,
+   SidebarFooter,
+   SidebarHeader,
+ } from "@/components/ui/sidebar"
+ import useAuth from "@/hooks/useAuth"
+ import { type Item, Main } from "./Main"
+ import { User } from "./User"
+ 
+ const baseItems: Item[] = [
+-  { icon: Home, title: "Dashboard", path: "/" },
++  { icon: Home, title: "Dashboard", path: "/dashboard" },
+   { icon: Briefcase, title: "Items", path: "/items" },
+ ]
+ 
+ export function AppSidebar() {
+   const { user: currentUser } = useAuth()
+ 
+   const items = currentUser?.is_superuser
+     ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
+     : baseItems
+ 
+diff --git a/frontend/src/hooks/useAuth.ts b/frontend/src/hooks/useAuth.ts
+index 9c6cfc7..ba37f06 100644
+--- a/frontend/src/hooks/useAuth.ts
++++ b/frontend/src/hooks/useAuth.ts
+@@ -45,21 +45,21 @@ const useAuth = () => {
+   const login = async (data: AccessToken) => {
+     const response = await LoginService.loginAccessToken({
+       body: data,
+     })
+     localStorage.setItem("access_token", response.data.access_token)
+   }
+ 
+   const loginMutation = useMutation({
+     mutationFn: login,
+     onSuccess: () => {
+-      navigate({ to: "/" })
++      navigate({ to: "/dashboard" })
+     },
+     onError: handleError.bind(showErrorToast),
+   })
+ 
+   const logout = () => {
+     void client
+       .post({ url: "/api/v1/auth/logout", throwOnError: true })
+       .finally(() => {
+         localStorage.removeItem("access_token")
+         localStorage.removeItem("session_authenticated")
+diff --git a/frontend/src/index.css b/frontend/src/index.css
+index 47e5696..a042441 100644
+--- a/frontend/src/index.css
++++ b/frontend/src/index.css
+@@ -36,38 +36,46 @@
+   --color-sidebar-primary: var(--sidebar-primary);
+   --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
+   --color-sidebar-accent: var(--sidebar-accent);
+   --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
+   --color-sidebar-border: var(--sidebar-border);
+   --color-sidebar-ring: var(--sidebar-ring);
+ }
+ 
+ :root {
+   --radius: 0.625rem;
+-  --background: oklch(1 0 0);
+-  --foreground: oklch(0.145 0 0);
+-  --card: oklch(1 0 0);
+-  --card-foreground: oklch(0.145 0 0);
+-  --popover: oklch(1 0 0);
+-  --popover-foreground: oklch(0.145 0 0);
+-  --primary: oklch(0.5982 0.10687 182.4689);
+-  --primary-foreground: oklch(0.985 0 0);
+-  --secondary: oklch(0.97 0 0);
+-  --secondary-foreground: oklch(0.205 0 0);
+-  --muted: oklch(0.97 0 0);
+-  --muted-foreground: oklch(0.556 0 0);
+-  --accent: oklch(0.97 0 0);
+-  --accent-foreground: oklch(0.205 0 0);
+-  --destructive: oklch(0.577 0.245 27.325);
+-  --border: oklch(0.922 0 0);
+-  --input: oklch(0.922 0 0);
+-  --ring: oklch(0.708 0 0);
++  --yeyu-paper: #f4f3ee;
++  --yeyu-paper-strong: #fffdf8;
++  --yeyu-ink: #17211f;
++  --yeyu-muted: #53635f;
++  --yeyu-teal: #197c72;
++  --yeyu-mint: #ddede7;
++  --yeyu-amber: #b45309;
++  --yeyu-line: #cbd8d3;
++  --background: var(--yeyu-paper);
++  --foreground: var(--yeyu-ink);
++  --card: var(--yeyu-paper-strong);
++  --card-foreground: var(--yeyu-ink);
++  --popover: var(--yeyu-paper-strong);
++  --popover-foreground: var(--yeyu-ink);
++  --primary: var(--yeyu-teal);
++  --primary-foreground: #ffffff;
++  --secondary: var(--yeyu-mint);
++  --secondary-foreground: var(--yeyu-ink);
++  --muted: #e8eee9;
++  --muted-foreground: var(--yeyu-muted);
++  --accent: #e6f0ec;
++  --accent-foreground: var(--yeyu-ink);
++  --destructive: #b42318;
++  --border: var(--yeyu-line);
++  --input: var(--yeyu-line);
++  --ring: var(--yeyu-teal);
+   --chart-1: oklch(0.646 0.222 41.116);
+   --chart-2: oklch(0.6 0.118 184.704);
+   --chart-3: oklch(0.398 0.07 227.392);
+   --chart-4: oklch(0.828 0.189 84.429);
+   --chart-5: oklch(0.769 0.188 70.08);
+   --sidebar: oklch(0.985 0 0);
+   --sidebar-foreground: oklch(0.145 0 0);
+   --sidebar-primary: oklch(0.5982 0.10687 182.4689);
+   --sidebar-primary-foreground: oklch(0.985 0 0);
+   --sidebar-accent: oklch(0.97 0 0);
+@@ -107,18 +115,474 @@
+   --sidebar-accent: oklch(0.269 0 0);
+   --sidebar-accent-foreground: oklch(0.985 0 0);
+   --sidebar-border: oklch(1 0 0 / 10%);
+   --sidebar-ring: oklch(0.556 0 0);
+ }
+ 
+ @layer base {
+   * {
+     @apply border-border outline-ring/50;
+   }
++
+   body {
+     @apply bg-background text-foreground;
++    min-width: 320px;
++    overflow-x: hidden;
++    font-family:
++      ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
++      "Microsoft YaHei", sans-serif;
+   }
++
+   button,
+   [role="button"] {
+     cursor: pointer;
+   }
++
++  :where(a, button, input, select, textarea):focus-visible {
++    outline: 3px solid var(--yeyu-teal);
++    outline-offset: 3px;
++  }
++}
++
++.public-site {
++  --background: var(--yeyu-paper);
++  --foreground: var(--yeyu-ink);
++  --card: var(--yeyu-paper-strong);
++  --card-foreground: var(--yeyu-ink);
++  --popover: var(--yeyu-paper-strong);
++  --popover-foreground: var(--yeyu-ink);
++  --primary: var(--yeyu-teal);
++  --primary-foreground: #ffffff;
++  --secondary: var(--yeyu-mint);
++  --secondary-foreground: var(--yeyu-ink);
++  --muted: #e8eee9;
++  --muted-foreground: var(--yeyu-muted);
++  --accent: #e6f0ec;
++  --accent-foreground: var(--yeyu-ink);
++  --border: var(--yeyu-line);
++  --input: var(--yeyu-line);
++  --ring: var(--yeyu-teal);
++  background: var(--yeyu-paper);
++  color: var(--yeyu-ink);
++  color-scheme: light;
++}
++
++.public-container {
++  width: min(calc(100% - 2rem), 72rem);
++  margin-inline: auto;
++}
++
++.public-header {
++  position: relative;
++  z-index: 20;
++  border-bottom: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper);
++}
++
++.public-header-inner {
++  display: flex;
++  min-height: 4.5rem;
++  align-items: center;
++  justify-content: space-between;
++  gap: 1rem;
++}
++
++.public-nav {
++  position: relative;
++  margin-left: auto;
++}
++
++.public-nav-link {
++  color: var(--yeyu-muted);
++  text-decoration: none;
++  transition:
++    background-color 160ms ease,
++    color 160ms ease;
++}
++
++.public-nav-link:hover {
++  background: var(--yeyu-mint);
++  color: var(--yeyu-ink);
++}
++
++.public-nav-link-primary {
++  background: var(--yeyu-teal);
++  color: #ffffff;
++}
++
++.public-nav-link-primary:hover {
++  background: #12665e;
++  color: #ffffff;
++}
++
++.public-menu-button {
++  display: inline-flex;
++  height: 2.5rem;
++  width: 2.5rem;
++  align-items: center;
++  justify-content: center;
++  border: 1px solid var(--yeyu-line);
++  border-radius: 0.375rem;
++  background: var(--yeyu-paper-strong);
++  color: var(--yeyu-ink);
++}
++
++.public-mobile-navigation {
++  position: absolute;
++  top: calc(100% + 0.75rem);
++  right: 0;
++  z-index: 30;
++  min-width: 14rem;
++  gap: 0.25rem;
++  padding: 0.5rem;
++  border: 1px solid var(--yeyu-line);
++  border-radius: 0.5rem;
++  background: var(--yeyu-paper-strong);
++  box-shadow: 0 12px 30px rgb(23 33 31 / 12%);
++}
++
++.public-mobile-navigation > * {
++  display: block;
++  width: 100%;
++}
++
++.public-hero {
++  display: grid;
++  gap: 2rem;
++  padding-block: clamp(3.5rem, 9vw, 7rem);
++}
++
++.public-hero-copy {
++  max-width: 48rem;
++}
++
++.public-eyebrow {
++  margin: 0;
++  color: var(--yeyu-teal);
++  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
++  font-size: 0.75rem;
++  font-weight: 700;
++  letter-spacing: 0.16em;
++  line-height: 1.5;
++  text-transform: uppercase;
++}
++
++.public-hero-title {
++  max-width: 13ch;
++  margin-top: 1rem;
++  color: var(--yeyu-ink);
++  font-size: clamp(2.5rem, 7vw, 5.5rem);
++  font-weight: 700;
++  letter-spacing: -0.055em;
++  line-height: 0.98;
++}
++
++.public-hero-lede {
++  max-width: 42rem;
++  margin-top: 1.5rem;
++  color: var(--yeyu-muted);
++  font-size: clamp(1rem, 2vw, 1.2rem);
++  line-height: 1.8;
++}
++
++.public-search-form {
++  display: flex;
++  max-width: 44rem;
++  flex-wrap: wrap;
++  gap: 0.75rem;
++  margin-top: 2rem;
++}
++
++.public-search-input {
++  min-width: 0;
++  flex: 1 1 16rem;
++  height: 3rem;
++  border: 1px solid var(--yeyu-line);
++  border-radius: 0.375rem;
++  background: var(--yeyu-paper-strong);
++  padding-inline: 1rem;
++  color: var(--yeyu-ink);
++}
++
++.public-search-input::placeholder {
++  color: var(--yeyu-muted);
++  opacity: 0.8;
++}
++
++.public-primary-button {
++  display: inline-flex;
++  min-height: 3rem;
++  align-items: center;
++  justify-content: center;
++  gap: 0.5rem;
++  border: 0;
++  border-radius: 0.375rem;
++  background: var(--yeyu-teal);
++  padding: 0.75rem 1.1rem;
++  color: #ffffff;
++  font-size: 0.9rem;
++  font-weight: 700;
++  text-decoration: none;
++  transition:
++    background-color 160ms ease,
++    transform 160ms ease;
++}
++
++.public-primary-button:hover {
++  background: #12665e;
++  transform: translateY(-1px);
++}
++
++.public-hero-links {
++  display: flex;
++  flex-wrap: wrap;
++  gap: 1.25rem;
++  margin-top: 1.25rem;
++}
++
++.public-text-link,
++.public-footer-link {
++  color: var(--yeyu-teal);
++  font-size: 0.9rem;
++  font-weight: 700;
++  text-underline-offset: 0.25rem;
++}
++
++.public-text-link:hover,
++.public-footer-link:hover {
++  text-decoration: underline;
++}
++
++.public-boundary-note {
++  align-self: end;
++  max-width: 28rem;
++  padding: 1.5rem;
++  border-left: 4px solid var(--yeyu-amber);
++  background: var(--yeyu-mint);
++}
++
++.public-note-title {
++  margin-top: 0.75rem;
++  color: var(--yeyu-ink);
++  font-size: 1.5rem;
++  font-weight: 700;
++  letter-spacing: -0.02em;
++}
++
++.public-note-copy,
++.public-section-copy {
++  margin-top: 0.75rem;
++  color: var(--yeyu-muted);
++  line-height: 1.75;
++}
++
++.public-note-rule {
++  height: 1px;
++  margin-block: 1.25rem;
++  background: var(--yeyu-line);
++}
++
++.public-note-label {
++  color: var(--yeyu-muted);
++  font-size: 0.75rem;
++  font-weight: 700;
++  letter-spacing: 0.12em;
++  text-transform: uppercase;
++}
++
++.public-code-chip,
++.public-path-line,
++.public-path-line code {
++  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
++}
++
++.public-code-chip {
++  display: inline-block;
++  margin-top: 0.5rem;
++  padding: 0.35rem 0.5rem;
++  border: 1px solid var(--yeyu-line);
++  border-radius: 0.25rem;
++  background: var(--yeyu-paper-strong);
++  color: var(--yeyu-ink);
++  font-size: 0.85rem;
++}
++
++.public-section {
++  padding-block: clamp(3rem, 7vw, 5.5rem);
++  border-top: 1px solid var(--yeyu-line);
++}
++
++.public-section-heading {
++  display: flex;
++  align-items: end;
++  justify-content: space-between;
++  gap: 1.5rem;
++}
++
++.public-section-title {
++  margin-top: 0.75rem;
++  color: var(--yeyu-ink);
++  font-size: clamp(1.75rem, 4vw, 3rem);
++  font-weight: 700;
++  letter-spacing: -0.04em;
++  line-height: 1.05;
++}
++
++.public-catalog-list {
++  display: grid;
++  gap: 0.75rem;
++  margin-top: 2rem;
++  padding: 0;
++  list-style: none;
++}
++
++.public-catalog-row {
++  display: grid;
++  grid-template-columns: minmax(12rem, 0.8fr) minmax(0, 1.6fr) auto;
++  gap: 1rem;
++  align-items: center;
++  padding: 1rem;
++  border: 1px solid var(--yeyu-line);
++  border-radius: 0.375rem;
++  background: var(--yeyu-paper-strong);
++}
++
++.public-path-line {
++  display: flex;
++  min-width: 0;
++  align-items: center;
++  gap: 0.65rem;
++  color: var(--yeyu-ink);
++  font-size: 0.85rem;
++  overflow-x: auto;
++  white-space: nowrap;
++}
++
++.public-method-badge {
++  flex: 0 0 auto;
++  color: var(--yeyu-teal);
++  font-size: 0.72rem;
++  font-weight: 800;
++  letter-spacing: 0.08em;
++}
++
++.public-catalog-meta {
++  display: flex;
++  flex-wrap: wrap;
++  justify-content: flex-end;
++  gap: 0.5rem 0.75rem;
++  color: var(--yeyu-muted);
++  font-size: 0.78rem;
++  text-align: right;
++}
++
++.public-state {
++  margin-top: 2rem;
++  padding: 1.25rem;
++  border: 1px dashed var(--yeyu-line);
++  border-radius: 0.375rem;
++  background: var(--yeyu-paper-strong);
++  color: var(--yeyu-muted);
++  line-height: 1.7;
++}
++
++.public-state-error {
++  display: flex;
++  align-items: center;
++  justify-content: space-between;
++  gap: 1rem;
++  border-color: var(--yeyu-amber);
++}
++
++.public-inline-button {
++  flex: 0 0 auto;
++  color: var(--yeyu-teal);
++  font-weight: 700;
++  text-decoration: underline;
++  text-underline-offset: 0.25rem;
++}
++
++.public-usage-section {
++  display: grid;
++  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
++  gap: 2rem;
++}
++
++.public-usage-grid {
++  display: grid;
++  gap: 1rem;
++  color: var(--yeyu-muted);
++  line-height: 1.75;
++}
++
++.public-usage-grid p {
++  padding-left: 1rem;
++  border-left: 2px solid var(--yeyu-teal);
++}
++
++.public-bottom-cta {
++  display: flex;
++  align-items: center;
++  justify-content: space-between;
++  gap: 1rem;
++  padding-block: 2rem 4rem;
++  color: var(--yeyu-ink);
++  font-weight: 700;
++}
++
++.public-footer {
++  border-top: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper-strong);
++}
++
++.public-footer-link {
++  color: var(--yeyu-muted);
++  font-weight: 600;
++}
++
++.logo-mark {
++  display: inline-flex;
++  height: 1.75rem;
++  width: 1.75rem;
++  align-items: center;
++  justify-content: center;
++  border-radius: 0.25rem;
++  background: var(--yeyu-teal);
++  color: #ffffff;
++  font-size: 0.85em;
++  font-weight: 800;
++}
++
++@media (min-width: 768px) {
++  .public-hero {
++    grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.65fr);
++    align-items: end;
++  }
++}
++
++@media (max-width: 767px) {
++  .public-section-heading,
++  .public-bottom-cta {
++    align-items: flex-start;
++    flex-direction: column;
++  }
++
++  .public-catalog-row,
++  .public-usage-section {
++    grid-template-columns: 1fr;
++  }
++
++  .public-catalog-meta {
++    justify-content: flex-start;
++    text-align: left;
++  }
++}
++
++@media (prefers-reduced-motion: reduce) {
++  *,
++  *::before,
++  *::after {
++    scroll-behavior: auto;
++    transition: none;
++    animation: none;
++  }
+ }
+diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
+index 7bafdf7..9d9f7c3 100644
+--- a/frontend/src/routes/_layout.tsx
++++ b/frontend/src/routes/_layout.tsx
+@@ -19,22 +19,25 @@ export const Route = createFileRoute("/_layout")({
+     }
+   },
+ })
+ 
+ function Layout() {
+   return (
+     <SidebarProvider>
+       <AppSidebar />
+       <SidebarInset>
+         <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
+-          <SidebarTrigger className="-ml-1 text-muted-foreground" />
++          <SidebarTrigger
++            className="-ml-1 text-muted-foreground"
++            aria-label="切换侧边栏"
++          />
+         </header>
+-        <main className="flex-1 p-6 md:p-8">
++        <main id="main-content" className="flex-1 p-6 md:p-8">
+           <div className="mx-auto max-w-7xl">
+             <Outlet />
+           </div>
+         </main>
+         <Footer />
+       </SidebarInset>
+     </SidebarProvider>
+   )
+ }
+diff --git a/frontend/src/routes/_layout/dashboard.tsx b/frontend/src/routes/_layout/dashboard.tsx
+new file mode 100644
+index 0000000..436dd2b
+--- /dev/null
++++ b/frontend/src/routes/_layout/dashboard.tsx
+@@ -0,0 +1,34 @@
++import { createFileRoute } from "@tanstack/react-router"
++
++import useAuth from "@/hooks/useAuth"
++
++export const Route = createFileRoute("/_layout/dashboard")({
++  component: Dashboard,
++  head: () => ({
++    meta: [
++      {
++        title: "Yeyu API 控制台",
++      },
++    ],
++  }),
++})
++
++function Dashboard() {
++  const { user: currentUser } = useAuth()
++  const displayName = currentUser?.full_name || currentUser?.email || "开发者"
++
++  return (
++    <section className="flex flex-col gap-3" data-testid="dashboard-page">
++      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
++        Yeyu API / 控制台
++      </p>
++      <h1 className="max-w-2xl truncate text-3xl font-semibold tracking-tight">
++        Yeyu API 控制台
++      </h1>
++      <p className="text-lg text-muted-foreground">你好，{displayName}。</p>
++      <p className="max-w-2xl text-muted-foreground">
++        在这里管理你的账户、API Key 和调用设置。公共目录仍然可以从站点首页查看。
++      </p>
++    </section>
++  )
++}
+diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
+deleted file mode 100644
+index 3e640cb..0000000
+--- a/frontend/src/routes/_layout/index.tsx
++++ /dev/null
+@@ -1,31 +0,0 @@
+-import { createFileRoute } from "@tanstack/react-router"
+-
+-import useAuth from "@/hooks/useAuth"
+-
+-export const Route = createFileRoute("/_layout/")({
+-  component: Dashboard,
+-  head: () => ({
+-    meta: [
+-      {
+-        title: "Dashboard - FastAPI Template",
+-      },
+-    ],
+-  }),
+-})
+-
+-function Dashboard() {
+-  const { user: currentUser } = useAuth()
+-
+-  return (
+-    <div>
+-      <div>
+-        <h1 className="text-2xl truncate max-w-sm">
+-          Hi, {currentUser?.full_name || currentUser?.email} 👋
+-        </h1>
+-        <p className="text-muted-foreground">
+-          Welcome back, nice to see you again!!!
+-        </p>
+-      </div>
+-    </div>
+-  )
+-}
+diff --git a/frontend/src/routes/index.tsx b/frontend/src/routes/index.tsx
+new file mode 100644
+index 0000000..ae23cfe
+--- /dev/null
++++ b/frontend/src/routes/index.tsx
+@@ -0,0 +1,212 @@
++import { useQuery } from "@tanstack/react-query"
++import { createFileRoute, Link } from "@tanstack/react-router"
++
++import { CatalogService } from "@/client"
++import PublicLayout from "@/components/PublicSite/PublicLayout"
++
++export const Route = createFileRoute("/")({
++  component: PublicHome,
++  head: () => ({
++    meta: [
++      {
++        title: "Yeyu API 公益工具箱",
++      },
++    ],
++  }),
++})
++
++function formatUpdatedAt(value?: string | null) {
++  if (!value) return "更新时间待补充"
++
++  const timestamp = Date.parse(value)
++  if (Number.isNaN(timestamp)) return value
++
++  return new Intl.DateTimeFormat("zh-HK", {
++    dateStyle: "medium",
++  }).format(new Date(timestamp))
++}
++
++function CatalogPreview() {
++  const catalogQuery = useQuery({
++    queryKey: ["public-catalog-preview"],
++    queryFn: async () => {
++      const response = await CatalogService.searchCatalog({
++        query: {
++          page: 1,
++          page_size: 4,
++        },
++      })
++      return response.data
++    },
++  })
++
++  const items = catalogQuery.data?.data ?? []
++
++  return (
++    <section
++      id="catalog"
++      className="public-section public-catalog-section"
++      aria-labelledby="catalog-heading"
++    >
++      <div className="public-section-heading">
++        <div>
++          <p className="public-eyebrow">目录入口</p>
++          <h2 id="catalog-heading" className="public-section-title">
++            从真实目录开始
++          </h2>
++          <p className="public-section-copy">
++            这里展示后端公开目录中的接口，不展示虚构卡片或调用统计。
++          </p>
++        </div>
++        <a className="public-text-link" href="/catalog">
++          搜索完整目录 <span aria-hidden="true">→</span>
++        </a>
++      </div>
++
++      {catalogQuery.isPending ? (
++        <p className="public-state" role="status">
++          正在读取真实目录……
++        </p>
++      ) : null}
++
++      {catalogQuery.isError ? (
++        <div className="public-state public-state-error" role="alert">
++          <p>目录暂时无法读取，请稍后重试。</p>
++          <button
++            type="button"
++            className="public-inline-button"
++            onClick={() => void catalogQuery.refetch()}
++          >
++            重试
++          </button>
++        </div>
++      ) : null}
++
++      {!catalogQuery.isPending &&
++      !catalogQuery.isError &&
++      items.length === 0 ? (
++        <p className="public-state">当前没有可公开的接口，请稍后再来查看。</p>
++      ) : null}
++
++      {!catalogQuery.isPending && !catalogQuery.isError && items.length > 0 ? (
++        <ul className="public-catalog-list" data-testid="catalog-preview-list">
++          {items.map((item) => (
++            <li key={item.slug} className="public-catalog-row">
++              <div className="public-path-line">
++                <span className="public-method-badge">{item.method}</span>
++                <code>{item.path}</code>
++              </div>
++              <div className="min-w-0">
++                <h3 className="truncate text-base font-semibold text-[var(--yeyu-ink)]">
++                  {item.name}
++                </h3>
++                <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
++                  {item.summary}
++                </p>
++              </div>
++              <div className="public-catalog-meta">
++                <span>{item.category}</span>
++                <time dateTime={item.updated_at ?? undefined}>
++                  {formatUpdatedAt(item.updated_at)}
++                </time>
++              </div>
++            </li>
++          ))}
++        </ul>
++      ) : null}
++    </section>
++  )
++}
++
++function PublicHome() {
++  return (
++    <PublicLayout>
++      <div className="public-container">
++        <section className="public-hero" aria-labelledby="home-heading">
++          <div className="public-hero-copy">
++            <p className="public-eyebrow">YEYU API / 公益工具箱</p>
++            <h1 id="home-heading" className="public-hero-title">
++              给学生和个人开发者的免费 API 工具箱
++            </h1>
++            <p className="public-hero-lede">
++              从清楚的接口文档开始，按公开规范调用稳定、可核验的自营工具。
++            </p>
++            <form className="public-search-form" action="/catalog" method="get">
++              <label className="sr-only" htmlFor="catalog-query">
++                搜索 API 目录
++              </label>
++              <input
++                id="catalog-query"
++                name="query"
++                className="public-search-input"
++                placeholder="搜索时间戳、UUID、天气……"
++                type="search"
++              />
++              <button className="public-primary-button" type="submit">
++                搜索 API 目录
++              </button>
++            </form>
++            <nav className="public-hero-links" aria-label="快速入口">
++              <a className="public-text-link" href="/catalog">
++                浏览公开目录 <span aria-hidden="true">↗</span>
++              </a>
++              <a className="public-text-link" href="#usage">
++                阅读使用规范 <span aria-hidden="true">↓</span>
++              </a>
++            </nav>
++          </div>
++
++          <aside
++            className="public-boundary-note"
++            aria-labelledby="boundary-heading"
++          >
++            <p className="public-eyebrow">调用边界</p>
++            <h2 id="boundary-heading" className="public-note-title">
++              先看清楚，再开始调用
++            </h2>
++            <p className="public-note-copy">
++              公共页面只负责发现和阅读目录。真正的工具调用需要独立 API
++              Key，浏览器登录状态不会替代它。
++            </p>
++            <div className="public-note-rule" aria-hidden="true" />
++            <p className="public-note-label">示例凭据</p>
++            <code className="public-code-chip">&lt;YOUR_API_KEY&gt;</code>
++          </aside>
++        </section>
++
++        <CatalogPreview />
++
++        <section
++          id="usage"
++          className="public-section public-usage-section"
++          aria-labelledby="usage-heading"
++        >
++          <div>
++            <p className="public-eyebrow">使用规范</p>
++            <h2 id="usage-heading" className="public-section-title">
++              公益服务也需要清楚的边界
++            </h2>
++          </div>
++          <div className="public-usage-grid">
++            <p>
++              只调用目录中公开、已发布的接口；参数、缓存和来源以对应文档为准。
++            </p>
++            <p>
++              请保管好自己的 API Key，不要把密钥提交到代码仓库或分享给他人。
++            </p>
++            <p>
++              发现异常或文档问题时，请停止重试并通过项目渠道反馈，给公共资源留下余量。
++            </p>
++          </div>
++        </section>
++
++        <div className="public-bottom-cta">
++          <p>准备好查找一个清楚、可用的接口了吗？</p>
++          <Link className="public-primary-button" to="/login">
++            登录并进入控制台
++          </Link>
++        </div>
++      </div>
++    </PublicLayout>
++  )
++}
+diff --git a/frontend/src/routes/login.tsx b/frontend/src/routes/login.tsx
+index 3f075c5..c2c02e2 100644
+--- a/frontend/src/routes/login.tsx
++++ b/frontend/src/routes/login.tsx
+@@ -39,45 +39,45 @@ type FormData = z.infer<typeof formSchema>
+ const searchSchema = z.object({
+   oauth: z.enum(["github"]).optional(),
+ })
+ 
+ export const Route = createFileRoute("/login")({
+   component: Login,
+   validateSearch: searchSchema,
+   beforeLoad: async ({ search }) => {
+     if (isLoggedIn() && search.oauth !== "github") {
+       throw redirect({
+-        to: "/",
++        to: "/dashboard",
+       })
+     }
+   },
+   head: () => ({
+     meta: [
+       {
+-        title: "Log In - FastAPI Template",
++        title: "登录 - Yeyu API",
+       },
+     ],
+   }),
+ })
+ 
+ function Login() {
+   const { loginMutation } = useAuth()
+   const navigate = Route.useNavigate()
+   const search = Route.useSearch()
+   const [oauthError, setOauthError] = useState<string | null>(null)
+ 
+   useEffect(() => {
+     if (search.oauth !== "github") return
+     UsersService.readUserMe()
+       .then(() => {
+         localStorage.setItem("session_authenticated", "1")
+-        void navigate({ to: "/" })
++        void navigate({ to: "/dashboard" })
+       })
+       .catch(() => {
+         localStorage.removeItem("session_authenticated")
+         setOauthError("GitHub 登录未完成，请先验证邮箱后再绑定 GitHub。")
+       })
+   }, [navigate, search.oauth])
+   const form = useForm<FormData>({
+     resolver: zodResolver(formSchema),
+     mode: "onBlur",
+     criteriaMode: "all",
+diff --git a/frontend/tests/login.spec.ts b/frontend/tests/login.spec.ts
+index 8072ddc..b399e9d 100644
+--- a/frontend/tests/login.spec.ts
++++ b/frontend/tests/login.spec.ts
+@@ -36,24 +36,24 @@ test("Forgot Password link is visible", async ({ page }) => {
+     page.getByRole("link", { name: "Forgot your password?" }),
+   ).toBeVisible()
+ })
+ 
+ test("Log in with valid email and password ", async ({ page }) => {
+   await page.goto("/login")
+ 
+   await fillForm(page, firstSuperuser, firstSuperuserPassword)
+   await page.getByRole("button", { name: "Log In" }).click()
+ 
+-  await page.waitForURL("/")
++  await page.waitForURL("/dashboard")
+ 
+   await expect(
+-    page.getByText("Welcome back, nice to see you again!"),
++    page.getByRole("heading", { name: "Yeyu API 控制台" }),
+   ).toBeVisible()
+ })
+ 
+ test("Log in with invalid email", async ({ page }) => {
+   await page.goto("/login")
+ 
+   await fillForm(page, "invalidemail", firstSuperuserPassword)
+   await page.getByRole("button", { name: "Log In" }).click()
+ 
+   await expect(page.getByText("Invalid email address")).toBeVisible()
+@@ -68,24 +68,24 @@ test("Log in with invalid password", async ({ page }) => {
+ 
+   await expect(page.getByText("Incorrect email or password")).toBeVisible()
+ })
+ 
+ test("Successful log out", async ({ page }) => {
+   await page.goto("/login")
+ 
+   await fillForm(page, firstSuperuser, firstSuperuserPassword)
+   await page.getByRole("button", { name: "Log In" }).click()
+ 
+-  await page.waitForURL("/")
++  await page.waitForURL("/dashboard")
+ 
+   await expect(
+-    page.getByText("Welcome back, nice to see you again!"),
++    page.getByRole("heading", { name: "Yeyu API 控制台" }),
+   ).toBeVisible()
+ 
+   await page.getByTestId("user-menu").click()
+   await page.getByRole("menuitem", { name: "Log out" }).click()
+   await page.waitForURL("/login")
+ })
+ 
+ test("Logged-out user cannot access protected routes", async ({ page }) => {
+   await page.goto("/login")
+ 
+@@ -99,19 +99,40 @@ test("Logged-out user cannot access protected routes", async ({ page }) => {
+   ).toBeVisible()
+ 
+   await page.getByTestId("user-menu").click()
+   await page.getByRole("menuitem", { name: "Log out" }).click()
+   await page.waitForURL("/login")
+ 
+   await page.goto("/settings")
+   await page.waitForURL("/login")
+ })
+ 
++test("Anonymous users are redirected to login from items", async ({ page }) => {
++  await page.goto("/items")
++
++  await page.waitForURL("/login")
++  await expect(page).toHaveURL("/login")
++})
++
++test("Logged-in users are redirected from login to dashboard", async ({
++  page,
++}) => {
++  await page.goto("/login")
++
++  await fillForm(page, firstSuperuser, firstSuperuserPassword)
++  await page.getByRole("button", { name: "Log In" }).click()
++  await page.waitForURL("/dashboard")
++
++  await page.goto("/login")
++  await page.waitForURL("/dashboard")
++  await expect(page).toHaveURL("/dashboard")
++})
++
+ test("Redirects to /login when token is wrong", async ({ page }) => {
+   await page.goto("/settings")
+   await page.evaluate(() => {
+     localStorage.setItem("access_token", "invalid_token")
+   })
+   await page.goto("/settings")
+   await page.waitForURL("/login")
+   await expect(page).toHaveURL("/login")
+ })
+diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
+new file mode 100644
+index 0000000..1c5789d
+--- /dev/null
++++ b/frontend/tests/public-catalog.spec.ts
+@@ -0,0 +1,39 @@
++import { expect, test } from "@playwright/test"
++
++test.use({ storageState: { cookies: [], origins: [] } })
++
++test("Anonymous users can open the public home without login redirect", async ({
++  page,
++}) => {
++  await page.goto("/")
++
++  await expect(page).toHaveURL(/\/$/)
++  await expect(
++    page.getByRole("heading", {
++      name: "给学生和个人开发者的免费 API 工具箱",
++    }),
++  ).toBeVisible()
++  await expect(page).not.toHaveURL(/\/login/)
++})
++
++test("Anonymous users can open the catalog entry without login redirect", async ({
++  page,
++}) => {
++  await page.goto("/catalog")
++
++  await expect(page).not.toHaveURL(/\/login/)
++})
++
++test("Public navigation exposes keyboard-accessible catalog and login links", async ({
++  page,
++}) => {
++  await page.setViewportSize({ width: 390, height: 844 })
++  await page.goto("/")
++
++  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
++  await expect(page.getByRole("link", { name: "API 目录" })).toBeVisible()
++  await expect(page.getByRole("link", { name: "登录" })).toBeVisible()
++
++  await page.getByRole("link", { name: "登录" }).focus()
++  await expect(page.getByRole("link", { name: "登录" })).toBeFocused()
++})
+diff --git a/plans/agent-reports/task-7-2-report.md b/plans/agent-reports/task-7-2-report.md
+new file mode 100644
+index 0000000..c795cbd
+--- /dev/null
++++ b/plans/agent-reports/task-7-2-report.md
+@@ -0,0 +1,106 @@
++# Task 7-2 实现报告：拆分公共和受保护的前端路由壳层
++
++## 范围与结果
++
++- 基线：`e125ac2`（任务 1 的 `feb0136` 已在历史中）。
++- 已实现公共首页 `/`，使用生成的 `CatalogService.searchCatalog` 读取真实目录；加载、错误、空结果和搜索入口均有明确状态，不硬编码接口卡片或统计。
++- 已实现 `PublicLayout`、`PublicHeader`、`PublicFooter`，包含首页、API 目录、使用规范、登录/控制台入口，以及移动端可折叠且可键盘访问的导航。
++- 已将受保护首页迁移为 `/dashboard`，保留 `_layout.tsx` 的认证 `beforeLoad`，并保留当前用户欢迎信息。
++- 已统一密码登录成功、GitHub callback 成功和已登录访问 `/login` 的目标为 `/dashboard`；登出仍跳转 `/login`。
++- 已更新侧边栏 Dashboard、Logo、Footer 和本地 CSS 变量，移除已使用组件中的 FastAPI Template 品牌链接与文案。
++- 未手改 `frontend/src/routeTree.gen.ts`；该文件仍需要 TanStack Router/Vite 生成。
++- 未实现任务 3 的完整 `/catalog` 目录页、筛选、详情页或代码示例页。
++
++## 修改文件
++
++实现文件：
++
++- `frontend/src/routes/index.tsx`
++- `frontend/src/routes/_layout/dashboard.tsx`
++- `frontend/src/routes/_layout.tsx`
++- 删除 `frontend/src/routes/_layout/index.tsx`
++- `frontend/src/components/PublicSite/PublicLayout.tsx`
++- `frontend/src/components/PublicSite/PublicHeader.tsx`
++- `frontend/src/components/PublicSite/PublicFooter.tsx`
++- `frontend/src/hooks/useAuth.ts`
++- `frontend/src/routes/login.tsx`
++- `frontend/src/components/Sidebar/AppSidebar.tsx`
++- `frontend/src/components/Common/Logo.tsx`
++- `frontend/src/components/Common/Footer.tsx`
++- `frontend/src/index.css`
++
++测试文件：
++
++- `frontend/tests/login.spec.ts`
++- `frontend/tests/public-catalog.spec.ts`
++
++未修改：
++
++- `frontend/src/routeTree.gen.ts`（按任务要求不手改）
++- `E:\AI_projects\yeyubakahome_Web`、线上服务、DNS、Nginx、服务器和凭据。
++
++## TDD RED/GREEN 证据
++
++### RED
++
++命令：
++
++```powershell
++Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
++pnpm exec playwright test tests/public-catalog.spec.ts tests/login.spec.ts
++```
++
++真实结果：退出码 `1`。测试收集阶段报错：`Environment variable FIRST_SUPERUSER is undefined`，未进入浏览器测试。
++
++为排除测试账号收集阻塞，仅使用进程级非真实占位值重试公共边界：
++
++```powershell
++$env:FIRST_SUPERUSER='red@example.com'
++$env:FIRST_SUPERUSER_PASSWORD='not-a-real-password'
++pnpm exec playwright test tests/public-catalog.spec.ts
++```
++
++真实结果：退出码 `1`。Playwright setup 阶段报错：
++`Executable doesn't exist at C:\Users\21239\AppData\Local\ms-playwright\chromium_headless_shell-1234\chrome-headless-shell-win64\chrome-headless-shell.exe`。
++该测试进程随后已停止；未将未执行的浏览器断言标记为通过。
++
++### GREEN / 静态检查
++
++Biome 修复格式和静态问题后执行：
++
++```powershell
++Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
++pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
++```
++
++真实结果：退出码 `0`，`Checked 63 files in 31ms. No fixes applied.`
++
++Playwright GREEN：未运行。由于 Chromium 可执行文件缺失，且用户要求本次不再运行浏览器或长时间命令，保持为未验证。
++
++## 其他验证与阻塞
++
++1. `pnpm build` 已执行，退出码 `2`。TypeScript 报告 `/dashboard` 和新的公共 `/` 不在旧 `routeTree.gen.ts` 类型中；构建脚本先执行 `tsc`、后执行 Vite 路由生成，因此未进入 Vite 阶段。
++2. 为使用官方 Vite/TanStack 生成链刷新路由树，执行 `pnpm exec vite build`，退出码 `1`。Vite 配置加载失败：`Failed to load native binding`；缺少 `./swc.win32-x64-msvc.node`，并报告 `ERR_SWC_NATIVE_CACHE` 及 SWC 缓存目录 DACL 权限问题。未手工写入生成路由树。
++3. Docker、数据库、SMTP、GitHub OAuth、DNS、Nginx 和线上服务验收本任务未运行，均未验证。
++
++## Self-review
++
++- 路由边界：公共 `/` 不挂载受保护 `_layout`；`/items`、`/settings`、`/admin` 仍挂载认证 layout；`/dashboard` 使用同一认证门禁。
++- 跳转边界：密码登录、GitHub callback、已登录访问 `/login` 和侧栏 Dashboard 均指向 `/dashboard`；登出仍清理本地认证标记并前往 `/login`。
++- 数据边界：首页只调用公开 `CatalogService.searchCatalog`，不伪造数据、统计、上游 URL 或 API Key；示例凭据仅为 `<YOUR_API_KEY>`。
++- 可访问性：公共页面使用 `header`、`nav`、`main`、`footer`、表单标签、`role=status`、`role=alert` 和可见 `:focus-visible` 焦点环；移动菜单使用 `aria-expanded`、`aria-controls` 和键盘可聚焦按钮。
++- 品牌边界：改动的 Logo/Footer/登录标题不再引用 FastAPI；未扩展修改任务简报之外的旧路由文件。
++- 独立只读子代理：当前会话未提供可调用的子代理工具，因此没有伪造独立审查结果；本报告仅记录主代理的只读 self-review。
++
++## 提交
++
++- 实现提交主题：`feat: split public and protected web shells`
++- 提交 SHA：`0acbfc3`。
++- 报告状态：本文件随实现提交写入；本次回填 SHA 后产生一个仅文档的收尾提交。
++
++## 未验证项
++
++- 真实 Chromium 浏览器中的匿名 `/`、`/catalog`、登录成功 `/dashboard`、登出和 `/items` 认证跳转。
++- TanStack Router 生成 `routeTree.gen.ts` 后的最终 TypeScript/build 结果。
++- 真实后端目录 API 返回项在浏览器中的展示。
++- 生产环境、Docker Compose、数据库、SMTP、GitHub OAuth、DNS、TLS、Nginx 和线上回归。
diff --git a/plans/agent-reports/task-7-2-fix-diff.md b/plans/agent-reports/task-7-2-fix-diff.md
new file mode 100644
index 0000000..e9747cb
--- /dev/null
+++ b/plans/agent-reports/task-7-2-fix-diff.md
@@ -0,0 +1,261 @@
+# Review package: 4c43285..e9efb91
+
+## Commits
+e9efb91 docs: record task 7-2 repair report
+673d806 fix: close public shell review findings
+
+## Files changed
+ frontend/package.json                  |  2 +-
+ frontend/src/routes/catalog/index.tsx  | 45 +++++++++++++++++++++++
+ frontend/tests/login.spec.ts           |  4 +--
+ frontend/tests/public-catalog.spec.ts  | 29 +++++++++++----
+ plans/agent-reports/task-7-2-report.md | 66 ++++++++++++++++++++++++++++++++++
+ 5 files changed, 136 insertions(+), 10 deletions(-)
+
+## Diff
+diff --git a/frontend/package.json b/frontend/package.json
+index 3a63aca..568862d 100644
+--- a/frontend/package.json
++++ b/frontend/package.json
+@@ -1,19 +1,19 @@
+ {
+   "name": "frontend",
+   "private": true,
+   "packageManager": "pnpm@10.28.2",
+   "version": "0.0.0",
+   "type": "module",
+   "scripts": {
+     "dev": "vite",
+-    "build": "tsc -p tsconfig.build.json && vite build",
++    "build": "vite build && tsc -p tsconfig.build.json",
+     "lint": "biome check --write --unsafe --no-errors-on-unmatched --files-ignore-unknown=true ./",
+     "preview": "vite preview",
+     "generate-client": "openapi-ts",
+     "test": "pnpm exec playwright test",
+     "test:ui": "pnpm exec playwright test --ui"
+   },
+   "dependencies": {
+     "@hookform/resolvers": "^5.7.1",
+     "@radix-ui/react-avatar": "^1.2.6",
+     "@radix-ui/react-checkbox": "^1.3.11",
+diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
+new file mode 100644
+index 0000000..a0084bb
+--- /dev/null
++++ b/frontend/src/routes/catalog/index.tsx
+@@ -0,0 +1,45 @@
++import { createFileRoute, Link } from "@tanstack/react-router"
++
++import PublicLayout from "@/components/PublicSite/PublicLayout"
++
++export const Route = createFileRoute("/catalog/")({
++  component: CatalogPlaceholder,
++  head: () => ({
++    meta: [
++      {
++        title: "API 目录 - Yeyu API",
++      },
++    ],
++  }),
++})
++
++function CatalogPlaceholder() {
++  return (
++    <PublicLayout>
++      <div className="public-container py-16 sm:py-24">
++        <section
++          className="public-state mx-auto max-w-2xl text-center"
++          aria-labelledby="catalog-placeholder-heading"
++          data-testid="catalog-placeholder"
++        >
++          <p className="public-eyebrow">公开目录</p>
++          <h1
++            id="catalog-placeholder-heading"
++            className="public-section-title mt-3"
++          >
++            API 目录建设中
++          </h1>
++          <p className="public-section-copy mx-auto mt-4 max-w-xl">
++            由公开目录驱动的真实接口条目将在下一阶段开放，当前先保留清晰的公共入口。
++          </p>
++          <p className="mt-3 text-sm text-[var(--yeyu-muted)]">
++            目录建设中，请稍后再来查看。
++          </p>
++          <Link to="/" className="public-primary-button mt-8 inline-flex">
++            返回首页
++          </Link>
++        </section>
++      </div>
++    </PublicLayout>
++  )
++}
+diff --git a/frontend/tests/login.spec.ts b/frontend/tests/login.spec.ts
+index b399e9d..05ef6ea 100644
+--- a/frontend/tests/login.spec.ts
++++ b/frontend/tests/login.spec.ts
+@@ -85,24 +85,24 @@ test("Successful log out", async ({ page }) => {
+   await page.getByRole("menuitem", { name: "Log out" }).click()
+   await page.waitForURL("/login")
+ })
+ 
+ test("Logged-out user cannot access protected routes", async ({ page }) => {
+   await page.goto("/login")
+ 
+   await fillForm(page, firstSuperuser, firstSuperuserPassword)
+   await page.getByRole("button", { name: "Log In" }).click()
+ 
+-  await page.waitForURL("/")
++  await page.waitForURL("/dashboard")
+ 
+   await expect(
+-    page.getByText("Welcome back, nice to see you again!"),
++    page.getByRole("heading", { name: "Yeyu API 控制台" }),
+   ).toBeVisible()
+ 
+   await page.getByTestId("user-menu").click()
+   await page.getByRole("menuitem", { name: "Log out" }).click()
+   await page.waitForURL("/login")
+ 
+   await page.goto("/settings")
+   await page.waitForURL("/login")
+ })
+ 
+diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
+index 1c5789d..ac5f343 100644
+--- a/frontend/tests/public-catalog.spec.ts
++++ b/frontend/tests/public-catalog.spec.ts
+@@ -9,31 +9,46 @@ test("Anonymous users can open the public home without login redirect", async ({
+ 
+   await expect(page).toHaveURL(/\/$/)
+   await expect(
+     page.getByRole("heading", {
+       name: "给学生和个人开发者的免费 API 工具箱",
+     }),
+   ).toBeVisible()
+   await expect(page).not.toHaveURL(/\/login/)
+ })
+ 
+-test("Anonymous users can open the catalog entry without login redirect", async ({
++test("Anonymous users can open the public catalog placeholder", async ({
+   page,
+ }) => {
+   await page.goto("/catalog")
+ 
+-  await expect(page).not.toHaveURL(/\/login/)
++  await expect(page).toHaveURL("/catalog")
++  await expect(
++    page.getByRole("heading", { name: "API 目录建设中" }),
++  ).toBeVisible()
++  await expect(page.getByText("由公开目录驱动")).toBeVisible()
++  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
+ })
+ 
+ test("Public navigation exposes keyboard-accessible catalog and login links", async ({
+   page,
+ }) => {
+   await page.setViewportSize({ width: 390, height: 844 })
+   await page.goto("/")
+ 
+-  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
+-  await expect(page.getByRole("link", { name: "API 目录" })).toBeVisible()
+-  await expect(page.getByRole("link", { name: "登录" })).toBeVisible()
++  const navigation = page.getByRole("navigation", { name: "公共导航" })
++  const menuButton = navigation.getByRole("button", { name: /菜单/ })
++
++  await expect(navigation).toBeVisible()
++  await expect(menuButton).toHaveAttribute("aria-expanded", "true")
++
++  await menuButton.press("Enter")
++  await expect(menuButton).toHaveAttribute("aria-expanded", "false")
++
++  await menuButton.press("Space")
++  await expect(menuButton).toHaveAttribute("aria-expanded", "true")
++  await expect(navigation.getByRole("link", { name: "API 目录" })).toBeVisible()
++  await expect(navigation.getByRole("link", { name: "登录" })).toBeVisible()
+ 
+-  await page.getByRole("link", { name: "登录" }).focus()
+-  await expect(page.getByRole("link", { name: "登录" })).toBeFocused()
++  await navigation.getByRole("link", { name: "登录" }).focus()
++  await expect(navigation.getByRole("link", { name: "登录" })).toBeFocused()
+ })
+diff --git a/plans/agent-reports/task-7-2-report.md b/plans/agent-reports/task-7-2-report.md
+index c795cbd..35c5158 100644
+--- a/plans/agent-reports/task-7-2-report.md
++++ b/plans/agent-reports/task-7-2-report.md
+@@ -97,10 +97,76 @@ Playwright GREEN：未运行。由于 Chromium 可执行文件缺失，且用户
+ - 实现提交主题：`feat: split public and protected web shells`
+ - 提交 SHA：`0acbfc3`。
+ - 报告状态：本文件随实现提交写入；本次回填 SHA 后产生一个仅文档的收尾提交。
+ 
+ ## 未验证项
+ 
+ - 真实 Chromium 浏览器中的匿名 `/`、`/catalog`、登录成功 `/dashboard`、登出和 `/items` 认证跳转。
+ - TanStack Router 生成 `routeTree.gen.ts` 后的最终 TypeScript/build 结果。
+ - 真实后端目录 API 返回项在浏览器中的展示。
+ - 生产环境、Docker Compose、数据库、SMTP、GitHub OAuth、DNS、TLS、Nginx 和线上回归。
++
++## Task 7-2 修复报告：关闭公共壳层审查问题
++
++### 修复文件
++
++- `frontend/package.json`：将 `build` 调整为 `vite build && tsc -p tsconfig.build.json`，先让 Vite/TanStack Router 官方插件生成路由树，再执行类型检查。
++- `frontend/tests/login.spec.ts`：将“Logged-out user cannot access protected routes”中的登录后断言改为 `/dashboard` 和 `Yeyu API 控制台`，保留退出后 `/settings` 跳转 `/login` 的断言。
++- `frontend/src/routes/catalog/index.tsx`：新增任务 2 范围内的最小公共目录占位路由，复用 `PublicLayout`，提供语义 `h1`、`API 目录建设中`、`由公开目录驱动` 文案和返回首页入口；没有接口卡片、统计或 API 请求。
++- `frontend/tests/public-catalog.spec.ts`：要求 `/catalog` 最终 URL、占位标题和公共导航可见；移动菜单使用键盘 `Enter`、`Space` 实际操作，并断言 `aria-expanded` 为 `true → false → true` 以及展开后的目录/登录链接可见。
++- 未修改 `frontend/src/routeTree.gen.ts`；未触碰旧项目、线上服务、服务器、DNS、Nginx 或真实凭据。
++
++### 审查问题对应改动
++
++1. Critical 构建阻塞：根因是原 `build` 在 Vite 路由生成前运行 `tsc`。已改为 Vite 官方生成链先执行，再运行 `tsc`；本机生成链仍受 SWC 原生绑定环境阻塞，未手写生成树。
++2. Important 登录测试：已等待 `/dashboard`，断言 `Yeyu API 控制台`，并保留登出后访问 `/settings` 必须回到 `/login`。
++3. Important 公共目录：已新增 `/catalog` 最小占位页，并将测试强化为最终 URL、占位标题和公共导航断言；任务 3 可继续扩展该文件。
++4. Important 移动菜单：已从仅 `focus()` 改为对 menu button 使用 `press("Enter")`、`press("Space")`，验证收起/展开状态和展开后的链接。
++
++### 验证命令与真实结果
++
++```text
++pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\package.json E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
++退出码：0
++输出：Checked 4 files in 6ms. No fixes applied.
++```
++
++```text
++git diff --check
++退出码：0；无空白错误（Git 仅提示 LF 将在后续写入时转换为 CRLF）。
++```
++
++```text
++pnpm build
++退出码：1
++输出关键原文：
++> frontend@0.0.0 build E:\AI_projects\YEYU-API\frontend
++> vite build && tsc -p tsconfig.build.json
++failed to load config from E:\AI_projects\YEYU-API\frontend\vite.config.ts
++Error: Failed to load native binding
++Error: Cannot find module './swc.win32-x64-msvc.node'
++Error: SWC native addon: validate cache root C:\Users\21239\AppData\Local\swc: ... DACL grants replacement rights ...
++code: 'ERR_SWC_NATIVE_CACHE'
++```
++
++```text
++pnpm rebuild @swc/core
++退出码：0，但 postinstall 真实输出仍为：
++@swc/core was not able to resolve native bindings installation. It'll try to use @swc/wasm as fallback instead.
++Error: ENOENT: no such file or directory, rename ...\@swc\core\npm-install\node_modules\@swc\wasm -> ...\node_modules\@swc\wasm
++Failed to install fallback @swc/wasm@1.16.12. @swc/core will not properly.
++```
++
++```text
++pnpm exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json
++退出码：1
++输出：旧 routeTree.gen.ts 类型集合中缺少 /dashboard、/catalog/ 和新的 /，对应 PublicHeader.tsx、useAuth.ts、_layout/dashboard.tsx、catalog/index.tsx、routes/index.tsx、login.tsx 报 TS2322/TS2345。
++```
++
++Playwright 未在本次修复中运行，遵循本次指令不运行长时间浏览器或全套测试；此前报告中的 Chromium 可执行文件缺失阻塞仍适用。
++
++### 阻塞结论与提交
++
++- 修复后的构建入口顺序已落地，但本机仍有阻塞：Vite/TanStack 官方生成链在加载配置时被 `@swc/core` 原生绑定缺失、`ERR_SWC_NATIVE_CACHE` 和 fallback `ENOENT` 阻断，因此本地未能生成新 `routeTree.gen.ts`，最终 `tsc` 不能通过。
++- 该阻塞已用真实命令和原始错误记录；没有手工编辑 `routeTree.gen.ts`，也没有把未运行的 Playwright 断言标记为通过。
++- 提交主题：`fix: close public shell review findings`
++- 提交 SHA：`673d806f955c54deb2284198babc33116b78d959`。
diff --git a/plans/agent-reports/task-7-2-fix-review.md b/plans/agent-reports/task-7-2-fix-review.md
new file mode 100644
index 0000000..4010abb
--- /dev/null
+++ b/plans/agent-reports/task-7-2-fix-review.md
@@ -0,0 +1,36 @@
+# Task 7-2 修复独立只读复审报告
+
+## Spec Compliance
+
+- ✅ 构建顺序已解决原 Critical（代码层面）：frontend/package.json:9 改为 vite build && tsc -p tsconfig.build.json；frontend/vite.config.ts:3,18-22 启用了 TanStack Router Vite 插件。routeTree.gen.ts 未被修改。
+- ✅ 登录断言已更新：frontend/tests/login.spec.ts:40-50,72-86,89-107,116-127 的登录后目标均为 /dashboard，旧根路径和旧欢迎文案已移除；/settings 退出后保护断言保留。
+- ✅ /catalog 公共占位路由真实存在：frontend/src/routes/catalog/index.tsx:5,18-43 使用公共壳层和唯一占位标题；测试在 frontend/tests/public-catalog.spec.ts:22-29 同时断言 /catalog、标题、占位文案和公共导航。
+- ✅ 移动菜单测试已实际操作键盘：frontend/tests/public-catalog.spec.ts:38-50 使用 Enter、Space，验证 aria-expanded 的 true 到 false 到 true 变化及展开后的目录、登录链接。
+- ✅ 占位页未加入目录 API、接口卡片或统计逻辑；增量仅涉及前端相关文件和报告，无凭据、旧项目或线上资源修改。
+- ⚠️ 修复报告中的 pnpm build 仍受 SWC 原生绑定、缓存 DACL 和 fallback 安装错误阻塞；Playwright 仍受 Chromium 缺失阻塞，因此最终浏览器运行时行为未验证。
+
+## Strengths
+
+- 原 Critical 的根因被准确修复：官方 Vite/TanStack 路由生成先于 tsc。
+- 测试断言从未跳转登录页提升为具体 URL、页面标题和公共壳层。
+- 修复范围克制，保留任务 3 扩展目录页的空间。
+
+## Issues
+
+### Critical (Must Fix)
+
+- 无。
+
+### Important (Should Fix)
+
+- 无。
+
+### Minor (Nice to Have)
+
+- 无。
+
+## Assessment
+
+**Task quality:** Approved
+
+**Reasoning:** 四项原审查问题均已在增量 diff 中闭环，build 顺序已正确解决原 Critical。实际构建与浏览器 E2E 仍受环境阻塞，但不构成此次修复本身的新缺陷。
diff --git a/plans/agent-reports/task-7-2-report.md b/plans/agent-reports/task-7-2-report.md
new file mode 100644
index 0000000..35c5158
--- /dev/null
+++ b/plans/agent-reports/task-7-2-report.md
@@ -0,0 +1,172 @@
+# Task 7-2 实现报告：拆分公共和受保护的前端路由壳层
+
+## 范围与结果
+
+- 基线：`e125ac2`（任务 1 的 `feb0136` 已在历史中）。
+- 已实现公共首页 `/`，使用生成的 `CatalogService.searchCatalog` 读取真实目录；加载、错误、空结果和搜索入口均有明确状态，不硬编码接口卡片或统计。
+- 已实现 `PublicLayout`、`PublicHeader`、`PublicFooter`，包含首页、API 目录、使用规范、登录/控制台入口，以及移动端可折叠且可键盘访问的导航。
+- 已将受保护首页迁移为 `/dashboard`，保留 `_layout.tsx` 的认证 `beforeLoad`，并保留当前用户欢迎信息。
+- 已统一密码登录成功、GitHub callback 成功和已登录访问 `/login` 的目标为 `/dashboard`；登出仍跳转 `/login`。
+- 已更新侧边栏 Dashboard、Logo、Footer 和本地 CSS 变量，移除已使用组件中的 FastAPI Template 品牌链接与文案。
+- 未手改 `frontend/src/routeTree.gen.ts`；该文件仍需要 TanStack Router/Vite 生成。
+- 未实现任务 3 的完整 `/catalog` 目录页、筛选、详情页或代码示例页。
+
+## 修改文件
+
+实现文件：
+
+- `frontend/src/routes/index.tsx`
+- `frontend/src/routes/_layout/dashboard.tsx`
+- `frontend/src/routes/_layout.tsx`
+- 删除 `frontend/src/routes/_layout/index.tsx`
+- `frontend/src/components/PublicSite/PublicLayout.tsx`
+- `frontend/src/components/PublicSite/PublicHeader.tsx`
+- `frontend/src/components/PublicSite/PublicFooter.tsx`
+- `frontend/src/hooks/useAuth.ts`
+- `frontend/src/routes/login.tsx`
+- `frontend/src/components/Sidebar/AppSidebar.tsx`
+- `frontend/src/components/Common/Logo.tsx`
+- `frontend/src/components/Common/Footer.tsx`
+- `frontend/src/index.css`
+
+测试文件：
+
+- `frontend/tests/login.spec.ts`
+- `frontend/tests/public-catalog.spec.ts`
+
+未修改：
+
+- `frontend/src/routeTree.gen.ts`（按任务要求不手改）
+- `E:\AI_projects\yeyubakahome_Web`、线上服务、DNS、Nginx、服务器和凭据。
+
+## TDD RED/GREEN 证据
+
+### RED
+
+命令：
+
+```powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec playwright test tests/public-catalog.spec.ts tests/login.spec.ts
+```
+
+真实结果：退出码 `1`。测试收集阶段报错：`Environment variable FIRST_SUPERUSER is undefined`，未进入浏览器测试。
+
+为排除测试账号收集阻塞，仅使用进程级非真实占位值重试公共边界：
+
+```powershell
+$env:FIRST_SUPERUSER='red@example.com'
+$env:FIRST_SUPERUSER_PASSWORD='not-a-real-password'
+pnpm exec playwright test tests/public-catalog.spec.ts
+```
+
+真实结果：退出码 `1`。Playwright setup 阶段报错：
+`Executable doesn't exist at C:\Users\21239\AppData\Local\ms-playwright\chromium_headless_shell-1234\chrome-headless-shell-win64\chrome-headless-shell.exe`。
+该测试进程随后已停止；未将未执行的浏览器断言标记为通过。
+
+### GREEN / 静态检查
+
+Biome 修复格式和静态问题后执行：
+
+```powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
+```
+
+真实结果：退出码 `0`，`Checked 63 files in 31ms. No fixes applied.`
+
+Playwright GREEN：未运行。由于 Chromium 可执行文件缺失，且用户要求本次不再运行浏览器或长时间命令，保持为未验证。
+
+## 其他验证与阻塞
+
+1. `pnpm build` 已执行，退出码 `2`。TypeScript 报告 `/dashboard` 和新的公共 `/` 不在旧 `routeTree.gen.ts` 类型中；构建脚本先执行 `tsc`、后执行 Vite 路由生成，因此未进入 Vite 阶段。
+2. 为使用官方 Vite/TanStack 生成链刷新路由树，执行 `pnpm exec vite build`，退出码 `1`。Vite 配置加载失败：`Failed to load native binding`；缺少 `./swc.win32-x64-msvc.node`，并报告 `ERR_SWC_NATIVE_CACHE` 及 SWC 缓存目录 DACL 权限问题。未手工写入生成路由树。
+3. Docker、数据库、SMTP、GitHub OAuth、DNS、Nginx 和线上服务验收本任务未运行，均未验证。
+
+## Self-review
+
+- 路由边界：公共 `/` 不挂载受保护 `_layout`；`/items`、`/settings`、`/admin` 仍挂载认证 layout；`/dashboard` 使用同一认证门禁。
+- 跳转边界：密码登录、GitHub callback、已登录访问 `/login` 和侧栏 Dashboard 均指向 `/dashboard`；登出仍清理本地认证标记并前往 `/login`。
+- 数据边界：首页只调用公开 `CatalogService.searchCatalog`，不伪造数据、统计、上游 URL 或 API Key；示例凭据仅为 `<YOUR_API_KEY>`。
+- 可访问性：公共页面使用 `header`、`nav`、`main`、`footer`、表单标签、`role=status`、`role=alert` 和可见 `:focus-visible` 焦点环；移动菜单使用 `aria-expanded`、`aria-controls` 和键盘可聚焦按钮。
+- 品牌边界：改动的 Logo/Footer/登录标题不再引用 FastAPI；未扩展修改任务简报之外的旧路由文件。
+- 独立只读子代理：当前会话未提供可调用的子代理工具，因此没有伪造独立审查结果；本报告仅记录主代理的只读 self-review。
+
+## 提交
+
+- 实现提交主题：`feat: split public and protected web shells`
+- 提交 SHA：`0acbfc3`。
+- 报告状态：本文件随实现提交写入；本次回填 SHA 后产生一个仅文档的收尾提交。
+
+## 未验证项
+
+- 真实 Chromium 浏览器中的匿名 `/`、`/catalog`、登录成功 `/dashboard`、登出和 `/items` 认证跳转。
+- TanStack Router 生成 `routeTree.gen.ts` 后的最终 TypeScript/build 结果。
+- 真实后端目录 API 返回项在浏览器中的展示。
+- 生产环境、Docker Compose、数据库、SMTP、GitHub OAuth、DNS、TLS、Nginx 和线上回归。
+
+## Task 7-2 修复报告：关闭公共壳层审查问题
+
+### 修复文件
+
+- `frontend/package.json`：将 `build` 调整为 `vite build && tsc -p tsconfig.build.json`，先让 Vite/TanStack Router 官方插件生成路由树，再执行类型检查。
+- `frontend/tests/login.spec.ts`：将“Logged-out user cannot access protected routes”中的登录后断言改为 `/dashboard` 和 `Yeyu API 控制台`，保留退出后 `/settings` 跳转 `/login` 的断言。
+- `frontend/src/routes/catalog/index.tsx`：新增任务 2 范围内的最小公共目录占位路由，复用 `PublicLayout`，提供语义 `h1`、`API 目录建设中`、`由公开目录驱动` 文案和返回首页入口；没有接口卡片、统计或 API 请求。
+- `frontend/tests/public-catalog.spec.ts`：要求 `/catalog` 最终 URL、占位标题和公共导航可见；移动菜单使用键盘 `Enter`、`Space` 实际操作，并断言 `aria-expanded` 为 `true → false → true` 以及展开后的目录/登录链接可见。
+- 未修改 `frontend/src/routeTree.gen.ts`；未触碰旧项目、线上服务、服务器、DNS、Nginx 或真实凭据。
+
+### 审查问题对应改动
+
+1. Critical 构建阻塞：根因是原 `build` 在 Vite 路由生成前运行 `tsc`。已改为 Vite 官方生成链先执行，再运行 `tsc`；本机生成链仍受 SWC 原生绑定环境阻塞，未手写生成树。
+2. Important 登录测试：已等待 `/dashboard`，断言 `Yeyu API 控制台`，并保留登出后访问 `/settings` 必须回到 `/login`。
+3. Important 公共目录：已新增 `/catalog` 最小占位页，并将测试强化为最终 URL、占位标题和公共导航断言；任务 3 可继续扩展该文件。
+4. Important 移动菜单：已从仅 `focus()` 改为对 menu button 使用 `press("Enter")`、`press("Space")`，验证收起/展开状态和展开后的链接。
+
+### 验证命令与真实结果
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\package.json E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+退出码：0
+输出：Checked 4 files in 6ms. No fixes applied.
+```
+
+```text
+git diff --check
+退出码：0；无空白错误（Git 仅提示 LF 将在后续写入时转换为 CRLF）。
+```
+
+```text
+pnpm build
+退出码：1
+输出关键原文：
+> frontend@0.0.0 build E:\AI_projects\YEYU-API\frontend
+> vite build && tsc -p tsconfig.build.json
+failed to load config from E:\AI_projects\YEYU-API\frontend\vite.config.ts
+Error: Failed to load native binding
+Error: Cannot find module './swc.win32-x64-msvc.node'
+Error: SWC native addon: validate cache root C:\Users\21239\AppData\Local\swc: ... DACL grants replacement rights ...
+code: 'ERR_SWC_NATIVE_CACHE'
+```
+
+```text
+pnpm rebuild @swc/core
+退出码：0，但 postinstall 真实输出仍为：
+@swc/core was not able to resolve native bindings installation. It'll try to use @swc/wasm as fallback instead.
+Error: ENOENT: no such file or directory, rename ...\@swc\core\npm-install\node_modules\@swc\wasm -> ...\node_modules\@swc\wasm
+Failed to install fallback @swc/wasm@1.16.12. @swc/core will not properly.
+```
+
+```text
+pnpm exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json
+退出码：1
+输出：旧 routeTree.gen.ts 类型集合中缺少 /dashboard、/catalog/ 和新的 /，对应 PublicHeader.tsx、useAuth.ts、_layout/dashboard.tsx、catalog/index.tsx、routes/index.tsx、login.tsx 报 TS2322/TS2345。
+```
+
+Playwright 未在本次修复中运行，遵循本次指令不运行长时间浏览器或全套测试；此前报告中的 Chromium 可执行文件缺失阻塞仍适用。
+
+### 阻塞结论与提交
+
+- 修复后的构建入口顺序已落地，但本机仍有阻塞：Vite/TanStack 官方生成链在加载配置时被 `@swc/core` 原生绑定缺失、`ERR_SWC_NATIVE_CACHE` 和 fallback `ENOENT` 阻断，因此本地未能生成新 `routeTree.gen.ts`，最终 `tsc` 不能通过。
+- 该阻塞已用真实命令和原始错误记录；没有手工编辑 `routeTree.gen.ts`，也没有把未运行的 Playwright 断言标记为通过。
+- 提交主题：`fix: close public shell review findings`
+- 提交 SHA：`673d806f955c54deb2284198babc33116b78d959`。
diff --git a/plans/agent-reports/task-7-2-review.md b/plans/agent-reports/task-7-2-review.md
new file mode 100644
index 0000000..c215f3a
--- /dev/null
+++ b/plans/agent-reports/task-7-2-review.md
@@ -0,0 +1,37 @@
+# Task 7-2 独立只读审查报告
+
+## Spec Compliance
+
+- ❌ 构建链阻塞：routeTree.gen.ts:17,46-50,67-75,209-224 仍引用已删除的 _layout/index，缺少新的 / 与 /dashboard；pnpm build 在 Vite 生成前的 tsc 阶段退出 2。此缺陷属于本任务应修复范围，但应修复生成顺序，不得手改生成文件。
+- ✅ 源文件路由无冲突：公共 routes/index.tsx 与 pathless _layout 平级，_layout/dashboard.tsx 仍受认证布局保护。
+- ✅ 登录成功、GitHub callback、已登录 /login 和 Sidebar Dashboard 的静态跳转均统一为 /dashboard。
+- ✅ 首页使用真实 CatalogService.searchCatalog，有加载/错误/空结果状态，无虚假统计、任意上游 URL 或真实密钥。
+- ⚠️ 无法从 diff 确认浏览器运行时、GitHub OAuth callback、/catalog 是否存在真实公共路由、目录 API 是否确实免认证，以及全仓库 FastAPI 品牌残留。
+
+## Strengths
+
+- 公共壳层使用 header、nav、main、footer、可见焦点环和移动菜单 ARIA 属性。
+- 受保护首页已迁移为 dashboard，认证 beforeLoad 保留。
+- 示例凭据仅为 <YOUR_API_KEY>；未发现线上资源、旧项目或凭据改动。
+
+## Issues
+
+### Critical (Must Fix)
+
+- E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts:17,46-50,67-75,209-224：生成树引用已删除文件并保留旧受保护根路由，新的 /、/dashboard 类型不存在；pnpm build 在 Vite 生成前失败，当前提交不可交付。修复生成顺序或通过官方生成链刷新并提交生成结果，不得手工编辑 routeTree.gen.ts。
+
+### Important (Should Fix)
+
+- E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts:89-99：测试仍等待 / 并查找已删除的旧欢迎文案；构建修复后会超时，登出及 /settings 保护断言不会执行。应改为等待 /dashboard 并断言新的 dashboard 标题。
+- E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts:18-24 与 E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx:61-63,134-151：/catalog 测试只断言不在 /login，404 或空路由也能通过；应断言最终 URL 保持 /catalog，并断言公共壳层。若目录页延后至任务 3，应同步延后该测试和入口验收。
+- E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts:27-39：测试仅调用 focus，没有实际操作移动菜单或验证 aria-expanded；应使用键盘 Enter/Space 操作菜单按钮并断言展开、收起和链接可访问性。
+
+### Minor (Nice to Have)
+
+- 无。
+
+## Assessment
+
+**Task quality:** Needs fixes
+
+**Reasoning:** 源码路由拆分和认证跳转方向正确，但生成路由树与构建顺序造成当前交付阻塞，且已有登录测试落后于新路由。
diff --git a/plans/agent-reports/task-7-3-brief.md b/plans/agent-reports/task-7-3-brief.md
new file mode 100644
index 0000000..67f06a2
--- /dev/null
+++ b/plans/agent-reports/task-7-3-brief.md
@@ -0,0 +1,58 @@
+## Task 3: Build Search-First Catalog and Detail Pages
+
+**Files:**
+
+- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogSearch.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogFilters.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogCard.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogGrid.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogStates.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CodeExample.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\index.css
+- Modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+
+### Implementation
+
+- [ ] 在测试中覆盖目录页匿名可访问、搜索参数能反映到 URL、分类筛选能反映到 URL、空结果有明确状态、详情页展示 /v1/tools/time、GET、API Key 鉴权、参数、响应字段和错误码。
+- [ ] 目录页通过生成的 CatalogService.getCatalog 和 React Query 获取分页数据，query、category、status 使用 TanStack Router search params 作为唯一可分享状态；输入搜索设置 300 至 500 毫秒防抖并避免逐键请求。
+- [ ] 目录页首屏顺序固定为页面标题与搜索框、分类/状态筛选、真实目录卡片；卡片包含名称、中文简介、请求方法、路径、免费标记、健康/发布状态和更新时间，点击后进入 /catalog/:slug。
+- [ ] 目录页只展示后端返回数据，不在前端硬编码候选接口；API 返回空、错误和加载状态分别使用可读的 Empty、Error、Skeleton 组件。
+- [ ] 详情页通过生成的 CatalogService.getCatalogDetail({ path: { slug } }) 获取数据；展示鉴权说明、参数表、响应结构、错误码、缓存规则、来源标签和 curl、JavaScript、Python 示例。
+- [ ] 代码示例只显示 <YOUR_API_KEY>，统一从当前域名拼接请求 URL，不保存或读取真实 API Key，不提供任意 URL 输入；复制按钮使用可访问名称并在成功后有非颜色反馈。
+- [ ] 首页保持索引台视觉：上方以一句清晰定位和主搜索入口为主，下面展示由真实目录 API 返回的精选工具卡片、一个可直接跳转的 Quick Start 区块和公益/使用边界说明；不展示假统计。
+- [ ] 公共导航在首页、目录页和详情页保持一致；目录页搜索框支持从首页带 query 参数跳转后继续搜索。
+- [ ] 移动端将详情页的参数表、代码块和路径行处理为可横向滚动而不撑破页面；桌面端使用窄内容列、明显分隔线和稳定状态色。
+
+### Verification
+
+- [ ] 执行前端构建与静态检查：
+
+~~~powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
+pnpm build
+~~~
+
+- [ ] 在项目 Docker Compose 测试环境可用时执行：
+
+~~~powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec playwright test tests/public-catalog.spec.ts
+~~~
+
+- [ ] 通过 API 测试确认种子后端实际提供目录数据：
+
+~~~powershell
+conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py -q
+~~~
+
+- [ ] 使用真实浏览器尺寸至少检查 1280 像素桌面视口和 390 像素移动视口；记录页面 URL、公开/受保护结果、控制台错误和截图路径。截图若用于审查，只放在项目外部临时目录。
+- [ ] 独立只读子代理检查 API client 使用、URL 状态同步、错误/空状态、示例密钥脱敏、移动端溢出、可访问性和视觉方案偏离，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-review.md。
+- [ ] 处理审查问题后重跑构建、API 测试和浏览器测试，创建提交 feat: add public catalog and api detail pages 并推送 origin/main。
+
diff --git a/plans/agent-reports/task-7-3-diff.md b/plans/agent-reports/task-7-3-diff.md
new file mode 100644
index 0000000..f85bbcc
--- /dev/null
+++ b/plans/agent-reports/task-7-3-diff.md
@@ -0,0 +1,2409 @@
+# Review package: 53b19fc..ec82905
+
+## Commits
+ec82905 docs: record task 3 catalog implementation
+a30e6e7 docs: record task 7-3 implementation report
+c13adce feat: add public catalog and api detail pages
+
+## Files changed
+ .../src/components/ApiCatalog/ApiDetailView.tsx    | 327 +++++++++++
+ frontend/src/components/ApiCatalog/CatalogCard.tsx |  42 ++
+ .../src/components/ApiCatalog/CatalogFilters.tsx   |  72 +++
+ frontend/src/components/ApiCatalog/CatalogGrid.tsx |  19 +
+ .../src/components/ApiCatalog/CatalogSearch.tsx    |  53 ++
+ .../src/components/ApiCatalog/CatalogStates.tsx    |  64 ++
+ frontend/src/components/ApiCatalog/CodeExample.tsx |  67 +++
+ .../src/components/ApiCatalog/catalog-types.ts     |  89 +++
+ .../src/components/PublicSite/PublicFooter.tsx     |   4 +-
+ .../src/components/PublicSite/PublicHeader.tsx     |   4 +-
+ frontend/src/index.css                             | 647 ++++++++++++++++++++-
+ frontend/src/routes/catalog/$slug.tsx              |  46 ++
+ frontend/src/routes/catalog/index.tsx              | 156 ++++-
+ frontend/src/routes/index.tsx                      |  28 +-
+ frontend/tests/public-catalog.spec.ts              | 235 +++++++-
+ plans/agent-reports/task-7-3-brief.md              |  58 ++
+ plans/agent-reports/task-7-3-report.md             | 135 +++++
+ 17 files changed, 1984 insertions(+), 62 deletions(-)
+
+## Diff
+diff --git a/frontend/src/components/ApiCatalog/ApiDetailView.tsx b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+new file mode 100644
+index 0000000..83a7ef8
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+@@ -0,0 +1,327 @@
++import { Link } from "@tanstack/react-router"
++
++import type { ApiDetail } from "@/client"
++
++import CodeExample from "./CodeExample"
++import {
++  asRecord,
++  asText,
++  formatMetadata,
++  formatUpdatedAt,
++  responseProperties,
++} from "./catalog-types"
++
++type QueryExample = {
++  name: string
++  value: string
++}
++
++function parameterExamples(detail: ApiDetail): QueryExample[] {
++  return detail.parameters.flatMap((parameter) => {
++    if (asText(parameter.in, "") !== "query") return []
++    const name = asText(parameter.name, "")
++    if (!name) return []
++
++    const schema = asRecord(parameter.schema)
++    const examples = schema?.examples
++    const example = Array.isArray(examples) ? examples[0] : undefined
++    const value = asText(example ?? schema?.default, "value")
++    return [{ name, value }]
++  })
++}
++
++function buildCodeExamples(detail: ApiDetail, authHeader: string) {
++  const method = detail.method.toUpperCase()
++  const queryParameters = parameterExamples(detail)
++  const absoluteUrl = `https://api.yeyubaka.top${detail.path}`
++  const curlStart =
++    method === "GET"
++      ? `curl -G "${absoluteUrl}"`
++      : `curl -X ${method} "${absoluteUrl}"`
++  const curlLines = [curlStart, `  -H "${authHeader}: <YOUR_API_KEY>"`]
++  for (const parameter of queryParameters) {
++    curlLines.push(`  --data-urlencode "${parameter.name}=${parameter.value}"`)
++  }
++
++  const javascriptLines = [
++    `const endpoint = new URL(${JSON.stringify(detail.path)}, window.location.origin);`,
++    ...queryParameters.map(
++      (parameter) =>
++        `endpoint.searchParams.set(${JSON.stringify(parameter.name)}, ${JSON.stringify(parameter.value)});`,
++    ),
++    "",
++    "const response = await fetch(endpoint, {",
++    `  method: ${JSON.stringify(method)},`,
++    "  headers: {",
++    `    ${JSON.stringify(authHeader)}: "<YOUR_API_KEY>",`,
++    "  },",
++    "});",
++    "const data = await response.json();",
++    "console.log(data);",
++  ]
++
++  const pythonLines = [
++    "import requests",
++    "",
++    "response = requests.request(",
++    `    ${JSON.stringify(method)},`,
++    `    ${JSON.stringify(absoluteUrl)},`,
++    `    headers={${JSON.stringify(authHeader)}: "<YOUR_API_KEY>"},`,
++    ...(queryParameters.length
++      ? [
++          `    params=${JSON.stringify(Object.fromEntries(queryParameters.map((parameter) => [parameter.name, parameter.value])))},`,
++        ]
++      : []),
++    "    timeout=10,",
++    ")",
++    "response.raise_for_status()",
++    "print(response.json())",
++  ]
++
++  return {
++    curl: curlLines.join(" \\\n"),
++    javascript: javascriptLines.join("\n"),
++    python: pythonLines.join("\n"),
++  }
++}
++
++function readableCacheKey(key: string) {
++  return key
++    .replaceAll("_", " ")
++    .replace(/\b\w/g, (character) => character.toUpperCase())
++}
++
++interface ApiDetailViewProps {
++  detail: ApiDetail
++}
++
++export function ApiDetailView({ detail }: ApiDetailViewProps) {
++  const authHeader = detail.auth.header ?? "X-API-Key"
++  const examples = buildCodeExamples(detail, authHeader)
++  const responseFields = responseProperties(detail)
++  const cacheEntries = Object.entries(detail.cache_rules)
++
++  return (
++    <div className="api-detail-page">
++      <div className="api-detail-breadcrumbs">
++        <Link to="/catalog" className="public-text-link">
++          ← 返回公开目录
++        </Link>
++        <span aria-hidden="true">/</span>
++        <span>{detail.category}</span>
++      </div>
++
++      <header className="api-detail-header">
++        <div className="api-detail-path-row">
++          <span className="catalog-method-badge">{detail.method}</span>
++          <code>{detail.path}</code>
++        </div>
++        <h1 className="api-detail-title">{detail.name}</h1>
++        <p className="api-detail-summary">{detail.summary}</p>
++        <div className="api-detail-tags">
++          {detail.is_free ? (
++            <span className="catalog-tag catalog-tag-free">免费</span>
++          ) : null}
++          <span className="catalog-tag catalog-tag-status">
++            {detail.status}
++          </span>
++          <time dateTime={detail.updated_at ?? undefined}>
++            更新于 {formatUpdatedAt(detail.updated_at)}
++          </time>
++        </div>
++      </header>
++
++      <div className="api-detail-layout">
++        <main className="api-detail-main">
++          <section
++            className="api-detail-section"
++            aria-labelledby="api-auth-heading"
++          >
++            <p className="public-eyebrow">AUTHENTICATION</p>
++            <h2 id="api-auth-heading" className="api-detail-section-title">
++              API Key 鉴权
++            </h2>
++            <p className="api-detail-copy">
++              调用该接口时，请在 <code>{authHeader}</code> 请求头中提供你的 API
++              Key。浏览器登录 Cookie 不会替代 API Key。
++            </p>
++            <div className="api-auth-callout">
++              <span>请求头</span>
++              <code>{authHeader}: &lt;YOUR_API_KEY&gt;</code>
++            </div>
++          </section>
++
++          <section
++            className="api-detail-section"
++            aria-labelledby="api-parameters-heading"
++          >
++            <p className="public-eyebrow">REQUEST</p>
++            <h2
++              id="api-parameters-heading"
++              className="api-detail-section-title"
++            >
++              参数
++            </h2>
++            {detail.parameters.length ? (
++              <div className="api-table-scroll">
++                <table className="api-detail-table">
++                  <thead>
++                    <tr>
++                      <th scope="col">名称</th>
++                      <th scope="col">位置</th>
++                      <th scope="col">必填</th>
++                      <th scope="col">类型 / 说明</th>
++                    </tr>
++                  </thead>
++                  <tbody>
++                    {detail.parameters.map((parameter, index) => {
++                      const schema = asRecord(parameter.schema)
++                      const name = asText(parameter.name, `参数 ${index + 1}`)
++                      const schemaText = asText(schema?.type, "—")
++                      const description = asText(parameter.description, "")
++                      return (
++                        <tr
++                          key={`${name}-${asText(parameter.in, "unknown")}-${index}`}
++                        >
++                          <th scope="row">
++                            <code>{name}</code>
++                          </th>
++                          <td>{asText(parameter.in)}</td>
++                          <td>{parameter.required === true ? "是" : "否"}</td>
++                          <td>
++                            <span>{schemaText}</span>
++                            {description ? (
++                              <span className="api-table-note">
++                                {description}
++                              </span>
++                            ) : null}
++                          </td>
++                        </tr>
++                      )
++                    })}
++                  </tbody>
++                </table>
++              </div>
++            ) : (
++              <p className="api-detail-muted">该接口不接受参数。</p>
++            )}
++          </section>
++
++          <section
++            className="api-detail-section"
++            aria-labelledby="api-response-heading"
++          >
++            <p className="public-eyebrow">RESPONSE</p>
++            <h2 id="api-response-heading" className="api-detail-section-title">
++              响应结构
++            </h2>
++            {responseFields.length ? (
++              <div className="api-response-fields">
++                {responseFields.map(([name, schema]) => (
++                  <div key={name} className="api-response-field">
++                    <code>{name}</code>
++                    <span>{asText(schema.type, "object")}</span>
++                    {schema.format ? (
++                      <span>{asText(schema.format)}</span>
++                    ) : null}
++                  </div>
++                ))}
++              </div>
++            ) : null}
++            <pre className="api-json-block">
++              <code>{formatMetadata(detail.response_schema)}</code>
++            </pre>
++          </section>
++
++          <section
++            className="api-detail-section"
++            aria-labelledby="api-errors-heading"
++          >
++            <p className="public-eyebrow">ERRORS</p>
++            <h2 id="api-errors-heading" className="api-detail-section-title">
++              错误码
++            </h2>
++            {detail.errors.length ? (
++              <div className="api-table-scroll">
++                <table className="api-detail-table">
++                  <thead>
++                    <tr>
++                      <th scope="col">HTTP</th>
++                      <th scope="col">错误码</th>
++                      <th scope="col">说明</th>
++                    </tr>
++                  </thead>
++                  <tbody>
++                    {detail.errors.map((error, index) => (
++                      <tr key={`${asText(error.code, "error")}-${index}`}>
++                        <td>{asText(error.status)}</td>
++                        <th scope="row">
++                          <code>{asText(error.code)}</code>
++                        </th>
++                        <td>
++                          {asText(error.description, asText(error.message))}
++                        </td>
++                      </tr>
++                    ))}
++                  </tbody>
++                </table>
++              </div>
++            ) : (
++              <p className="api-detail-muted">目录暂未提供错误码说明。</p>
++            )}
++          </section>
++
++          <section
++            className="api-detail-section"
++            aria-labelledby="api-examples-heading"
++          >
++            <p className="public-eyebrow">EXAMPLES</p>
++            <h2 id="api-examples-heading" className="api-detail-section-title">
++              安全调用示例
++            </h2>
++            <p className="api-detail-copy">
++              示例只使用占位密钥，不会读取或保存浏览器中的真实凭据。
++            </p>
++            <div className="api-code-grid">
++              <CodeExample language="curl" code={examples.curl} />
++              <CodeExample language="JavaScript" code={examples.javascript} />
++              <CodeExample language="Python" code={examples.python} />
++            </div>
++          </section>
++        </main>
++
++        <aside className="api-detail-aside" aria-label="接口补充信息">
++          <section
++            className="api-aside-card"
++            aria-labelledby="api-source-heading"
++          >
++            <p className="public-eyebrow">SOURCE</p>
++            <h2 id="api-source-heading" className="api-aside-title">
++              来源
++            </h2>
++            <p className="api-aside-value">{detail.source}</p>
++          </section>
++          <section
++            className="api-aside-card"
++            aria-labelledby="api-cache-heading"
++          >
++            <p className="public-eyebrow">CACHE</p>
++            <h2 id="api-cache-heading" className="api-aside-title">
++              缓存规则
++            </h2>
++            <dl className="api-cache-list">
++              {cacheEntries.map(([key, value]) => (
++                <div key={key}>
++                  <dt>{readableCacheKey(key)}</dt>
++                  <dd>{formatMetadata(value)}</dd>
++                </div>
++              ))}
++            </dl>
++          </section>
++        </aside>
++      </div>
++    </div>
++  )
++}
++
++export default ApiDetailView
+diff --git a/frontend/src/components/ApiCatalog/CatalogCard.tsx b/frontend/src/components/ApiCatalog/CatalogCard.tsx
+new file mode 100644
+index 0000000..5b3c94e
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/CatalogCard.tsx
+@@ -0,0 +1,42 @@
++import { Link } from "@tanstack/react-router"
++
++import type { CatalogItem } from "@/client"
++
++import { formatUpdatedAt } from "./catalog-types"
++
++interface CatalogCardProps {
++  item: CatalogItem
++}
++
++export function CatalogCard({ item }: CatalogCardProps) {
++  return (
++    <article className="catalog-card" data-testid={`catalog-card-${item.slug}`}>
++      <div className="catalog-card-path">
++        <span className="catalog-method-badge">{item.method}</span>
++        <code>{item.path}</code>
++      </div>
++      <div className="catalog-card-content">
++        <Link
++          to="/catalog/$slug"
++          params={{ slug: item.slug }}
++          className="catalog-card-title"
++        >
++          {item.name}
++        </Link>
++        <p className="catalog-card-summary">{item.summary}</p>
++      </div>
++      <div className="catalog-card-meta">
++        <span className="catalog-tag">{item.category}</span>
++        {item.is_free ? (
++          <span className="catalog-tag catalog-tag-free">免费</span>
++        ) : null}
++        <span className="catalog-tag catalog-tag-status">{item.status}</span>
++        <time dateTime={item.updated_at ?? undefined}>
++          更新于 {formatUpdatedAt(item.updated_at)}
++        </time>
++      </div>
++    </article>
++  )
++}
++
++export default CatalogCard
+diff --git a/frontend/src/components/ApiCatalog/CatalogFilters.tsx b/frontend/src/components/ApiCatalog/CatalogFilters.tsx
+new file mode 100644
+index 0000000..2df3a59
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/CatalogFilters.tsx
+@@ -0,0 +1,72 @@
++import type { CatalogItem } from "@/client"
++
++import { uniqueCatalogValues } from "./catalog-types"
++
++interface CatalogFiltersProps {
++  items: CatalogItem[]
++  category?: string
++  status?: string
++  onCategoryChange: (value: string) => void
++  onStatusChange: (value: string) => void
++}
++
++export function CatalogFilters({
++  items,
++  category,
++  status,
++  onCategoryChange,
++  onStatusChange,
++}: CatalogFiltersProps) {
++  const categories = uniqueCatalogValues(items, "category", category)
++  const statuses = uniqueCatalogValues(items, "status", status)
++
++  return (
++    <section
++      className="catalog-filters"
++      aria-labelledby="catalog-filter-heading"
++    >
++      <div>
++        <p className="public-eyebrow">筛选</p>
++        <h2 id="catalog-filter-heading" className="catalog-filter-title">
++          缩小公开接口范围
++        </h2>
++      </div>
++      <div className="catalog-filter-controls">
++        <div className="catalog-filter-field">
++          <label htmlFor="catalog-category">分类</label>
++          <select
++            id="catalog-category"
++            aria-label="分类"
++            value={category ?? ""}
++            onChange={(event) => onCategoryChange(event.target.value)}
++          >
++            <option value="">全部分类</option>
++            {categories.map((value) => (
++              <option key={value} value={value}>
++                {value}
++              </option>
++            ))}
++          </select>
++        </div>
++        <div className="catalog-filter-field">
++          <label htmlFor="catalog-status">状态</label>
++          <select
++            id="catalog-status"
++            aria-label="状态"
++            value={status ?? ""}
++            onChange={(event) => onStatusChange(event.target.value)}
++          >
++            <option value="">全部状态</option>
++            {statuses.map((value) => (
++              <option key={value} value={value}>
++                {value}
++              </option>
++            ))}
++          </select>
++        </div>
++      </div>
++    </section>
++  )
++}
++
++export default CatalogFilters
+diff --git a/frontend/src/components/ApiCatalog/CatalogGrid.tsx b/frontend/src/components/ApiCatalog/CatalogGrid.tsx
+new file mode 100644
+index 0000000..86425a4
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/CatalogGrid.tsx
+@@ -0,0 +1,19 @@
++import type { CatalogItem } from "@/client"
++
++import CatalogCard from "./CatalogCard"
++
++interface CatalogGridProps {
++  items: CatalogItem[]
++}
++
++export function CatalogGrid({ items }: CatalogGridProps) {
++  return (
++    <div className="catalog-grid" data-testid="catalog-grid">
++      {items.map((item) => (
++        <CatalogCard key={item.slug} item={item} />
++      ))}
++    </div>
++  )
++}
++
++export default CatalogGrid
+diff --git a/frontend/src/components/ApiCatalog/CatalogSearch.tsx b/frontend/src/components/ApiCatalog/CatalogSearch.tsx
+new file mode 100644
+index 0000000..a625b17
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/CatalogSearch.tsx
+@@ -0,0 +1,53 @@
++import { Search, X } from "lucide-react"
++
++interface CatalogSearchProps {
++  value: string
++  onChange: (value: string) => void
++}
++
++export function CatalogSearch({ value, onChange }: CatalogSearchProps) {
++  return (
++    <section
++      className="catalog-search-panel"
++      aria-labelledby="catalog-search-heading"
++    >
++      <div className="catalog-search-heading">
++        <div>
++          <p className="public-eyebrow">搜索优先</p>
++          <h2 id="catalog-search-heading" className="catalog-search-title">
++            先按接口名、简介或路径查找
++          </h2>
++        </div>
++        <p className="catalog-search-hint">输入停止后约 400ms 更新目录</p>
++      </div>
++      <div className="catalog-search-control">
++        <Search aria-hidden="true" className="catalog-search-icon" />
++        <label className="sr-only" htmlFor="catalog-search-input">
++          搜索公开 API
++        </label>
++        <input
++          id="catalog-search-input"
++          data-testid="catalog-search-input"
++          className="catalog-search-input"
++          type="search"
++          value={value}
++          onChange={(event) => onChange(event.target.value)}
++          placeholder="例如：时间、UUID、工具"
++          autoComplete="off"
++        />
++        {value ? (
++          <button
++            type="button"
++            className="catalog-search-clear"
++            aria-label="清除搜索"
++            onClick={() => onChange("")}
++          >
++            <X aria-hidden="true" />
++          </button>
++        ) : null}
++      </div>
++    </section>
++  )
++}
++
++export default CatalogSearch
+diff --git a/frontend/src/components/ApiCatalog/CatalogStates.tsx b/frontend/src/components/ApiCatalog/CatalogStates.tsx
+new file mode 100644
+index 0000000..760889d
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/CatalogStates.tsx
+@@ -0,0 +1,64 @@
++interface CatalogErrorStateProps {
++  onRetry: () => void
++}
++
++export function CatalogLoadingState() {
++  return (
++    <div
++      className="catalog-state catalog-skeleton-list"
++      data-testid="catalog-loading"
++      role="status"
++      aria-label="正在加载公开目录"
++    >
++      <span className="catalog-skeleton-line catalog-skeleton-line-wide" />
++      <span className="catalog-skeleton-line" />
++      <span className="catalog-skeleton-line catalog-skeleton-line-short" />
++      <span className="sr-only">正在读取真实目录……</span>
++    </div>
++  )
++}
++
++export function CatalogErrorState({ onRetry }: CatalogErrorStateProps) {
++  return (
++    <div
++      className="catalog-state catalog-state-error"
++      data-testid="catalog-error"
++      role="alert"
++    >
++      <div>
++        <p className="catalog-state-kicker">目录读取失败</p>
++        <p>公开目录暂时无法读取，请稍后重试。</p>
++      </div>
++      <button type="button" className="public-inline-button" onClick={onRetry}>
++        重试
++      </button>
++    </div>
++  )
++}
++
++export function CatalogEmptyState() {
++  return (
++    <div className="catalog-state" data-testid="catalog-empty" role="status">
++      <p className="catalog-state-kicker">没有匹配结果</p>
++      <p>没有找到匹配的公开接口，请换一个关键词或清除筛选。</p>
++    </div>
++  )
++}
++
++export function CatalogDetailErrorState({ onRetry }: CatalogErrorStateProps) {
++  return (
++    <div
++      className="catalog-state catalog-state-error"
++      data-testid="catalog-detail-error"
++      role="alert"
++    >
++      <div>
++        <p className="catalog-state-kicker">详情读取失败</p>
++        <p>该接口可能已下线，或目录服务暂时不可用。</p>
++      </div>
++      <button type="button" className="public-inline-button" onClick={onRetry}>
++        重试
++      </button>
++    </div>
++  )
++}
+diff --git a/frontend/src/components/ApiCatalog/CodeExample.tsx b/frontend/src/components/ApiCatalog/CodeExample.tsx
+new file mode 100644
+index 0000000..bcec275
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/CodeExample.tsx
+@@ -0,0 +1,67 @@
++import { Check, Copy } from "lucide-react"
++import { useState } from "react"
++
++interface CodeExampleProps {
++  language: string
++  code: string
++}
++
++function codeId(language: string) {
++  return language.toLowerCase().replace(/[^a-z0-9]+/g, "-")
++}
++
++export function CodeExample({ language, code }: CodeExampleProps) {
++  const [copyState, setCopyState] = useState<"idle" | "success" | "error">(
++    "idle",
++  )
++  const headingId = `code-example-${codeId(language)}`
++
++  const copyCode = async () => {
++    if (!navigator.clipboard) {
++      setCopyState("error")
++      return
++    }
++
++    try {
++      await navigator.clipboard.writeText(code)
++      setCopyState("success")
++    } catch {
++      setCopyState("error")
++    }
++  }
++
++  const buttonLabel = copyState === "success" ? "已复制" : "复制"
++
++  return (
++    <section className="code-example" aria-labelledby={headingId}>
++      <div className="code-example-header">
++        <h3 id={headingId}>{language}</h3>
++        <button
++          type="button"
++          className="code-copy-button"
++          aria-label={`复制 ${language} 示例`}
++          onClick={() => void copyCode()}
++        >
++          {copyState === "success" ? (
++            <Check aria-hidden="true" />
++          ) : (
++            <Copy aria-hidden="true" />
++          )}
++          <span>{buttonLabel}</span>
++        </button>
++      </div>
++      <pre className="code-example-block">
++        <code>{code}</code>
++      </pre>
++      <p className="code-example-feedback" aria-live="polite">
++        {copyState === "success"
++          ? `${language} 示例已复制到剪贴板。`
++          : copyState === "error"
++            ? "复制失败，请手动选择代码。"
++            : ""}
++      </p>
++    </section>
++  )
++}
++
++export default CodeExample
+diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
+new file mode 100644
+index 0000000..16a7477
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/catalog-types.ts
+@@ -0,0 +1,89 @@
++import type { ApiDetail, CatalogItem } from "@/client"
++
++export type CatalogSearchParams = {
++  query?: string
++  category?: string
++  status?: string
++}
++
++export type CatalogMetadata = Record<string, unknown>
++
++export function normalizeSearchValue(value: unknown): string | undefined {
++  if (typeof value !== "string") return undefined
++  const normalized = value.trim()
++  return normalized || undefined
++}
++
++export function parseCatalogSearch(
++  search: Record<string, unknown>,
++): CatalogSearchParams {
++  return {
++    query: normalizeSearchValue(search.query),
++    category: normalizeSearchValue(search.category),
++    status: normalizeSearchValue(search.status),
++  }
++}
++
++export function formatUpdatedAt(value?: string | null): string {
++  if (!value) return "更新时间待补充"
++
++  const timestamp = Date.parse(value)
++  if (Number.isNaN(timestamp)) return value
++
++  return new Intl.DateTimeFormat("zh-HK", {
++    dateStyle: "medium",
++  }).format(new Date(timestamp))
++}
++
++export function asRecord(value: unknown): CatalogMetadata | undefined {
++  if (typeof value !== "object" || value === null || Array.isArray(value)) {
++    return undefined
++  }
++  return value as CatalogMetadata
++}
++
++export function asText(value: unknown, fallback = "—"): string {
++  if (typeof value === "string") return value
++  if (typeof value === "number" || typeof value === "boolean") {
++    return String(value)
++  }
++  return fallback
++}
++
++export function formatMetadata(value: unknown): string {
++  if (value === null || value === undefined) return "—"
++  if (typeof value === "string") return value
++  if (typeof value === "number" || typeof value === "boolean") {
++    return String(value)
++  }
++
++  try {
++    return JSON.stringify(value, null, 2) ?? "无法展示"
++  } catch {
++    return "无法展示"
++  }
++}
++
++export function responseProperties(
++  detail: ApiDetail,
++): Array<[string, CatalogMetadata]> {
++  const properties = asRecord(detail.response_schema)?.properties
++  if (!properties || typeof properties !== "object") return []
++
++  return Object.entries(properties)
++    .map(
++      ([name, value]) =>
++        [name, asRecord(value) ?? {}] as [string, CatalogMetadata],
++    )
++    .sort(([left], [right]) => left.localeCompare(right))
++}
++
++export function uniqueCatalogValues(
++  items: CatalogItem[],
++  field: "category" | "status",
++  currentValue?: string,
++): string[] {
++  const values = new Set(items.map((item) => item[field]).filter(Boolean))
++  if (currentValue) values.add(currentValue)
++  return Array.from(values).sort((left, right) => left.localeCompare(right))
++}
+diff --git a/frontend/src/components/PublicSite/PublicFooter.tsx b/frontend/src/components/PublicSite/PublicFooter.tsx
+index 15a05ca..192e8b8 100644
+--- a/frontend/src/components/PublicSite/PublicFooter.tsx
++++ b/frontend/src/components/PublicSite/PublicFooter.tsx
+@@ -8,23 +8,23 @@ export function PublicFooter() {
+       <div className="public-container flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
+         <div>
+           <p className="font-semibold text-[var(--yeyu-ink)]">
+             Yeyu API 公益平台
+           </p>
+           <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
+             面向学生与个人开发者的公开工具目录 · {currentYear}
+           </p>
+         </div>
+         <nav aria-label="页脚导航" className="flex flex-wrap gap-4 text-sm">
+-          <a className="public-footer-link" href="/catalog">
++          <Link className="public-footer-link" to="/catalog">
+             API 目录
+-          </a>
++          </Link>
+           <Link className="public-footer-link" to="/" hash="usage">
+             使用规范
+           </Link>
+           <Link className="public-footer-link" to="/login">
+             登录
+           </Link>
+         </nav>
+       </div>
+     </footer>
+   )
+diff --git a/frontend/src/components/PublicSite/PublicHeader.tsx b/frontend/src/components/PublicSite/PublicHeader.tsx
+index e6daf45..4a2d6d2 100644
+--- a/frontend/src/components/PublicSite/PublicHeader.tsx
++++ b/frontend/src/components/PublicSite/PublicHeader.tsx
+@@ -11,23 +11,23 @@ interface NavigationLinksProps {
+ 
+ function NavigationLinks({ onNavigate }: NavigationLinksProps) {
+   const linkClassName =
+     "public-nav-link rounded-md px-3 py-2 text-sm font-medium"
+ 
+   return (
+     <>
+       <Link to="/" className={linkClassName} onClick={onNavigate}>
+         首页
+       </Link>
+-      <a href="/catalog" className={linkClassName} onClick={onNavigate}>
++      <Link to="/catalog" className={linkClassName} onClick={onNavigate}>
+         API 目录
+-      </a>
++      </Link>
+       <Link to="/" hash="usage" className={linkClassName} onClick={onNavigate}>
+         使用规范
+       </Link>
+       {isLoggedIn() ? (
+         <Link
+           to="/dashboard"
+           className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
+           onClick={onNavigate}
+         >
+           控制台
+diff --git a/frontend/src/index.css b/frontend/src/index.css
+index a042441..4cd1214 100644
+--- a/frontend/src/index.css
++++ b/frontend/src/index.css
+@@ -545,43 +545,688 @@
+   width: 1.75rem;
+   align-items: center;
+   justify-content: center;
+   border-radius: 0.25rem;
+   background: var(--yeyu-teal);
+   color: #ffffff;
+   font-size: 0.85em;
+   font-weight: 800;
+ }
+ 
++.public-catalog-title-link {
++  color: inherit;
++  text-decoration: none;
++  text-underline-offset: 0.2rem;
++}
++
++.public-catalog-title-link:hover {
++  color: var(--yeyu-teal);
++  text-decoration: underline;
++}
++
++.catalog-page-shell,
++.catalog-detail-shell {
++  padding-block: clamp(3rem, 7vw, 6rem);
++}
++
++.catalog-page-header {
++  max-width: 48rem;
++  padding-bottom: 2.5rem;
++}
++
++.catalog-page-title {
++  margin-top: 0.85rem;
++  color: var(--yeyu-ink);
++  font-size: clamp(2.75rem, 7vw, 5.25rem);
++  font-weight: 700;
++  letter-spacing: -0.06em;
++  line-height: 0.98;
++}
++
++.catalog-page-lede {
++  max-width: 42rem;
++  margin-top: 1.25rem;
++  color: var(--yeyu-muted);
++  font-size: 1.05rem;
++  line-height: 1.8;
++}
++
++.catalog-search-panel,
++.catalog-filters {
++  display: grid;
++  gap: 1.25rem;
++  padding: 1.25rem;
++  border: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper-strong);
++}
++
++.catalog-search-panel {
++  margin-top: 0.5rem;
++}
++
++.catalog-search-heading,
++.catalog-results-heading {
++  display: flex;
++  align-items: end;
++  justify-content: space-between;
++  gap: 1rem;
++}
++
++.catalog-search-title,
++.catalog-filter-title,
++.catalog-results-title {
++  margin-top: 0.45rem;
++  color: var(--yeyu-ink);
++  font-size: 1.25rem;
++  font-weight: 700;
++  letter-spacing: -0.025em;
++}
++
++.catalog-search-hint,
++.catalog-results-count,
++.catalog-refreshing {
++  color: var(--yeyu-muted);
++  font-size: 0.8rem;
++}
++
++.catalog-search-control {
++  display: flex;
++  min-width: 0;
++  align-items: center;
++  gap: 0.7rem;
++  min-height: 3.25rem;
++  padding-inline: 1rem;
++  border: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper);
++}
++
++.catalog-search-icon {
++  flex: 0 0 auto;
++  color: var(--yeyu-teal);
++}
++
++.catalog-search-input {
++  min-width: 0;
++  flex: 1;
++  border: 0;
++  outline: 0;
++  background: transparent;
++  color: var(--yeyu-ink);
++}
++
++.catalog-search-input::placeholder {
++  color: var(--yeyu-muted);
++}
++
++.catalog-search-clear {
++  display: inline-flex;
++  height: 2rem;
++  width: 2rem;
++  flex: 0 0 auto;
++  align-items: center;
++  justify-content: center;
++  border: 1px solid var(--yeyu-line);
++  color: var(--yeyu-muted);
++}
++
++.catalog-search-clear svg {
++  height: 1rem;
++  width: 1rem;
++}
++
++.catalog-filters {
++  grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr);
++  margin-top: 1rem;
++  background: var(--yeyu-mint);
++}
++
++.catalog-filter-controls {
++  display: grid;
++  grid-template-columns: repeat(2, minmax(0, 1fr));
++  gap: 0.75rem;
++}
++
++.catalog-filter-field {
++  display: grid;
++  gap: 0.35rem;
++}
++
++.catalog-filter-field label {
++  color: var(--yeyu-muted);
++  font-size: 0.78rem;
++  font-weight: 700;
++}
++
++.catalog-filter-field select {
++  min-height: 2.75rem;
++  min-width: 0;
++  border: 1px solid var(--yeyu-line);
++  border-radius: 0.25rem;
++  background: var(--yeyu-paper-strong);
++  padding-inline: 0.75rem;
++  color: var(--yeyu-ink);
++}
++
++.catalog-results {
++  margin-top: clamp(3rem, 6vw, 5rem);
++  padding-top: 2rem;
++  border-top: 1px solid var(--yeyu-line);
++}
++
++.catalog-refreshing {
++  margin-top: 1rem;
++}
++
++.catalog-grid {
++  display: grid;
++  grid-template-columns: repeat(2, minmax(0, 1fr));
++  gap: 1rem;
++  margin-top: 1.25rem;
++}
++
++.catalog-card {
++  display: grid;
++  min-width: 0;
++  gap: 1.1rem;
++  padding: 1.25rem;
++  border: 1px solid var(--yeyu-line);
++  border-top: 3px solid var(--yeyu-teal);
++  background: var(--yeyu-paper-strong);
++  transition:
++    border-color 160ms ease,
++    box-shadow 160ms ease,
++    transform 160ms ease;
++}
++
++.catalog-card:hover {
++  border-color: var(--yeyu-teal);
++  box-shadow: 0 10px 24px rgb(23 33 31 / 8%);
++  transform: translateY(-2px);
++}
++
++.catalog-card-path,
++.api-detail-path-row {
++  display: flex;
++  min-width: 0;
++  align-items: center;
++  gap: 0.65rem;
++  overflow-x: auto;
++  color: var(--yeyu-ink);
++  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
++  font-size: 0.85rem;
++  white-space: nowrap;
++}
++
++.catalog-card-path code,
++.api-detail-path-row code {
++  overflow: visible;
++}
++
++.catalog-method-badge {
++  flex: 0 0 auto;
++  color: var(--yeyu-teal);
++  font-size: 0.72rem;
++  font-weight: 800;
++  letter-spacing: 0.08em;
++}
++
++.catalog-card-content {
++  min-width: 0;
++}
++
++.catalog-card-title {
++  display: inline-block;
++  max-width: 100%;
++  overflow: hidden;
++  color: var(--yeyu-ink);
++  font-size: 1.2rem;
++  font-weight: 700;
++  text-overflow: ellipsis;
++  text-decoration: none;
++  white-space: nowrap;
++}
++
++.catalog-card-title:hover {
++  color: var(--yeyu-teal);
++  text-decoration: underline;
++  text-underline-offset: 0.2rem;
++}
++
++.catalog-card-summary {
++  margin-top: 0.5rem;
++  color: var(--yeyu-muted);
++  line-height: 1.65;
++}
++
++.catalog-card-meta,
++.api-detail-tags {
++  display: flex;
++  flex-wrap: wrap;
++  align-items: center;
++  gap: 0.45rem 0.6rem;
++  color: var(--yeyu-muted);
++  font-size: 0.76rem;
++}
++
++.catalog-tag {
++  display: inline-flex;
++  align-items: center;
++  min-height: 1.65rem;
++  padding-inline: 0.5rem;
++  border: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper);
++  color: var(--yeyu-muted);
++  font-size: 0.72rem;
++  font-weight: 700;
++}
++
++.catalog-tag-free {
++  border-color: var(--yeyu-teal);
++  color: var(--yeyu-teal);
++}
++
++.catalog-tag-status {
++  border-color: rgb(180 83 9 / 38%);
++  color: var(--yeyu-amber);
++}
++
++.catalog-state {
++  display: grid;
++  gap: 0.35rem;
++  margin-top: 1.25rem;
++  padding: 1.25rem;
++  border: 1px dashed var(--yeyu-line);
++  background: var(--yeyu-paper-strong);
++  color: var(--yeyu-muted);
++  line-height: 1.65;
++}
++
++.catalog-state-error {
++  display: flex;
++  align-items: center;
++  justify-content: space-between;
++  gap: 1rem;
++  border-color: var(--yeyu-amber);
++}
++
++.catalog-state-kicker {
++  color: var(--yeyu-ink);
++  font-weight: 700;
++}
++
++.catalog-skeleton-list {
++  min-height: 12rem;
++  align-content: center;
++}
++
++.catalog-skeleton-line {
++  display: block;
++  width: 68%;
++  height: 0.8rem;
++  background: var(--yeyu-mint);
++}
++
++.catalog-skeleton-line-wide {
++  width: 92%;
++  height: 1.4rem;
++}
++
++.catalog-skeleton-line-short {
++  width: 42%;
++}
++
++.catalog-detail-shell {
++  max-width: 86rem;
++}
++
++.api-detail-page {
++  min-width: 0;
++}
++
++.api-detail-breadcrumbs {
++  display: flex;
++  flex-wrap: wrap;
++  align-items: center;
++  gap: 0.65rem;
++  color: var(--yeyu-muted);
++  font-size: 0.82rem;
++}
++
++.api-detail-header {
++  max-width: 58rem;
++  padding-block: 2.25rem 3rem;
++}
++
++.api-detail-title {
++  margin-top: 1rem;
++  color: var(--yeyu-ink);
++  font-size: clamp(2.35rem, 6vw, 4.75rem);
++  font-weight: 700;
++  letter-spacing: -0.055em;
++  line-height: 1;
++}
++
++.api-detail-summary {
++  max-width: 48rem;
++  margin-top: 1rem;
++  color: var(--yeyu-muted);
++  font-size: 1.05rem;
++  line-height: 1.8;
++}
++
++.api-detail-tags {
++  margin-top: 1.25rem;
++}
++
++.api-detail-layout {
++  display: grid;
++  grid-template-columns: minmax(0, 1fr) minmax(15rem, 20rem);
++  gap: clamp(2rem, 6vw, 5rem);
++  align-items: start;
++}
++
++.api-detail-main {
++  min-width: 0;
++}
++
++.api-detail-section {
++  min-width: 0;
++  padding-block: 2.25rem;
++  border-top: 1px solid var(--yeyu-line);
++}
++
++.api-detail-section-title {
++  margin-top: 0.55rem;
++  color: var(--yeyu-ink);
++  font-size: 1.5rem;
++  font-weight: 700;
++  letter-spacing: -0.03em;
++}
++
++.api-detail-copy {
++  max-width: 52rem;
++  margin-top: 0.85rem;
++  color: var(--yeyu-muted);
++  line-height: 1.75;
++}
++
++.api-auth-callout {
++  display: flex;
++  flex-wrap: wrap;
++  align-items: center;
++  justify-content: space-between;
++  gap: 0.75rem;
++  margin-top: 1.25rem;
++  padding: 0.85rem 1rem;
++  border-left: 3px solid var(--yeyu-amber);
++  background: var(--yeyu-mint);
++  color: var(--yeyu-muted);
++  font-size: 0.82rem;
++}
++
++.api-auth-callout code {
++  overflow-x: auto;
++  color: var(--yeyu-ink);
++  white-space: nowrap;
++}
++
++.api-table-scroll {
++  max-width: 100%;
++  margin-top: 1.25rem;
++  overflow-x: auto;
++  border: 1px solid var(--yeyu-line);
++}
++
++.api-detail-table {
++  width: 100%;
++  min-width: 38rem;
++  border-collapse: collapse;
++  color: var(--yeyu-muted);
++  font-size: 0.86rem;
++  text-align: left;
++}
++
++.api-detail-table th,
++.api-detail-table td {
++  padding: 0.85rem 1rem;
++  border-bottom: 1px solid var(--yeyu-line);
++  vertical-align: top;
++}
++
++.api-detail-table thead th {
++  background: var(--yeyu-mint);
++  color: var(--yeyu-ink);
++  font-size: 0.75rem;
++  font-weight: 800;
++  letter-spacing: 0.05em;
++}
++
++.api-detail-table tbody th {
++  color: var(--yeyu-ink);
++  font-weight: 700;
++}
++
++.api-detail-table tr:last-child th,
++.api-detail-table tr:last-child td {
++  border-bottom: 0;
++}
++
++.api-table-note {
++  display: block;
++  max-width: 28rem;
++  margin-top: 0.35rem;
++  line-height: 1.55;
++}
++
++.api-detail-muted {
++  margin-top: 1rem;
++  color: var(--yeyu-muted);
++}
++
++.api-response-fields {
++  display: grid;
++  grid-template-columns: repeat(2, minmax(0, 1fr));
++  gap: 0.5rem;
++  margin-top: 1.25rem;
++}
++
++.api-response-field {
++  display: flex;
++  min-width: 0;
++  flex-wrap: wrap;
++  gap: 0.5rem;
++  align-items: center;
++  justify-content: space-between;
++  padding: 0.7rem 0.8rem;
++  border: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper-strong);
++  color: var(--yeyu-muted);
++  font-size: 0.8rem;
++}
++
++.api-response-field code {
++  color: var(--yeyu-ink);
++  font-weight: 700;
++}
++
++.api-json-block,
++.code-example-block {
++  max-width: 100%;
++  margin-top: 1rem;
++  overflow-x: auto;
++  border: 1px solid var(--yeyu-line);
++  background: var(--yeyu-ink);
++  padding: 1rem;
++  color: #eaf5f0;
++  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
++  font-size: 0.78rem;
++  line-height: 1.7;
++  white-space: pre;
++}
++
++.api-detail-aside {
++  display: grid;
++  gap: 1rem;
++  position: sticky;
++  top: 1.5rem;
++}
++
++.api-aside-card {
++  padding: 1.25rem;
++  border: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper-strong);
++}
++
++.api-aside-title {
++  margin-top: 0.55rem;
++  color: var(--yeyu-ink);
++  font-size: 1.1rem;
++  font-weight: 700;
++}
++
++.api-aside-value {
++  margin-top: 0.85rem;
++  color: var(--yeyu-teal);
++  font-weight: 700;
++}
++
++.api-cache-list {
++  display: grid;
++  gap: 0.75rem;
++  margin-top: 1rem;
++}
++
++.api-cache-list > div {
++  display: flex;
++  justify-content: space-between;
++  gap: 0.75rem;
++  padding-top: 0.75rem;
++  border-top: 1px solid var(--yeyu-line);
++  color: var(--yeyu-muted);
++  font-size: 0.8rem;
++}
++
++.api-cache-list dt {
++  color: var(--yeyu-ink);
++  font-weight: 700;
++}
++
++.api-cache-list dd {
++  max-width: 9rem;
++  overflow-wrap: anywhere;
++  text-align: right;
++}
++
++.api-code-grid {
++  display: grid;
++  gap: 1rem;
++  margin-top: 1.25rem;
++}
++
++.code-example {
++  min-width: 0;
++  border: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper-strong);
++}
++
++.code-example-header {
++  display: flex;
++  align-items: center;
++  justify-content: space-between;
++  gap: 1rem;
++  padding: 0.75rem 1rem;
++  border-bottom: 1px solid var(--yeyu-line);
++}
++
++.code-example-header h3 {
++  color: var(--yeyu-ink);
++  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
++  font-size: 0.82rem;
++  font-weight: 800;
++}
++
++.code-copy-button {
++  display: inline-flex;
++  min-height: 2.25rem;
++  align-items: center;
++  gap: 0.4rem;
++  border: 1px solid var(--yeyu-line);
++  background: var(--yeyu-paper);
++  padding: 0.4rem 0.65rem;
++  color: var(--yeyu-teal);
++  font-size: 0.78rem;
++  font-weight: 700;
++}
++
++.code-copy-button svg {
++  height: 0.9rem;
++  width: 0.9rem;
++}
++
++.code-example-block {
++  margin-top: 0;
++  border: 0;
++}
++
++.code-example-feedback {
++  min-height: 1.5rem;
++  padding: 0 1rem 0.65rem;
++  color: var(--yeyu-teal);
++  font-size: 0.75rem;
++}
++
+ @media (min-width: 768px) {
+   .public-hero {
+     grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.65fr);
+     align-items: end;
+   }
+ }
+ 
+ @media (max-width: 767px) {
+   .public-section-heading,
++  .catalog-search-heading,
++  .catalog-results-heading,
+   .public-bottom-cta {
+     align-items: flex-start;
+     flex-direction: column;
+   }
+ 
+   .public-catalog-row,
+-  .public-usage-section {
++  .public-usage-section,
++  .catalog-filters,
++  .catalog-filter-controls,
++  .api-detail-layout {
+     grid-template-columns: 1fr;
+   }
+ 
++  .catalog-grid,
++  .api-response-fields {
++    grid-template-columns: 1fr;
++  }
++
++  .catalog-search-hint {
++    margin-top: -0.5rem;
++  }
++
+   .public-catalog-meta {
+     justify-content: flex-start;
+     text-align: left;
+   }
++
++  .api-detail-aside {
++    position: static;
++  }
++
++  .api-auth-callout {
++    align-items: flex-start;
++    flex-direction: column;
++  }
+ }
+ 
+ @media (prefers-reduced-motion: reduce) {
+   *,
+   *::before,
+   *::after {
+     scroll-behavior: auto;
+     transition: none;
+     animation: none;
+   }
+diff --git a/frontend/src/routes/catalog/$slug.tsx b/frontend/src/routes/catalog/$slug.tsx
+new file mode 100644
+index 0000000..5c51950
+--- /dev/null
++++ b/frontend/src/routes/catalog/$slug.tsx
+@@ -0,0 +1,46 @@
++import { useQuery } from "@tanstack/react-query"
++import { createFileRoute } from "@tanstack/react-router"
++
++import { CatalogService } from "@/client"
++import ApiDetailView from "@/components/ApiCatalog/ApiDetailView"
++import {
++  CatalogDetailErrorState,
++  CatalogLoadingState,
++} from "@/components/ApiCatalog/CatalogStates"
++import PublicLayout from "@/components/PublicSite/PublicLayout"
++
++export const Route = createFileRoute("/catalog/$slug")({
++  component: CatalogDetailRoute,
++  head: () => ({
++    meta: [
++      {
++        title: "API 详情 - Yeyu API",
++      },
++    ],
++  }),
++})
++
++function CatalogDetailRoute() {
++  const { slug } = Route.useParams()
++  const detailQuery = useQuery({
++    queryKey: ["public-catalog-detail", slug],
++    queryFn: async () => {
++      const response = await CatalogService.getCatalogDetail({
++        path: { slug },
++      })
++      return response.data
++    },
++  })
++
++  return (
++    <PublicLayout>
++      <div className="public-container catalog-detail-shell">
++        {detailQuery.isPending ? <CatalogLoadingState /> : null}
++        {detailQuery.isError ? (
++          <CatalogDetailErrorState onRetry={() => void detailQuery.refetch()} />
++        ) : null}
++        {detailQuery.data ? <ApiDetailView detail={detailQuery.data} /> : null}
++      </div>
++    </PublicLayout>
++  )
++}
+diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
+index a0084bb..f83b403 100644
+--- a/frontend/src/routes/catalog/index.tsx
++++ b/frontend/src/routes/catalog/index.tsx
+@@ -1,45 +1,155 @@
+-import { createFileRoute, Link } from "@tanstack/react-router"
++import { useQuery } from "@tanstack/react-query"
++import { createFileRoute } from "@tanstack/react-router"
++import { useEffect, useState } from "react"
+ 
++import { type CatalogPage, CatalogService } from "@/client"
++import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
++import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
++import CatalogSearch from "@/components/ApiCatalog/CatalogSearch"
++import {
++  CatalogEmptyState,
++  CatalogErrorState,
++  CatalogLoadingState,
++} from "@/components/ApiCatalog/CatalogStates"
++import {
++  type CatalogSearchParams,
++  normalizeSearchValue,
++  parseCatalogSearch,
++} from "@/components/ApiCatalog/catalog-types"
+ import PublicLayout from "@/components/PublicSite/PublicLayout"
+ 
+ export const Route = createFileRoute("/catalog/")({
+-  component: CatalogPlaceholder,
++  validateSearch: (search): CatalogSearchParams => parseCatalogSearch(search),
++  component: CatalogRoutePage,
+   head: () => ({
+     meta: [
+       {
+         title: "API 目录 - Yeyu API",
+       },
+     ],
+   }),
+ })
+ 
+-function CatalogPlaceholder() {
++function CatalogRoutePage() {
++  const search = Route.useSearch()
++  const navigate = Route.useNavigate()
++  const [draftQuery, setDraftQuery] = useState(search.query ?? "")
++
++  useEffect(() => {
++    setDraftQuery(search.query ?? "")
++  }, [search.query])
++
++  useEffect(() => {
++    const normalizedQuery = normalizeSearchValue(draftQuery)
++    if (normalizedQuery === search.query) return
++
++    const timeoutId = window.setTimeout(() => {
++      void navigate({
++        search: (previous) => ({
++          ...previous,
++          query: normalizedQuery,
++        }),
++        replace: true,
++      })
++    }, 400)
++
++    return () => window.clearTimeout(timeoutId)
++  }, [draftQuery, navigate, search.query])
++
++  const catalogQuery = useQuery<CatalogPage>({
++    queryKey: [
++      "public-catalog",
++      search.query ?? "",
++      search.category ?? "",
++      search.status ?? "",
++    ],
++    queryFn: async () => {
++      const response = await CatalogService.searchCatalog({
++        query: {
++          query: search.query,
++          category: search.category,
++          status: search.status,
++          page: 1,
++          page_size: 20,
++        },
++      })
++      return response.data
++    },
++  })
++
++  const items = catalogQuery.data?.data ?? []
++  const updateFilter = (key: "category" | "status", value: string) => {
++    void navigate({
++      search: (previous) => ({
++        ...previous,
++        [key]: normalizeSearchValue(value),
++      }),
++      replace: true,
++    })
++  }
++
+   return (
+     <PublicLayout>
+-      <div className="public-container py-16 sm:py-24">
++      <div className="public-container catalog-page-shell">
++        <header className="catalog-page-header">
++          <p className="public-eyebrow">公开目录 / REAL DATA</p>
++          <h1 className="catalog-page-title">API 目录</h1>
++          <p className="catalog-page-lede">
++            只展示后端公开、健康或已发布的真实接口。先搜索，再阅读完整调用契约。
++          </p>
++        </header>
++
++        <CatalogSearch value={draftQuery} onChange={setDraftQuery} />
++        <CatalogFilters
++          items={items}
++          category={search.category}
++          status={search.status}
++          onCategoryChange={(value) => updateFilter("category", value)}
++          onStatusChange={(value) => updateFilter("status", value)}
++        />
++
+         <section
+-          className="public-state mx-auto max-w-2xl text-center"
+-          aria-labelledby="catalog-placeholder-heading"
+-          data-testid="catalog-placeholder"
++          className="catalog-results"
++          aria-labelledby="catalog-results-heading"
+         >
+-          <p className="public-eyebrow">公开目录</p>
+-          <h1
+-            id="catalog-placeholder-heading"
+-            className="public-section-title mt-3"
+-          >
+-            API 目录建设中
+-          </h1>
+-          <p className="public-section-copy mx-auto mt-4 max-w-xl">
+-            由公开目录驱动的真实接口条目将在下一阶段开放，当前先保留清晰的公共入口。
+-          </p>
+-          <p className="mt-3 text-sm text-[var(--yeyu-muted)]">
+-            目录建设中，请稍后再来查看。
+-          </p>
+-          <Link to="/" className="public-primary-button mt-8 inline-flex">
+-            返回首页
+-          </Link>
++          <div className="catalog-results-heading">
++            <div>
++              <p className="public-eyebrow">RESULTS</p>
++              <h2
++                id="catalog-results-heading"
++                className="catalog-results-title"
++              >
++                可用接口
++              </h2>
++            </div>
++            {catalogQuery.data ? (
++              <p className="catalog-results-count">
++                共 {catalogQuery.data.count} 条
++              </p>
++            ) : null}
++          </div>
++
++          {catalogQuery.isFetching && !catalogQuery.isPending ? (
++            <p className="catalog-refreshing" role="status">
++              正在更新目录……
++            </p>
++          ) : null}
++          {catalogQuery.isPending ? <CatalogLoadingState /> : null}
++          {catalogQuery.isError ? (
++            <CatalogErrorState onRetry={() => void catalogQuery.refetch()} />
++          ) : null}
++          {!catalogQuery.isPending &&
++          !catalogQuery.isError &&
++          items.length === 0 ? (
++            <CatalogEmptyState />
++          ) : null}
++          {!catalogQuery.isPending &&
++          !catalogQuery.isError &&
++          items.length > 0 ? (
++            <CatalogGrid items={items} />
++          ) : null}
+         </section>
+       </div>
+     </PublicLayout>
+   )
+ }
+diff --git a/frontend/src/routes/index.tsx b/frontend/src/routes/index.tsx
+index ae23cfe..2067555 100644
+--- a/frontend/src/routes/index.tsx
++++ b/frontend/src/routes/index.tsx
+@@ -1,38 +1,28 @@
+ import { useQuery } from "@tanstack/react-query"
+ import { createFileRoute, Link } from "@tanstack/react-router"
+ 
+ import { CatalogService } from "@/client"
++import { formatUpdatedAt } from "@/components/ApiCatalog/catalog-types"
+ import PublicLayout from "@/components/PublicSite/PublicLayout"
+ 
+ export const Route = createFileRoute("/")({
+   component: PublicHome,
+   head: () => ({
+     meta: [
+       {
+         title: "Yeyu API 公益工具箱",
+       },
+     ],
+   }),
+ })
+ 
+-function formatUpdatedAt(value?: string | null) {
+-  if (!value) return "更新时间待补充"
+-
+-  const timestamp = Date.parse(value)
+-  if (Number.isNaN(timestamp)) return value
+-
+-  return new Intl.DateTimeFormat("zh-HK", {
+-    dateStyle: "medium",
+-  }).format(new Date(timestamp))
+-}
+-
+ function CatalogPreview() {
+   const catalogQuery = useQuery({
+     queryKey: ["public-catalog-preview"],
+     queryFn: async () => {
+       const response = await CatalogService.searchCatalog({
+         query: {
+           page: 1,
+           page_size: 4,
+         },
+       })
+@@ -51,23 +41,23 @@ function CatalogPreview() {
+       <div className="public-section-heading">
+         <div>
+           <p className="public-eyebrow">目录入口</p>
+           <h2 id="catalog-heading" className="public-section-title">
+             从真实目录开始
+           </h2>
+           <p className="public-section-copy">
+             这里展示后端公开目录中的接口，不展示虚构卡片或调用统计。
+           </p>
+         </div>
+-        <a className="public-text-link" href="/catalog">
++        <Link className="public-text-link" to="/catalog">
+           搜索完整目录 <span aria-hidden="true">→</span>
+-        </a>
++        </Link>
+       </div>
+ 
+       {catalogQuery.isPending ? (
+         <p className="public-state" role="status">
+           正在读取真实目录……
+         </p>
+       ) : null}
+ 
+       {catalogQuery.isError ? (
+         <div className="public-state public-state-error" role="alert">
+@@ -91,28 +81,36 @@ function CatalogPreview() {
+       {!catalogQuery.isPending && !catalogQuery.isError && items.length > 0 ? (
+         <ul className="public-catalog-list" data-testid="catalog-preview-list">
+           {items.map((item) => (
+             <li key={item.slug} className="public-catalog-row">
+               <div className="public-path-line">
+                 <span className="public-method-badge">{item.method}</span>
+                 <code>{item.path}</code>
+               </div>
+               <div className="min-w-0">
+                 <h3 className="truncate text-base font-semibold text-[var(--yeyu-ink)]">
+-                  {item.name}
++                  <Link
++                    to="/catalog/$slug"
++                    params={{ slug: item.slug }}
++                    className="public-catalog-title-link"
++                  >
++                    {item.name}
++                  </Link>
+                 </h3>
+                 <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
+                   {item.summary}
+                 </p>
+               </div>
+               <div className="public-catalog-meta">
+                 <span>{item.category}</span>
++                {item.is_free ? <span>免费</span> : null}
++                <span>{item.status}</span>
+                 <time dateTime={item.updated_at ?? undefined}>
+                   {formatUpdatedAt(item.updated_at)}
+                 </time>
+               </div>
+             </li>
+           ))}
+         </ul>
+       ) : null}
+     </section>
+   )
+@@ -132,21 +130,21 @@ function PublicHome() {
+               从清楚的接口文档开始，按公开规范调用稳定、可核验的自营工具。
+             </p>
+             <form className="public-search-form" action="/catalog" method="get">
+               <label className="sr-only" htmlFor="catalog-query">
+                 搜索 API 目录
+               </label>
+               <input
+                 id="catalog-query"
+                 name="query"
+                 className="public-search-input"
+-                placeholder="搜索时间戳、UUID、天气……"
++                placeholder="搜索时间、UUID 等公开接口……"
+                 type="search"
+               />
+               <button className="public-primary-button" type="submit">
+                 搜索 API 目录
+               </button>
+             </form>
+             <nav className="public-hero-links" aria-label="快速入口">
+               <a className="public-text-link" href="/catalog">
+                 浏览公开目录 <span aria-hidden="true">↗</span>
+               </a>
+diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
+index ac5f343..39af2f7 100644
+--- a/frontend/tests/public-catalog.spec.ts
++++ b/frontend/tests/public-catalog.spec.ts
+@@ -1,54 +1,251 @@
+-import { expect, test } from "@playwright/test"
++import { expect, type Page, test } from "@playwright/test"
+ 
+ test.use({ storageState: { cookies: [], origins: [] } })
+ 
+-test("Anonymous users can open the public home without login redirect", async ({
+-  page,
+-}) => {
+-  await page.goto("/")
++const timeItem = {
++  slug: "time",
++  name: "时间查询",
++  summary: "按可选 IANA 时区返回当前 UTC、Unix 时间戳和本地时间。",
++  category: "tools",
++  method: "GET",
++  path: "/v1/tools/time",
++  auth_type: "api_key",
++  is_free: true,
++  status: "published",
++  updated_at: "2026-10-02T00:00:00Z",
++}
++
++const uuidItem = {
++  slug: "uuid",
++  name: "UUID v4 生成器",
++  summary: "生成一个随机 UUID v4，不接受任何查询参数。",
++  category: "tools",
++  method: "GET",
++  path: "/v1/tools/uuid",
++  auth_type: "api_key",
++  is_free: true,
++  status: "published",
++  updated_at: "2026-10-02T00:00:00Z",
++}
++
++const timeDetail = {
++  ...timeItem,
++  auth: { type: "api_key", header: "X-API-Key" },
++  parameters: [
++    {
++      name: "timezone",
++      in: "query",
++      required: false,
++      description: "可选的 IANA 时区名称，省略时使用 UTC。",
++      schema: {
++        type: "string",
++        default: "UTC",
++        examples: ["UTC", "Asia/Shanghai"],
++      },
++    },
++  ],
++  response_schema: {
++    type: "object",
++    properties: {
++      utc: { type: "string", format: "date-time" },
++      unix_timestamp: { type: "number" },
++      timezone: { type: "string" },
++      local: { type: "string", format: "date-time" },
++    },
++    required: ["utc", "unix_timestamp", "timezone", "local"],
++  },
++  errors: [
++    {
++      status: 401,
++      code: "API_KEY_REQUIRED",
++      description: "请求必须提供 X-API-Key。",
++    },
++    { status: 404, code: "API_NOT_FOUND", description: "接口不存在或未公开。" },
++  ],
++  examples: [
++    {
++      language: "curl",
++      request:
++        'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
++    },
++  ],
++  source: "Yeyu API",
++  cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
++}
++
++type CatalogPage = {
++  data: (typeof timeItem)[]
++  count: number
++  page: number
++  page_size: number
++}
++
++async function mockCatalogApi(page: Page) {
++  await page.route("**/api/v1/catalog*", async (route) => {
++    const url = new URL(route.request().url())
++
++    if (url.pathname.endsWith("/time")) {
++      await route.fulfill({
++        status: 200,
++        contentType: "application/json",
++        body: JSON.stringify(timeDetail),
++      })
++      return
++    }
++
++    const query = url.searchParams.get("query") ?? ""
++    const category = url.searchParams.get("category")
++    const status = url.searchParams.get("status")
++    const data =
++      query === "missing"
++        ? []
++        : query === "uuid"
++          ? [uuidItem]
++          : [timeItem, uuidItem]
++    const filtered = data.filter(
++      (item) =>
++        (!category || item.category === category) &&
++        (!status || item.status === status),
++    )
++    const response: CatalogPage = {
++      data: filtered,
++      count: filtered.length,
++      page: 1,
++      page_size: 20,
++    }
+ 
+-  await expect(page).toHaveURL(/\/$/)
++    await route.fulfill({
++      status: 200,
++      contentType: "application/json",
++      body: JSON.stringify(response),
++    })
++  })
++}
++
++test("Anonymous users can browse the real public catalog", async ({ page }) => {
++  await mockCatalogApi(page)
++  await page.goto("/catalog")
++
++  await expect(page).toHaveURL("/catalog")
++  await expect(page.getByRole("heading", { name: "API 目录" })).toBeVisible()
++  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
++  await expect(page.getByTestId("catalog-card-time")).toContainText(
++    "/v1/tools/time",
++  )
++  await expect(page.getByText("免费", { exact: true }).first()).toBeVisible()
+   await expect(
+-    page.getByRole("heading", {
+-      name: "给学生和个人开发者的免费 API 工具箱",
+-    }),
++    page.getByText("published", { exact: true }).first(),
+   ).toBeVisible()
+-  await expect(page).not.toHaveURL(/\/login/)
++  await expect(page.getByRole("link", { name: /时间查询/ })).toHaveAttribute(
++    "href",
++    "/catalog/time",
++  )
+ })
+ 
+-test("Anonymous users can open the public catalog placeholder", async ({
++test("Catalog search is debounced and filters are shareable in the URL", async ({
+   page,
+ }) => {
++  const catalogRequests: string[] = []
++  await page.route("**/api/v1/catalog*", async (route) => {
++    const url = new URL(route.request().url())
++    if (url.pathname.endsWith("/time")) {
++      await route.fulfill({
++        status: 200,
++        contentType: "application/json",
++        body: JSON.stringify(timeDetail),
++      })
++      return
++    }
++    catalogRequests.push(url.search)
++    const item = url.searchParams.get("query") === "uuid" ? uuidItem : timeItem
++    await route.fulfill({
++      status: 200,
++      contentType: "application/json",
++      body: JSON.stringify({ data: [item], count: 1, page: 1, page_size: 20 }),
++    })
++  })
++
+   await page.goto("/catalog")
++  const searchInput = page.getByRole("searchbox", { name: "搜索公开 API" })
++  await searchInput.fill("uuid")
++  await page.waitForTimeout(150)
++  expect(
++    catalogRequests.filter((request) => request.includes("query=uuid")),
++  ).toHaveLength(0)
++  await expect(page).toHaveURL(/\/catalog\?query=uuid$/)
++  await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
+ 
+-  await expect(page).toHaveURL("/catalog")
++  await page.getByLabel("分类").selectOption("tools")
++  await expect(page).toHaveURL(/query=uuid.*category=tools/)
++  await page.getByLabel("状态").selectOption("published")
++  await expect(page).toHaveURL(/query=uuid.*category=tools.*status=published/)
++})
++
++test("Catalog displays an explicit empty state for an empty result", async ({
++  page,
++}) => {
++  await mockCatalogApi(page)
++  await page.goto("/catalog?query=missing")
++
++  await expect(page.getByTestId("catalog-empty")).toBeVisible()
++  await expect(page.getByText("没有找到匹配的公开接口")).toBeVisible()
++  await expect(page.getByTestId("catalog-grid")).not.toBeVisible()
++})
++
++test("Time detail documents the request contract and safe code examples", async ({
++  page,
++}) => {
++  await mockCatalogApi(page)
++  await page.goto("/catalog/time")
++
++  await expect(page).toHaveURL("/catalog/time")
++  await expect(page.getByRole("heading", { name: "时间查询" })).toBeVisible()
++  await expect(page.getByText("/v1/tools/time", { exact: true })).toBeVisible()
++  await expect(page.getByText("GET", { exact: true }).first()).toBeVisible()
+   await expect(
+-    page.getByRole("heading", { name: "API 目录建设中" }),
++    page.getByText("API Key", { exact: false }).first(),
+   ).toBeVisible()
+-  await expect(page.getByText("由公开目录驱动")).toBeVisible()
+-  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
++  await expect(page.getByText("timezone", { exact: true })).toBeVisible()
++  await expect(page.getByText("utc", { exact: true })).toBeVisible()
++  await expect(page.getByText("unix_timestamp", { exact: true })).toBeVisible()
++  await expect(
++    page.getByText("API_KEY_REQUIRED", { exact: true }),
++  ).toBeVisible()
++  await expect(page.getByText("Yeyu API", { exact: true })).toBeVisible()
++  await expect(page.getByRole("heading", { name: "curl" })).toBeVisible()
++  await expect(page.getByRole("heading", { name: "JavaScript" })).toBeVisible()
++  await expect(page.getByRole("heading", { name: "Python" })).toBeVisible()
++  await expect(
++    page.locator("code").filter({ hasText: "<YOUR_API_KEY>" }).first(),
++  ).toBeVisible()
++  await expect(
++    page.locator("code").filter({ hasText: "api.yeyubaka.top" }).first(),
++  ).toBeVisible()
++
++  const copyButton = page.getByRole("button", { name: "复制 curl 示例" })
++  await expect(copyButton).toBeVisible()
++  await copyButton.click()
++  await expect(copyButton).toContainText("已复制")
+ })
+ 
+-test("Public navigation exposes keyboard-accessible catalog and login links", async ({
++test("Public navigation remains keyboard accessible on mobile", async ({
+   page,
+ }) => {
+   await page.setViewportSize({ width: 390, height: 844 })
++  await mockCatalogApi(page)
+   await page.goto("/")
+ 
+   const navigation = page.getByRole("navigation", { name: "公共导航" })
+   const menuButton = navigation.getByRole("button", { name: /菜单/ })
+ 
+   await expect(navigation).toBeVisible()
+   await expect(menuButton).toHaveAttribute("aria-expanded", "true")
+ 
+   await menuButton.press("Enter")
+   await expect(menuButton).toHaveAttribute("aria-expanded", "false")
+ 
+   await menuButton.press("Space")
+   await expect(menuButton).toHaveAttribute("aria-expanded", "true")
+   await expect(navigation.getByRole("link", { name: "API 目录" })).toBeVisible()
+   await expect(navigation.getByRole("link", { name: "登录" })).toBeVisible()
+-
+-  await navigation.getByRole("link", { name: "登录" }).focus()
+-  await expect(navigation.getByRole("link", { name: "登录" })).toBeFocused()
+ })
+diff --git a/plans/agent-reports/task-7-3-brief.md b/plans/agent-reports/task-7-3-brief.md
+new file mode 100644
+index 0000000..67f06a2
+--- /dev/null
++++ b/plans/agent-reports/task-7-3-brief.md
+@@ -0,0 +1,58 @@
++## Task 3: Build Search-First Catalog and Detail Pages
++
++**Files:**
++
++- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx
++- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx
++- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts
++- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogSearch.tsx
++- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogFilters.tsx
++- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogCard.tsx
++- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogGrid.tsx
++- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogStates.tsx
++- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx
++- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CodeExample.tsx
++- Modify E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
++- Modify E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
++- Modify E:\AI_projects\yeyu-api\frontend\src\index.css
++- Modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
++
++### Implementation
++
++- [ ] 在测试中覆盖目录页匿名可访问、搜索参数能反映到 URL、分类筛选能反映到 URL、空结果有明确状态、详情页展示 /v1/tools/time、GET、API Key 鉴权、参数、响应字段和错误码。
++- [ ] 目录页通过生成的 CatalogService.getCatalog 和 React Query 获取分页数据，query、category、status 使用 TanStack Router search params 作为唯一可分享状态；输入搜索设置 300 至 500 毫秒防抖并避免逐键请求。
++- [ ] 目录页首屏顺序固定为页面标题与搜索框、分类/状态筛选、真实目录卡片；卡片包含名称、中文简介、请求方法、路径、免费标记、健康/发布状态和更新时间，点击后进入 /catalog/:slug。
++- [ ] 目录页只展示后端返回数据，不在前端硬编码候选接口；API 返回空、错误和加载状态分别使用可读的 Empty、Error、Skeleton 组件。
++- [ ] 详情页通过生成的 CatalogService.getCatalogDetail({ path: { slug } }) 获取数据；展示鉴权说明、参数表、响应结构、错误码、缓存规则、来源标签和 curl、JavaScript、Python 示例。
++- [ ] 代码示例只显示 <YOUR_API_KEY>，统一从当前域名拼接请求 URL，不保存或读取真实 API Key，不提供任意 URL 输入；复制按钮使用可访问名称并在成功后有非颜色反馈。
++- [ ] 首页保持索引台视觉：上方以一句清晰定位和主搜索入口为主，下面展示由真实目录 API 返回的精选工具卡片、一个可直接跳转的 Quick Start 区块和公益/使用边界说明；不展示假统计。
++- [ ] 公共导航在首页、目录页和详情页保持一致；目录页搜索框支持从首页带 query 参数跳转后继续搜索。
++- [ ] 移动端将详情页的参数表、代码块和路径行处理为可横向滚动而不撑破页面；桌面端使用窄内容列、明显分隔线和稳定状态色。
++
++### Verification
++
++- [ ] 执行前端构建与静态检查：
++
++~~~powershell
++Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
++pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
++pnpm build
++~~~
++
++- [ ] 在项目 Docker Compose 测试环境可用时执行：
++
++~~~powershell
++Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
++pnpm exec playwright test tests/public-catalog.spec.ts
++~~~
++
++- [ ] 通过 API 测试确认种子后端实际提供目录数据：
++
++~~~powershell
++conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py -q
++~~~
++
++- [ ] 使用真实浏览器尺寸至少检查 1280 像素桌面视口和 390 像素移动视口；记录页面 URL、公开/受保护结果、控制台错误和截图路径。截图若用于审查，只放在项目外部临时目录。
++- [ ] 独立只读子代理检查 API client 使用、URL 状态同步、错误/空状态、示例密钥脱敏、移动端溢出、可访问性和视觉方案偏离，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-review.md。
++- [ ] 处理审查问题后重跑构建、API 测试和浏览器测试，创建提交 feat: add public catalog and api detail pages 并推送 origin/main。
++
+diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
+new file mode 100644
+index 0000000..aaab69a
+--- /dev/null
++++ b/plans/agent-reports/task-7-3-report.md
+@@ -0,0 +1,135 @@
++# Task 3：公共目录与 API 详情页实现报告
++
++日期：2026-10-02
++项目：`E:\AI_projects\yeyu-api`
++实现提交：`c13adce`
++
++## 1. 实现范围
++
++本次完成公共目录从占位页到真实搜索优先目录，以及公开 API 详情页：
++
++- 目录页通过生成的 `CatalogService.searchCatalog` 和 React Query 请求后端公开目录；只渲染 API 返回的 `CatalogItem`。
++- `query` 使用 400ms 防抖同步到 TanStack Router search params；`category`、`status` 立即同步 URL，并作为 React Query key 的一部分。
++- 卡片展示名称、简介、方法、路径、免费标记、后端状态和更新时间，并链接到 `/catalog/:slug`。
++- 分别实现加载、错误、空结果状态；空结果不创建前端候选卡片。
++- 新增 `/catalog/$slug` 详情路由，使用 `CatalogService.getCatalogDetail({ path: { slug } })`。
++- 详情展示 API Key 鉴权、参数表、响应字段和 schema、错误码、缓存规则、来源，以及 curl、JavaScript、Python 示例。
++- 所有示例只使用 `<YOUR_API_KEY>`；JavaScript 使用当前页面 origin，curl/Python 使用正式 API 域名；未读取 localStorage、Cookie 或真实 API Key。
++- 首页预览继续使用真实目录 API，并补充详情链接、真实状态/更新时间和搜索跳转入口。
++- 公共导航改为 TanStack Router 链接；详情路径、表格和代码块在窄视口使用滚动/换行边界。
++- 未修改 `frontend/src/routeTree.gen.ts`，未修改 dashboard 保护或认证逻辑，未实现在线调试和 API Key 管理 UI。
++
++## 2. 修改文件
++
++- `frontend/src/components/ApiCatalog/catalog-types.ts`
++- `frontend/src/components/ApiCatalog/CatalogSearch.tsx`
++- `frontend/src/components/ApiCatalog/CatalogFilters.tsx`
++- `frontend/src/components/ApiCatalog/CatalogCard.tsx`
++- `frontend/src/components/ApiCatalog/CatalogGrid.tsx`
++- `frontend/src/components/ApiCatalog/CatalogStates.tsx`
++- `frontend/src/components/ApiCatalog/ApiDetailView.tsx`
++- `frontend/src/components/ApiCatalog/CodeExample.tsx`
++- `frontend/src/routes/catalog/index.tsx`
++- `frontend/src/routes/catalog/$slug.tsx`
++- `frontend/src/routes/index.tsx`
++- `frontend/src/components/PublicSite/PublicHeader.tsx`
++- `frontend/src/components/PublicSite/PublicFooter.tsx`
++- `frontend/src/index.css`
++- `frontend/tests/public-catalog.spec.ts`
++
++任务简报 `plans/agent-reports/task-7-3-brief.md` 是用户提供的未跟踪文件，本次未修改、未提交。
++
++## 3. TDD RED/GREEN 证据
++
++### RED
++
++先更新了 `frontend/tests/public-catalog.spec.ts`，覆盖：匿名目录、搜索参数 URL 同步、防抖、分类/状态筛选 URL、空结果、`/catalog/time`、`/v1/tools/time`、GET、API Key、`timezone`、响应字段、错误码、三种代码示例和复制反馈。
++
++真实命令与结果：
++
++```text
++pnpm exec playwright test tests/public-catalog.spec.ts
++exit 1
++Error: Environment variable FIRST_SUPERUSER is undefined
++```
++
++仅在进程内注入非真实测试值后重试：
++
++```text
++$env:FIRST_SUPERUSER='<NON_SECRET_TEST_EMAIL>'; $env:FIRST_SUPERUSER_PASSWORD='<NON_SECRET_TEST_VALUE>'; pnpm exec playwright test tests/public-catalog.spec.ts
++exit 1
++browserType.launch: Executable doesn't exist ... chrome-headless-shell.exe
++1 failed [setup] auth.setup.ts; 5 did not run
++```
++
++随后执行了依赖安装：
++
++```text
++pnpm exec playwright install chromium
++exit 0
++Chrome for Testing and Chrome Headless Shell downloaded to the Playwright user cache
++```
++
++安装后再次以同样的非真实进程值运行：
++
++```text
++exit 1
++Test timeout of 30000ms exceeded
++at tests/auth.setup.ts:8:41, waiting for getByTestId('email-input')
++1 failed [setup] auth.setup.ts; 5 did not run
++```
++
++因此 RED 阶段有测试收集/环境阻塞证据，但目标目录断言没有进入浏览器执行。
++
++### GREEN
++
++已完成对应静态实现，并执行 Biome 作为快速静态门禁；没有运行 Playwright/build，故不能宣称浏览器 GREEN、类型检查 GREEN 或产品验收 GREEN。
++
++## 4. 静态验证
++
++首次对 `src tests` 执行 Biome 的真实结果：
++
++```text
++exit 1
++Checked 73 files in 46ms. No fixes applied.
++Found 14 errors.
++Found 2 warnings.
++```
++
++错误集中在新增 JSX 格式、无效 div `aria-label`、搜索容器 role，以及 CSS 特异性顺序。修正后只对本次改动的 15 个文件执行：
++
++```text
++pnpm exec biome check --write --no-errors-on-unmatched --files-ignore-unknown=true <15 absolute paths>
++exit 0
++Checked 15 files in 18ms. Fixed 9 files.
++
++pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true <15 absolute paths>
++exit 0
++Checked 15 files in 14ms. No fixes applied.
++```
++
++另执行 `git diff --check`，未发现空白错误；Git 仅提示 Windows 工作树的 LF/CRLF 转换警告。
++
++## 5. 未验证阻塞与边界
++
++- Playwright 被既有 `auth.setup.ts` 的认证 setup 阻塞；缺少浏览器已安装，但 setup 后续仍在登录页 `email-input` 等待超时。未把 setup 失败算作目录测试通过。
++- 按用户本次要求未运行 `pnpm build`，未运行后端 pytest，也未做真实浏览器桌面/移动截图验收。
++- 未运行 Vite 官方路由生成链，因此 `routeTree.gen.ts` 仍保持未手改状态；新增路由是否被生成链和 TypeScript 完整接纳需要后续 build/开发服务器验证。
++- 未执行线上验收、DNS/Nginx/SMTP/GitHub OAuth 或生产部署；没有触碰旧项目、线上服务和凭据。
++
++## 6. Self-review
++
++- [x] 目录卡片由 `CatalogService` 返回数据驱动，无硬编码接口卡片。
++- [x] 目录搜索和筛选状态可分享，搜索防抖为 400ms。
++- [x] 详情页使用生成 client 的 path slug 形态，展示真实 schema/参数/错误/缓存/来源字段。
++- [x] 示例只包含 `<YOUR_API_KEY>`，没有新增浏览器凭据读取或在线调用控件。
++- [x] 复制按钮有可访问名称，成功状态有文字和图标反馈。
++- [x] 移动端表格、路径和代码块设置横向滚动边界。
++- [x] Biome 最终对本次 15 个文件通过。
++- [ ] Playwright、build、pytest 和真实浏览器验收：受用户要求/现有 setup 阻塞，未验证。
++
++## 7. 提交
++
++实现代码提交主题：`feat: add public catalog and api detail pages`
++
++提交 SHA：`c13adce`（实现提交；报告随后单独提交）。
diff --git a/plans/agent-reports/task-7-3-fix-diff.md b/plans/agent-reports/task-7-3-fix-diff.md
new file mode 100644
index 0000000..c28a1db
--- /dev/null
+++ b/plans/agent-reports/task-7-3-fix-diff.md
@@ -0,0 +1,1100 @@
+# Review package: ec82905..04fcbd4
+
+## Commits
+04fcbd4 fix: close catalog review findings
+
+## Files changed
+ .../src/components/ApiCatalog/ApiDetailView.tsx    |  81 ++++++---
+ .../components/ApiCatalog/CatalogPagination.tsx    |  45 +++++
+ .../src/components/ApiCatalog/catalog-types.ts     |  91 +++++++++-
+ frontend/src/index.css                             |  15 ++
+ frontend/src/routes/catalog/$slug.tsx              |   8 +-
+ frontend/src/routes/catalog/index.tsx              |  22 ++-
+ frontend/tests/public-catalog.spec.ts              | 193 ++++++++++++++++++---
+ plans/agent-reports/task-7-3-report.md             |  65 +++++++
+ plans/fix-task-7-3-catalog-review-findings.md      |  67 +++++++
+ 9 files changed, 530 insertions(+), 57 deletions(-)
+
+## Diff
+diff --git a/frontend/src/components/ApiCatalog/ApiDetailView.tsx b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+index 83a7ef8..7c7f036 100644
+--- a/frontend/src/components/ApiCatalog/ApiDetailView.tsx
++++ b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+@@ -1,57 +1,75 @@
+ import { Link } from "@tanstack/react-router"
+ 
+ import type { ApiDetail } from "@/client"
+ 
+ import CodeExample from "./CodeExample"
+ import {
+   asRecord,
+   asText,
++  buildPublicApiUrl,
+   formatMetadata,
+   formatUpdatedAt,
++  normalizeInternalApiPath,
++  PUBLIC_API_BASE_URL,
+   responseProperties,
++  sanitizeMetadata,
+ } from "./catalog-types"
+ 
+ type QueryExample = {
+   name: string
+   value: string
+ }
+ 
+ function parameterExamples(detail: ApiDetail): QueryExample[] {
+   return detail.parameters.flatMap((parameter) => {
+-    if (asText(parameter.in, "") !== "query") return []
+-    const name = asText(parameter.name, "")
++    const safeParameter = asRecord(sanitizeMetadata(parameter))
++    if (!safeParameter || asText(safeParameter.in, "") !== "query") {
++      return []
++    }
++
++    const name = asText(safeParameter.name, "")
+     if (!name) return []
+ 
+-    const schema = asRecord(parameter.schema)
++    const schema = asRecord(safeParameter.schema)
+     const examples = schema?.examples
+     const example = Array.isArray(examples) ? examples[0] : undefined
+     const value = asText(example ?? schema?.default, "value")
+     return [{ name, value }]
+   })
+ }
+ 
+ function buildCodeExamples(detail: ApiDetail, authHeader: string) {
+   const method = detail.method.toUpperCase()
+   const queryParameters = parameterExamples(detail)
+-  const absoluteUrl = `https://api.yeyubaka.top${detail.path}`
++  const path = normalizeInternalApiPath(detail.path)
++  const absoluteUrl = buildPublicApiUrl(path)
++  if (!path || !absoluteUrl) {
++    const unavailable = "无法生成示例：目录路径不可用。"
++    return {
++      curl: unavailable,
++      javascript: unavailable,
++      python: unavailable,
++    }
++  }
++
+   const curlStart =
+     method === "GET"
+       ? `curl -G "${absoluteUrl}"`
+       : `curl -X ${method} "${absoluteUrl}"`
+   const curlLines = [curlStart, `  -H "${authHeader}: <YOUR_API_KEY>"`]
+   for (const parameter of queryParameters) {
+     curlLines.push(`  --data-urlencode "${parameter.name}=${parameter.value}"`)
+   }
+ 
+   const javascriptLines = [
+-    `const endpoint = new URL(${JSON.stringify(detail.path)}, window.location.origin);`,
++    `const endpoint = new URL(${JSON.stringify(path)}, ${JSON.stringify(PUBLIC_API_BASE_URL)});`,
+     ...queryParameters.map(
+       (parameter) =>
+         `endpoint.searchParams.set(${JSON.stringify(parameter.name)}, ${JSON.stringify(parameter.value)});`,
+     ),
+     "",
+     "const response = await fetch(endpoint, {",
+     `  method: ${JSON.stringify(method)},`,
+     "  headers: {",
+     `    ${JSON.stringify(authHeader)}: "<YOUR_API_KEY>",`,
+     "  },",
+@@ -92,36 +110,38 @@ function readableCacheKey(key: string) {
+ }
+ 
+ interface ApiDetailViewProps {
+   detail: ApiDetail
+ }
+ 
+ export function ApiDetailView({ detail }: ApiDetailViewProps) {
+   const authHeader = detail.auth.header ?? "X-API-Key"
+   const examples = buildCodeExamples(detail, authHeader)
+   const responseFields = responseProperties(detail)
+-  const cacheEntries = Object.entries(detail.cache_rules)
++  const safePath = normalizeInternalApiPath(detail.path)
++  const safeCacheRules = asRecord(sanitizeMetadata(detail.cache_rules)) ?? {}
++  const cacheEntries = Object.entries(safeCacheRules)
+ 
+   return (
+     <div className="api-detail-page">
+       <div className="api-detail-breadcrumbs">
+         <Link to="/catalog" className="public-text-link">
+           ← 返回公开目录
+         </Link>
+         <span aria-hidden="true">/</span>
+         <span>{detail.category}</span>
+       </div>
+ 
+       <header className="api-detail-header">
+         <div className="api-detail-path-row">
+           <span className="catalog-method-badge">{detail.method}</span>
+-          <code>{detail.path}</code>
++          <code>{safePath ?? "路径不可用"}</code>
+         </div>
+         <h1 className="api-detail-title">{detail.name}</h1>
+         <p className="api-detail-summary">{detail.summary}</p>
+         <div className="api-detail-tags">
+           {detail.is_free ? (
+             <span className="catalog-tag catalog-tag-free">免费</span>
+           ) : null}
+           <span className="catalog-tag catalog-tag-status">
+             {detail.status}
+           </span>
+@@ -168,33 +188,40 @@ export function ApiDetailView({ detail }: ApiDetailViewProps) {
+                   <thead>
+                     <tr>
+                       <th scope="col">名称</th>
+                       <th scope="col">位置</th>
+                       <th scope="col">必填</th>
+                       <th scope="col">类型 / 说明</th>
+                     </tr>
+                   </thead>
+                   <tbody>
+                     {detail.parameters.map((parameter, index) => {
+-                      const schema = asRecord(parameter.schema)
+-                      const name = asText(parameter.name, `参数 ${index + 1}`)
++                      const safeParameter =
++                        asRecord(sanitizeMetadata(parameter)) ?? {}
++                      const schema = asRecord(safeParameter.schema)
++                      const name = asText(
++                        safeParameter.name,
++                        `参数 ${index + 1}`,
++                      )
+                       const schemaText = asText(schema?.type, "—")
+-                      const description = asText(parameter.description, "")
++                      const description = asText(safeParameter.description, "")
+                       return (
+                         <tr
+-                          key={`${name}-${asText(parameter.in, "unknown")}-${index}`}
++                          key={`${name}-${asText(safeParameter.in, "unknown")}-${index}`}
+                         >
+                           <th scope="row">
+                             <code>{name}</code>
+                           </th>
+-                          <td>{asText(parameter.in)}</td>
+-                          <td>{parameter.required === true ? "是" : "否"}</td>
++                          <td>{asText(safeParameter.in)}</td>
++                          <td>
++                            {safeParameter.required === true ? "是" : "否"}
++                          </td>
+                           <td>
+                             <span>{schemaText}</span>
+                             {description ? (
+                               <span className="api-table-note">
+                                 {description}
+                               </span>
+                             ) : null}
+                           </td>
+                         </tr>
+                       )
+@@ -245,31 +272,37 @@ export function ApiDetailView({ detail }: ApiDetailViewProps) {
+               <div className="api-table-scroll">
+                 <table className="api-detail-table">
+                   <thead>
+                     <tr>
+                       <th scope="col">HTTP</th>
+                       <th scope="col">错误码</th>
+                       <th scope="col">说明</th>
+                     </tr>
+                   </thead>
+                   <tbody>
+-                    {detail.errors.map((error, index) => (
+-                      <tr key={`${asText(error.code, "error")}-${index}`}>
+-                        <td>{asText(error.status)}</td>
+-                        <th scope="row">
+-                          <code>{asText(error.code)}</code>
+-                        </th>
+-                        <td>
+-                          {asText(error.description, asText(error.message))}
+-                        </td>
+-                      </tr>
+-                    ))}
++                    {detail.errors.map((error, index) => {
++                      const safeError = asRecord(sanitizeMetadata(error)) ?? {}
++                      return (
++                        <tr key={`${asText(safeError.code, "error")}-${index}`}>
++                          <td>{asText(safeError.status)}</td>
++                          <th scope="row">
++                            <code>{asText(safeError.code)}</code>
++                          </th>
++                          <td>
++                            {asText(
++                              safeError.description,
++                              asText(safeError.message),
++                            )}
++                          </td>
++                        </tr>
++                      )
++                    })}
+                   </tbody>
+                 </table>
+               </div>
+             ) : (
+               <p className="api-detail-muted">目录暂未提供错误码说明。</p>
+             )}
+           </section>
+ 
+           <section
+             className="api-detail-section"
+diff --git a/frontend/src/components/ApiCatalog/CatalogPagination.tsx b/frontend/src/components/ApiCatalog/CatalogPagination.tsx
+new file mode 100644
+index 0000000..b530923
+--- /dev/null
++++ b/frontend/src/components/ApiCatalog/CatalogPagination.tsx
+@@ -0,0 +1,45 @@
++interface CatalogPaginationProps {
++  count: number
++  page: number
++  pageSize: number
++  isFetching?: boolean
++  onPageChange: (page: number) => void
++}
++
++export function CatalogPagination({
++  count,
++  page,
++  pageSize,
++  isFetching = false,
++  onPageChange,
++}: CatalogPaginationProps) {
++  const safePageSize = Math.max(1, pageSize)
++  const totalPages = Math.max(1, Math.ceil(count / safePageSize))
++  if (totalPages <= 1) return null
++
++  return (
++    <nav className="catalog-pagination" aria-label="目录分页">
++      <button
++        type="button"
++        className="public-inline-button"
++        disabled={isFetching || page <= 1}
++        onClick={() => onPageChange(page - 1)}
++      >
++        上一页
++      </button>
++      <span aria-live="polite">
++        第 {page} / {totalPages} 页
++      </span>
++      <button
++        type="button"
++        className="public-inline-button"
++        disabled={isFetching || page >= totalPages}
++        onClick={() => onPageChange(page + 1)}
++      >
++        下一页
++      </button>
++    </nav>
++  )
++}
++
++export default CatalogPagination
+diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
+index 16a7477..248fd59 100644
+--- a/frontend/src/components/ApiCatalog/catalog-types.ts
++++ b/frontend/src/components/ApiCatalog/catalog-types.ts
+@@ -1,33 +1,95 @@
+ import type { ApiDetail, CatalogItem } from "@/client"
+ 
+ export type CatalogSearchParams = {
+   query?: string
+   category?: string
+   status?: string
++  page: number
+ }
+ 
+ export type CatalogMetadata = Record<string, unknown>
+ 
++export const PUBLIC_API_BASE_URL = "https://api.yeyubaka.top"
++
++const SENSITIVE_METADATA_KEY_PARTS = [
++  "token",
++  "secret",
++  "password",
++  "authorization",
++  "cookie",
++  "apikey",
++  "credential",
++  "privatekey",
++  "providerref",
++]
++
++function normalizedMetadataKey(key: string): string {
++  return key.toLowerCase().replace(/[^a-z0-9]/g, "")
++}
++
++function isSensitiveMetadataKey(key: string): boolean {
++  const normalized = normalizedMetadataKey(key)
++  return SENSITIVE_METADATA_KEY_PARTS.some((part) => normalized.includes(part))
++}
++
+ export function normalizeSearchValue(value: unknown): string | undefined {
+   if (typeof value !== "string") return undefined
+   const normalized = value.trim()
+   return normalized || undefined
+ }
+ 
++export function normalizePage(value: unknown): number {
++  const page =
++    typeof value === "number"
++      ? value
++      : typeof value === "string" && value.trim()
++        ? Number(value)
++        : Number.NaN
++
++  return Number.isSafeInteger(page) && page > 0 ? page : 1
++}
++
++export function normalizeInternalApiPath(value: unknown): string | undefined {
++  if (typeof value !== "string") return undefined
++
++  const normalized = value.trim()
++  if (!normalized) return undefined
++
++  if (
++    !normalized.startsWith("/") ||
++    normalized.startsWith("//") ||
++    normalized.includes("//") ||
++    /https?:/i.test(normalized) ||
++    normalized.includes("\\") ||
++    /[?#%]/.test(normalized) ||
++    normalized.includes("..")
++  ) {
++    return undefined
++  }
++
++  return normalized
++}
++
++export function buildPublicApiUrl(value: unknown): string | undefined {
++  const path = normalizeInternalApiPath(value)
++  return path ? `${PUBLIC_API_BASE_URL}${path}` : undefined
++}
++
+ export function parseCatalogSearch(
+   search: Record<string, unknown>,
+ ): CatalogSearchParams {
+   return {
+     query: normalizeSearchValue(search.query),
+     category: normalizeSearchValue(search.category),
+     status: normalizeSearchValue(search.status),
++    page: normalizePage(search.page),
+   }
+ }
+ 
+ export function formatUpdatedAt(value?: string | null): string {
+   if (!value) return "更新时间待补充"
+ 
+   const timestamp = Date.parse(value)
+   if (Number.isNaN(timestamp)) return value
+ 
+   return new Intl.DateTimeFormat("zh-HK", {
+@@ -43,38 +105,55 @@ export function asRecord(value: unknown): CatalogMetadata | undefined {
+ }
+ 
+ export function asText(value: unknown, fallback = "—"): string {
+   if (typeof value === "string") return value
+   if (typeof value === "number" || typeof value === "boolean") {
+     return String(value)
+   }
+   return fallback
+ }
+ 
++export function sanitizeMetadata(value: unknown): unknown {
++  if (Array.isArray(value)) {
++    return value.map((item) => sanitizeMetadata(item))
++  }
++
++  if (typeof value !== "object" || value === null) return value
++
++  const sanitized: CatalogMetadata = {}
++  for (const [key, nestedValue] of Object.entries(value)) {
++    if (isSensitiveMetadataKey(key)) continue
++    sanitized[key] = sanitizeMetadata(nestedValue)
++  }
++  return sanitized
++}
++
+ export function formatMetadata(value: unknown): string {
+-  if (value === null || value === undefined) return "—"
+-  if (typeof value === "string") return value
+-  if (typeof value === "number" || typeof value === "boolean") {
+-    return String(value)
++  const sanitized = sanitizeMetadata(value)
++  if (sanitized === null || sanitized === undefined) return "—"
++  if (typeof sanitized === "string") return sanitized
++  if (typeof sanitized === "number" || typeof sanitized === "boolean") {
++    return String(sanitized)
+   }
+ 
+   try {
+-    return JSON.stringify(value, null, 2) ?? "无法展示"
++    return JSON.stringify(sanitized, null, 2) ?? "无法展示"
+   } catch {
+     return "无法展示"
+   }
+ }
+ 
+ export function responseProperties(
+   detail: ApiDetail,
+ ): Array<[string, CatalogMetadata]> {
+-  const properties = asRecord(detail.response_schema)?.properties
++  const safeResponseSchema = asRecord(sanitizeMetadata(detail.response_schema))
++  const properties = safeResponseSchema?.properties
+   if (!properties || typeof properties !== "object") return []
+ 
+   return Object.entries(properties)
+     .map(
+       ([name, value]) =>
+         [name, asRecord(value) ?? {}] as [string, CatalogMetadata],
+     )
+     .sort(([left], [right]) => left.localeCompare(right))
+ }
+ 
+diff --git a/frontend/src/index.css b/frontend/src/index.css
+index 4cd1214..eff80a1 100644
+--- a/frontend/src/index.css
++++ b/frontend/src/index.css
+@@ -716,20 +716,35 @@
+   margin-top: 1rem;
+ }
+ 
+ .catalog-grid {
+   display: grid;
+   grid-template-columns: repeat(2, minmax(0, 1fr));
+   gap: 1rem;
+   margin-top: 1.25rem;
+ }
+ 
++.catalog-pagination {
++  display: flex;
++  align-items: center;
++  justify-content: center;
++  gap: 1rem;
++  margin-top: 1.5rem;
++  color: var(--yeyu-muted);
++  font-size: 0.85rem;
++}
++
++.catalog-pagination button:disabled {
++  cursor: not-allowed;
++  opacity: 0.45;
++}
++
+ .catalog-card {
+   display: grid;
+   min-width: 0;
+   gap: 1.1rem;
+   padding: 1.25rem;
+   border: 1px solid var(--yeyu-line);
+   border-top: 3px solid var(--yeyu-teal);
+   background: var(--yeyu-paper-strong);
+   transition:
+     border-color 160ms ease,
+diff --git a/frontend/src/routes/catalog/$slug.tsx b/frontend/src/routes/catalog/$slug.tsx
+index 5c51950..30c0fa2 100644
+--- a/frontend/src/routes/catalog/$slug.tsx
++++ b/frontend/src/routes/catalog/$slug.tsx
+@@ -28,19 +28,21 @@ function CatalogDetailRoute() {
+       const response = await CatalogService.getCatalogDetail({
+         path: { slug },
+       })
+       return response.data
+     },
+   })
+ 
+   return (
+     <PublicLayout>
+       <div className="public-container catalog-detail-shell">
+-        {detailQuery.isPending ? <CatalogLoadingState /> : null}
+-        {detailQuery.isError ? (
++        {detailQuery.isPending ? (
++          <CatalogLoadingState />
++        ) : detailQuery.isError ? (
+           <CatalogDetailErrorState onRetry={() => void detailQuery.refetch()} />
++        ) : detailQuery.data ? (
++          <ApiDetailView detail={detailQuery.data} />
+         ) : null}
+-        {detailQuery.data ? <ApiDetailView detail={detailQuery.data} /> : null}
+       </div>
+     </PublicLayout>
+   )
+ }
+diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
+index f83b403..9ad8056 100644
+--- a/frontend/src/routes/catalog/index.tsx
++++ b/frontend/src/routes/catalog/index.tsx
+@@ -1,17 +1,18 @@
+ import { useQuery } from "@tanstack/react-query"
+ import { createFileRoute } from "@tanstack/react-router"
+ import { useEffect, useState } from "react"
+ 
+ import { type CatalogPage, CatalogService } from "@/client"
+ import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
+ import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
++import CatalogPagination from "@/components/ApiCatalog/CatalogPagination"
+ import CatalogSearch from "@/components/ApiCatalog/CatalogSearch"
+ import {
+   CatalogEmptyState,
+   CatalogErrorState,
+   CatalogLoadingState,
+ } from "@/components/ApiCatalog/CatalogStates"
+ import {
+   type CatalogSearchParams,
+   normalizeSearchValue,
+   parseCatalogSearch,
+@@ -41,55 +42,58 @@ function CatalogRoutePage() {
+ 
+   useEffect(() => {
+     const normalizedQuery = normalizeSearchValue(draftQuery)
+     if (normalizedQuery === search.query) return
+ 
+     const timeoutId = window.setTimeout(() => {
+       void navigate({
+         search: (previous) => ({
+           ...previous,
+           query: normalizedQuery,
++          page: 1,
+         }),
+         replace: true,
+       })
+     }, 400)
+ 
+     return () => window.clearTimeout(timeoutId)
+   }, [draftQuery, navigate, search.query])
+ 
+   const catalogQuery = useQuery<CatalogPage>({
+     queryKey: [
+       "public-catalog",
+       search.query ?? "",
+       search.category ?? "",
+       search.status ?? "",
++      search.page,
+     ],
+     queryFn: async () => {
+       const response = await CatalogService.searchCatalog({
+         query: {
+           query: search.query,
+           category: search.category,
+           status: search.status,
+-          page: 1,
++          page: search.page,
+           page_size: 20,
+         },
+       })
+       return response.data
+     },
+   })
+ 
+   const items = catalogQuery.data?.data ?? []
+   const updateFilter = (key: "category" | "status", value: string) => {
+     void navigate({
+       search: (previous) => ({
+         ...previous,
+         [key]: normalizeSearchValue(value),
++        page: 1,
+       }),
+       replace: true,
+     })
+   }
+ 
+   return (
+     <PublicLayout>
+       <div className="public-container catalog-page-shell">
+         <header className="catalog-page-header">
+           <p className="public-eyebrow">公开目录 / REAL DATA</p>
+@@ -141,15 +145,31 @@ function CatalogRoutePage() {
+           {!catalogQuery.isPending &&
+           !catalogQuery.isError &&
+           items.length === 0 ? (
+             <CatalogEmptyState />
+           ) : null}
+           {!catalogQuery.isPending &&
+           !catalogQuery.isError &&
+           items.length > 0 ? (
+             <CatalogGrid items={items} />
+           ) : null}
++          {!catalogQuery.isPending &&
++          !catalogQuery.isError &&
++          catalogQuery.data ? (
++            <CatalogPagination
++              count={catalogQuery.data.count}
++              page={search.page}
++              pageSize={catalogQuery.data.page_size}
++              isFetching={catalogQuery.isFetching}
++              onPageChange={(page) =>
++                void navigate({
++                  search: (previous) => ({ ...previous, page }),
++                  replace: true,
++                })
++              }
++            />
++          ) : null}
+         </section>
+       </div>
+     </PublicLayout>
+   )
+ }
+diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
+index 39af2f7..e190367 100644
+--- a/frontend/tests/public-catalog.spec.ts
++++ b/frontend/tests/public-catalog.spec.ts
+@@ -66,58 +66,103 @@ const timeDetail = {
+     {
+       language: "curl",
+       request:
+         'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
+     },
+   ],
+   source: "Yeyu API",
+   cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
+ }
+ 
++const unsafeDetail = {
++  ...timeDetail,
++  path: "https://evil.example/redirect?token=<NON_SECRET_TEST_VALUE>",
++  parameters: [
++    ...timeDetail.parameters,
++    {
++      name: "metadata",
++      in: "query",
++      required: false,
++      description: "可见参数",
++      schema: {
++        type: "string",
++        "client-secret": "<NON_SECRET_TEST_VALUE>",
++      },
++    },
++  ],
++  response_schema: {
++    ...timeDetail.response_schema,
++    token: "<NON_SECRET_TEST_VALUE>",
++    properties: {
++      ...timeDetail.response_schema.properties,
++      api_key: {
++        type: "string",
++        private_key: "<NON_SECRET_TEST_VALUE>",
++      },
++    },
++  },
++  errors: [
++    ...timeDetail.errors,
++    {
++      status: 500,
++      code: "SAFE_ERROR",
++      description: "可见错误描述",
++      authorization: "<NON_SECRET_TEST_VALUE>",
++    },
++  ],
++  cache_rules: {
++    ...timeDetail.cache_rules,
++    "provider-ref": "<NON_SECRET_TEST_VALUE>",
++    safe: { nested_password: "<NON_SECRET_TEST_VALUE>" },
++  },
++}
++
+ type CatalogPage = {
+   data: (typeof timeItem)[]
+   count: number
+   page: number
+   page_size: number
+ }
+ 
+-async function mockCatalogApi(page: Page) {
+-  await page.route("**/api/v1/catalog*", async (route) => {
+-    const url = new URL(route.request().url())
++const catalogListUrl = /\/api\/v1\/catalog(?:\?.*)?$/
++const catalogTimeDetailUrl = /\/api\/v1\/catalog\/time(?:\?.*)?$/
+ 
+-    if (url.pathname.endsWith("/time")) {
+-      await route.fulfill({
+-        status: 200,
+-        contentType: "application/json",
+-        body: JSON.stringify(timeDetail),
+-      })
+-      return
+-    }
++async function mockCatalogApi(page: Page, detail = timeDetail) {
++  await page.route(catalogTimeDetailUrl, async (route) => {
++    await route.fulfill({
++      status: 200,
++      contentType: "application/json",
++      body: JSON.stringify(detail),
++    })
++  })
+ 
++  await page.route(catalogListUrl, async (route) => {
++    const url = new URL(route.request().url())
+     const query = url.searchParams.get("query") ?? ""
+     const category = url.searchParams.get("category")
+     const status = url.searchParams.get("status")
++    const pageNumber = Number(url.searchParams.get("page") ?? "1")
+     const data =
+       query === "missing"
+         ? []
+         : query === "uuid"
+           ? [uuidItem]
+           : [timeItem, uuidItem]
+     const filtered = data.filter(
+       (item) =>
+         (!category || item.category === category) &&
+         (!status || item.status === status),
+     )
+     const response: CatalogPage = {
+       data: filtered,
+       count: filtered.length,
+-      page: 1,
++      page: pageNumber,
+       page_size: 20,
+     }
+ 
+     await route.fulfill({
+       status: 200,
+       contentType: "application/json",
+       body: JSON.stringify(response),
+     })
+   })
+ }
+@@ -139,55 +184,99 @@ test("Anonymous users can browse the real public catalog", async ({ page }) => {
+   await expect(page.getByRole("link", { name: /时间查询/ })).toHaveAttribute(
+     "href",
+     "/catalog/time",
+   )
+ })
+ 
+ test("Catalog search is debounced and filters are shareable in the URL", async ({
+   page,
+ }) => {
+   const catalogRequests: string[] = []
+-  await page.route("**/api/v1/catalog*", async (route) => {
++  await page.route(catalogListUrl, async (route) => {
+     const url = new URL(route.request().url())
+-    if (url.pathname.endsWith("/time")) {
+-      await route.fulfill({
+-        status: 200,
+-        contentType: "application/json",
+-        body: JSON.stringify(timeDetail),
+-      })
+-      return
+-    }
+     catalogRequests.push(url.search)
+     const item = url.searchParams.get("query") === "uuid" ? uuidItem : timeItem
+     await route.fulfill({
+       status: 200,
+       contentType: "application/json",
+       body: JSON.stringify({ data: [item], count: 1, page: 1, page_size: 20 }),
+     })
+   })
+ 
+-  await page.goto("/catalog")
++  await page.goto("/catalog?page=2")
+   const searchInput = page.getByRole("searchbox", { name: "搜索公开 API" })
+   await searchInput.fill("uuid")
+   await page.waitForTimeout(150)
+   expect(
+     catalogRequests.filter((request) => request.includes("query=uuid")),
+   ).toHaveLength(0)
+-  await expect(page).toHaveURL(/\/catalog\?query=uuid$/)
++  await expect
++    .poll(() => new URL(page.url()).searchParams.get("page"))
++    .toBe("1")
++  await expect
++    .poll(() => new URL(page.url()).searchParams.get("query"))
++    .toBe("uuid")
+   await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
+ 
+   await page.getByLabel("分类").selectOption("tools")
++  await expect
++    .poll(() => new URL(page.url()).searchParams.get("page"))
++    .toBe("1")
+   await expect(page).toHaveURL(/query=uuid.*category=tools/)
+   await page.getByLabel("状态").selectOption("published")
++  await expect
++    .poll(() => new URL(page.url()).searchParams.get("page"))
++    .toBe("1")
+   await expect(page).toHaveURL(/query=uuid.*category=tools.*status=published/)
+ })
+ 
++test("Catalog pagination preserves search filters and requests the selected page", async ({
++  page,
++}) => {
++  const catalogRequests: URL[] = []
++  await page.route(catalogListUrl, async (route) => {
++    const url = new URL(route.request().url())
++    catalogRequests.push(url)
++    const pageNumber = Number(url.searchParams.get("page") ?? "1")
++    const response: CatalogPage = {
++      data: pageNumber === 2 ? [uuidItem] : [timeItem],
++      count: 21,
++      page: pageNumber,
++      page_size: 20,
++    }
++    await route.fulfill({
++      status: 200,
++      contentType: "application/json",
++      body: JSON.stringify(response),
++    })
++  })
++
++  await page.goto("/catalog?query=time&category=tools&status=published")
++  await expect(page.getByTestId("catalog-card-time")).toBeVisible()
++  await expect(page.getByRole("button", { name: "下一页" })).toBeEnabled()
++
++  await page.getByRole("button", { name: "下一页" }).click()
++  await expect(page).toHaveURL(
++    /query=time.*category=tools.*status=published.*page=2/,
++  )
++  await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
++
++  const secondRequest = catalogRequests.at(-1)
++  expect(secondRequest?.searchParams.get("page")).toBe("2")
++  expect(secondRequest?.searchParams.get("page_size")).toBe("20")
++
++  await page.getByRole("button", { name: "上一页" }).click()
++  await expect(page).toHaveURL(
++    /query=time.*category=tools.*status=published.*page=1/,
++  )
++})
++
+ test("Catalog displays an explicit empty state for an empty result", async ({
+   page,
+ }) => {
+   await mockCatalogApi(page)
+   await page.goto("/catalog?query=missing")
+ 
+   await expect(page.getByTestId("catalog-empty")).toBeVisible()
+   await expect(page.getByText("没有找到匹配的公开接口")).toBeVisible()
+   await expect(page.getByTestId("catalog-grid")).not.toBeVisible()
+ })
+@@ -221,20 +310,78 @@ test("Time detail documents the request contract and safe code examples", async
+   await expect(
+     page.locator("code").filter({ hasText: "api.yeyubaka.top" }).first(),
+   ).toBeVisible()
+ 
+   const copyButton = page.getByRole("button", { name: "复制 curl 示例" })
+   await expect(copyButton).toBeVisible()
+   await copyButton.click()
+   await expect(copyButton).toContainText("已复制")
+ })
+ 
++test("Detail rejects unsafe paths and hides sensitive metadata values", async ({
++  page,
++}) => {
++  await mockCatalogApi(page, unsafeDetail)
++  await page.goto("/catalog/time")
++
++  await expect(page.getByText("路径不可用", { exact: true })).toBeVisible()
++  await expect(page.locator("body")).not.toContainText("evil.example")
++  await expect(page.locator("body")).not.toContainText(
++    "<NON_SECRET_TEST_VALUE>",
++  )
++  await expect(page.getByText("可见错误描述", { exact: true })).toBeVisible()
++})
++
++test("Detail errors do not render stale detail data", async ({ page }) => {
++  let detailRequestCount = 0
++  await page.route(catalogTimeDetailUrl, async (route) => {
++    detailRequestCount += 1
++    if (detailRequestCount === 1) {
++      await route.fulfill({
++        status: 200,
++        contentType: "application/json",
++        body: JSON.stringify(timeDetail),
++      })
++      return
++    }
++
++    await route.fulfill({
++      status: 503,
++      contentType: "application/json",
++      body: JSON.stringify({ detail: "unavailable" }),
++    })
++  })
++  await page.route(catalogListUrl, async (route) => {
++    await route.fulfill({
++      status: 200,
++      contentType: "application/json",
++      body: JSON.stringify({
++        data: [timeItem],
++        count: 1,
++        page: 1,
++        page_size: 20,
++      }),
++    })
++  })
++
++  await page.goto("/catalog/time")
++  await expect(page.getByRole("heading", { name: "时间查询" })).toBeVisible()
++  await page.getByRole("link", { name: /返回公开目录/ }).click()
++  await expect(page).toHaveURL("/catalog")
++  await page.getByRole("link", { name: /时间查询/ }).click()
++
++  await expect(page.getByTestId("catalog-detail-error")).toBeVisible()
++  await expect(
++    page.getByRole("heading", { name: "时间查询" }),
++  ).not.toBeVisible()
++})
++
+ test("Public navigation remains keyboard accessible on mobile", async ({
+   page,
+ }) => {
+   await page.setViewportSize({ width: 390, height: 844 })
+   await mockCatalogApi(page)
+   await page.goto("/")
+ 
+   const navigation = page.getByRole("navigation", { name: "公共导航" })
+   const menuButton = navigation.getByRole("button", { name: /菜单/ })
+ 
+diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
+index aaab69a..14106a5 100644
+--- a/plans/agent-reports/task-7-3-report.md
++++ b/plans/agent-reports/task-7-3-report.md
+@@ -126,10 +126,75 @@ Checked 15 files in 14ms. No fixes applied.
+ - [x] 复制按钮有可访问名称，成功状态有文字和图标反馈。
+ - [x] 移动端表格、路径和代码块设置横向滚动边界。
+ - [x] Biome 最终对本次 15 个文件通过。
+ - [ ] Playwright、build、pytest 和真实浏览器验收：受用户要求/现有 setup 阻塞，未验证。
+ 
+ ## 7. 提交
+ 
+ 实现代码提交主题：`feat: add public catalog and api detail pages`
+ 
+ 提交 SHA：`c13adce`（实现提交；报告随后单独提交）。
++
++## 8. 独立审查 Important 修复（2026-10-02）
++
++本次修复范围仅覆盖独立审查报告中的五个 Important，不修改任务 2 认证/公共壳层，不手改 `frontend/src/routeTree.gen.ts`，不扩展在线调试、API Key 管理或第三方接口。
++
++### 8.1 示例 URL/path 边界
++
++- `frontend/src/components/ApiCatalog/catalog-types.ts` 新增 `normalizeInternalApiPath` 和 `buildPublicApiUrl`。
++- 只接受经过 trim 的单斜杠内部绝对路径，拒绝 `http(s)`、`//`、反斜杠、query/hash、百分号和 `..`。
++- `ApiDetailView` 的 curl、JavaScript、Python 示例统一使用受控路径和 `https://api.yeyubaka.top`；非法路径显示“路径不可用”和不可执行的占位说明，不回显后端任意绝对 URL。
++- 保留 `<YOUR_API_KEY>`，未增加任意 URL 输入或凭据读取。
++
++### 8.2 metadata 防御性脱敏
++
++- `sanitizeMetadata` 递归删除规范化后包含 `token`、`secret`、`password`、`authorization`、`cookie`、`apikey`、`credential`、`privatekey`、`providerref` 的大小写/下划线/连字符变体。
++- `formatMetadata` 在 JSON 格式化前过滤；响应 schema、参数、错误和 cache rules 的展示均使用过滤后的对象，敏感值不替换回显。
++
++### 8.3 目录分页
++
++- `CatalogSearchParams` 新增合法正整数 `page`，缺失或非法值默认为 1。
++- 目录 query key 和 `CatalogService.searchCatalog` 请求均使用 `page` 与 `page_size: 20`。
++- 新增单一职责文件 `frontend/src/components/ApiCatalog/CatalogPagination.tsx`，提供可访问的上一页/下一页、当前页和总页数；搜索、分类、状态变化会重置 `page=1`，分页导航保留其他 search params。
++- 增加分页 URL、请求 query 和上一页行为的 route-mock 回归断言。
++
++### 8.4 详情错误状态互斥
++
++- `frontend/src/routes/catalog/$slug.tsx` 改为 loading/error/success 三选一分支；`isError` 时不再渲染 React Query 保留的旧 detail。
++- 增加“先成功、导航返回后详情请求失败”的 stale detail 回归断言。
++
++### 8.5 Playwright mock 匹配可靠性
++
++- `frontend/tests/public-catalog.spec.ts` 将宽泛 `**/api/v1/catalog*` 改为分别匹配列表 URL 和 `/api/v1/catalog/time` 详情 URL 的正则，并允许 query string。
++- 列表和详情 route mock 不会再把详情请求误判为列表请求，也不会意外访问真实后端。
++
++## 9. 本次真实验证结果
++
++按用户要求没有运行长时间 Playwright、前端 build、后端 pytest、路由生成或线上验收。
++
++先写测试后的短静态检查：
++
++```text
++pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
++exit 1
++原因：Biome 仅报告新增 expect.poll 的格式问题，未修改文件。
++```
++
++修复格式并完成实现后的静态检查：
++
++```text
++pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx E:\AI_projects\yeyu-api\frontend\src\index.css E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
++exit 0
++Checked 7 files in 12ms. No fixes applied.
++
++git diff --check
++exit 0
++仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
++```
++
++### 未验证项
++
++- 本次新增/强化的 Playwright 行为测试未运行，因此不能宣称浏览器测试通过。
++- build、TypeScript 完整检查、后端接口实际分页/脱敏响应、真实浏览器尺寸验收和线上验收仍未验证。
++- 原有 Playwright `auth.setup.ts` 阻塞证据仍以本报告第 5 节为准；本次没有重试，也没有触碰认证配置或真实凭据。
++
++修复提交主题：`fix: close catalog review findings`
+diff --git a/plans/fix-task-7-3-catalog-review-findings.md b/plans/fix-task-7-3-catalog-review-findings.md
+new file mode 100644
+index 0000000..9d91c89
+--- /dev/null
++++ b/plans/fix-task-7-3-catalog-review-findings.md
+@@ -0,0 +1,67 @@
++# Task 7-3 Catalog Review Findings Fix Plan
++
++> **For agentic workers:** Execute this plan in the current `E:\AI_projects\yeyu-api` worktree. Keep the existing public shell and generated route tree unchanged.
++
++**Goal:** Close the five Important findings from the Task 7-3 read-only review with the smallest safe frontend changes and focused regression coverage.
++
++**Architecture:** Keep catalog state in TanStack Router search params. Add pure path and metadata guards in `catalog-types.ts`, use those guards at every detail rendering boundary, and keep pagination as a focused `CatalogPagination` component. Make the detail route render exactly one loading, error, or success state.
++
++**Tech Stack:** React, TypeScript, TanStack Router, TanStack Query, generated `CatalogService`, Playwright route mocks, Biome.
++
++## Global Constraints
++
++- Modify only the Task 7-3 frontend catalog files, focused catalog tests, this plan, and the Task 7-3 report.
++- Do not edit `frontend\src\routeTree.gen.ts`, Task 2 authentication/public shell behavior, backend, online services, DNS, Nginx, or credentials.
++- Use `https://api.yeyubaka.top` only as the controlled public API base in generated examples.
++- Retain `<YOUR_API_KEY>` and use `<NON_SECRET_TEST_VALUE>` for any sensitive-looking test value.
++- Write or update regression tests before implementation; do not run long Playwright or build commands.
++
++### Task 1: Add failing regression coverage
++
++**Files:**
++- Modify: `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`
++
++- [ ] Replace the broad catalog glob with separate regular expressions for `/api/v1/catalog` list URLs with optional query strings and `/api/v1/catalog/time` detail URLs.
++- [ ] Add route-mocked assertions for page 2 and page 1 navigation while retaining `query`, `category`, and `status`.
++- [ ] Add route-mocked detail data containing an unsafe absolute path and sensitive nested keys, then assert the unsafe host and `<NON_SECRET_TEST_VALUE>` are absent from rendered examples/metadata.
++- [ ] Add a stale-detail failure flow that asserts the detail error state does not render the previous detail heading.
++- [ ] Run only the permitted short static check on the updated test file; do not run Playwright.
++
++### Task 2: Harden detail path and metadata boundaries
++
++**Files:**
++- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
++- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`
++
++**Interfaces:**
++- `normalizeInternalApiPath(value: unknown): string | undefined` trims and accepts only a single-slash internal path without `http(s)`, `//`, backslash, query/hash, percent encoding, or `..`.
++- `sanitizeMetadata(value: unknown): unknown` recursively removes object keys whose normalized lowercase form contains `token`, `secret`, `password`, `authorization`, `cookie`, `apikey`, `credential`, `privatekey`, or `providerref`.
++- `formatMetadata` sanitizes before JSON formatting; `responseProperties`, parameter display/examples, error display, and cache display consume sanitized values.
++
++- [ ] Implement the two pure guards in `catalog-types.ts` without changing generated client types.
++- [ ] Build curl, JavaScript, and Python snippets from the controlled base plus the normalized path; render `路径不可用` and a non-URL message when the backend path is rejected.
++- [ ] Keep `<YOUR_API_KEY>` unchanged and do not add arbitrary URL input or credential reads.
++
++### Task 3: Add legal page state and mutually exclusive detail states
++
++**Files:**
++- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
++- Create: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx`
++- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`
++- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx`
++
++- [ ] Add `page: number` to parsed search state, normalize only positive safe integers, and default invalid/missing input to 1.
++- [ ] Include `page` in the query key and send `page` plus `page_size: 20` to `CatalogService.searchCatalog`.
++- [ ] Reset `page` to 1 on debounced query changes and category/status changes while preserving the other search params.
++- [ ] Render accessible previous/next controls using `count` and `page_size`; disable controls at boundaries and while fetching.
++- [ ] Render detail loading, error, and success as an exclusive branch so stale detail data is hidden when `isError` is true.
++
++### Task 4: Verify and record evidence
++
++**Files:**
++- Modify: `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-report.md`
++
++- [ ] Run targeted Biome on every changed frontend source/test file and record the real exit code/output.
++- [ ] Run `git diff --check` and record the real result, including any non-failure line-ending warning.
++- [ ] Do not claim Playwright, build, backend tests, route generation, or browser acceptance unless actually run; record them as unverified.
++- [ ] Inspect the final diff and status, append the five fixes and evidence to the report, then commit with `fix: close catalog review findings`.
diff --git a/plans/agent-reports/task-7-3-fix-review.md b/plans/agent-reports/task-7-3-fix-review.md
new file mode 100644
index 0000000..5d9d4da
--- /dev/null
+++ b/plans/agent-reports/task-7-3-fix-review.md
@@ -0,0 +1,39 @@
+# Task 7-3 修复独立只读复审报告
+
+## Spec Compliance
+
+1. ❌ 路径校验已拒绝绝对 URL、双斜杠、反斜杠、查询/hash、编码和 ..，示例基址固定为正式域名；但 ApiDetailView 的参数 examples/default 仍未充分约束，可能进入 curl、JavaScript、Python 示例。
+2. ❌ sanitizeMetadata 递归删除敏感键，响应、错误、缓存和参数表调用边界基本覆盖；但参数 schema.examples/default 仍可能把未受控值写入示例代码。
+3. ❌ page search/request/pagination/reset 链路正确，分页控件可访问；但筛选选项仍只从当前分页数据生成，其他页面的分类/状态可能不可发现。
+4. ✅ 详情路由 loading/error/success 为互斥分支，错误时不渲染 stale detail。
+5. ✅ 列表和 /api/v1/catalog/time 使用独立正则匹配，分页、敏感数据和 stale detail 回归断言与 mock 基本对应真实页面。
+- ⚠️ 无法从 diff 验证 build、TypeScript、Playwright、真实后端和浏览器验收。
+
+## Strengths
+
+- 正式 API 基址固定，非法路径显示占位文本而不回显原始 URL。
+- 敏感键过滤覆盖响应 schema、参数、错误和缓存展示边界。
+- 分页 search 参数、请求参数、重置逻辑和可访问按钮已补齐。
+- 详情错误状态已隐藏 React Query 保留的旧数据。
+- diff 未修改 routeTree.gen.ts、任务 2 认证/公共壳层或线上资源。
+
+## Issues
+
+### Critical (Must Fix)
+
+- 无。
+
+### Important (Should Fix)
+
+- E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx:33-37,59-68,81-92：参数 examples/default 值未经安全约束，可能把敏感值、外部 URL 或 shell 特殊字符写入示例。应使用严格 allowlist/安全值策略，敏感或 URL-like 值省略，并对 curl 参数转义。
+- E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx:106-113 与 E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogFilters.tsx:20-21：筛选选项只来自当前页，跨页分类/状态不可发现。应使用跨页枚举来源并保留当前选项。
+
+### Minor (Nice to Have)
+
+- 无。
+
+## Assessment
+
+**Task quality:** Needs fixes
+
+**Reasoning:** 路径校验、分页主流程、详情状态互斥和 mock 分离正确，但参数示例和值级安全边界及跨页筛选枚举仍未完全关闭。
diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
new file mode 100644
index 0000000..2cdb6de
--- /dev/null
+++ b/plans/agent-reports/task-7-3-report.md
@@ -0,0 +1,264 @@
+# Task 3：公共目录与 API 详情页实现报告
+
+日期：2026-10-02
+项目：`E:\AI_projects\yeyu-api`
+实现提交：`c13adce`
+
+## 1. 实现范围
+
+本次完成公共目录从占位页到真实搜索优先目录，以及公开 API 详情页：
+
+- 目录页通过生成的 `CatalogService.searchCatalog` 和 React Query 请求后端公开目录；只渲染 API 返回的 `CatalogItem`。
+- `query` 使用 400ms 防抖同步到 TanStack Router search params；`category`、`status` 立即同步 URL，并作为 React Query key 的一部分。
+- 卡片展示名称、简介、方法、路径、免费标记、后端状态和更新时间，并链接到 `/catalog/:slug`。
+- 分别实现加载、错误、空结果状态；空结果不创建前端候选卡片。
+- 新增 `/catalog/$slug` 详情路由，使用 `CatalogService.getCatalogDetail({ path: { slug } })`。
+- 详情展示 API Key 鉴权、参数表、响应字段和 schema、错误码、缓存规则、来源，以及 curl、JavaScript、Python 示例。
+- 所有示例只使用 `<YOUR_API_KEY>`；JavaScript 使用当前页面 origin，curl/Python 使用正式 API 域名；未读取 localStorage、Cookie 或真实 API Key。
+- 首页预览继续使用真实目录 API，并补充详情链接、真实状态/更新时间和搜索跳转入口。
+- 公共导航改为 TanStack Router 链接；详情路径、表格和代码块在窄视口使用滚动/换行边界。
+- 未修改 `frontend/src/routeTree.gen.ts`，未修改 dashboard 保护或认证逻辑，未实现在线调试和 API Key 管理 UI。
+
+## 2. 修改文件
+
+- `frontend/src/components/ApiCatalog/catalog-types.ts`
+- `frontend/src/components/ApiCatalog/CatalogSearch.tsx`
+- `frontend/src/components/ApiCatalog/CatalogFilters.tsx`
+- `frontend/src/components/ApiCatalog/CatalogCard.tsx`
+- `frontend/src/components/ApiCatalog/CatalogGrid.tsx`
+- `frontend/src/components/ApiCatalog/CatalogStates.tsx`
+- `frontend/src/components/ApiCatalog/ApiDetailView.tsx`
+- `frontend/src/components/ApiCatalog/CodeExample.tsx`
+- `frontend/src/routes/catalog/index.tsx`
+- `frontend/src/routes/catalog/$slug.tsx`
+- `frontend/src/routes/index.tsx`
+- `frontend/src/components/PublicSite/PublicHeader.tsx`
+- `frontend/src/components/PublicSite/PublicFooter.tsx`
+- `frontend/src/index.css`
+- `frontend/tests/public-catalog.spec.ts`
+
+任务简报 `plans/agent-reports/task-7-3-brief.md` 是用户提供的未跟踪文件，本次未修改、未提交。
+
+## 3. TDD RED/GREEN 证据
+
+### RED
+
+先更新了 `frontend/tests/public-catalog.spec.ts`，覆盖：匿名目录、搜索参数 URL 同步、防抖、分类/状态筛选 URL、空结果、`/catalog/time`、`/v1/tools/time`、GET、API Key、`timezone`、响应字段、错误码、三种代码示例和复制反馈。
+
+真实命令与结果：
+
+```text
+pnpm exec playwright test tests/public-catalog.spec.ts
+exit 1
+Error: Environment variable FIRST_SUPERUSER is undefined
+```
+
+仅在进程内注入非真实测试值后重试：
+
+```text
+$env:FIRST_SUPERUSER='<NON_SECRET_TEST_EMAIL>'; $env:FIRST_SUPERUSER_PASSWORD='<NON_SECRET_TEST_VALUE>'; pnpm exec playwright test tests/public-catalog.spec.ts
+exit 1
+browserType.launch: Executable doesn't exist ... chrome-headless-shell.exe
+1 failed [setup] auth.setup.ts; 5 did not run
+```
+
+随后执行了依赖安装：
+
+```text
+pnpm exec playwright install chromium
+exit 0
+Chrome for Testing and Chrome Headless Shell downloaded to the Playwright user cache
+```
+
+安装后再次以同样的非真实进程值运行：
+
+```text
+exit 1
+Test timeout of 30000ms exceeded
+at tests/auth.setup.ts:8:41, waiting for getByTestId('email-input')
+1 failed [setup] auth.setup.ts; 5 did not run
+```
+
+因此 RED 阶段有测试收集/环境阻塞证据，但目标目录断言没有进入浏览器执行。
+
+### GREEN
+
+已完成对应静态实现，并执行 Biome 作为快速静态门禁；没有运行 Playwright/build，故不能宣称浏览器 GREEN、类型检查 GREEN 或产品验收 GREEN。
+
+## 4. 静态验证
+
+首次对 `src tests` 执行 Biome 的真实结果：
+
+```text
+exit 1
+Checked 73 files in 46ms. No fixes applied.
+Found 14 errors.
+Found 2 warnings.
+```
+
+错误集中在新增 JSX 格式、无效 div `aria-label`、搜索容器 role，以及 CSS 特异性顺序。修正后只对本次改动的 15 个文件执行：
+
+```text
+pnpm exec biome check --write --no-errors-on-unmatched --files-ignore-unknown=true <15 absolute paths>
+exit 0
+Checked 15 files in 18ms. Fixed 9 files.
+
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true <15 absolute paths>
+exit 0
+Checked 15 files in 14ms. No fixes applied.
+```
+
+另执行 `git diff --check`，未发现空白错误；Git 仅提示 Windows 工作树的 LF/CRLF 转换警告。
+
+## 5. 未验证阻塞与边界
+
+- Playwright 被既有 `auth.setup.ts` 的认证 setup 阻塞；缺少浏览器已安装，但 setup 后续仍在登录页 `email-input` 等待超时。未把 setup 失败算作目录测试通过。
+- 按用户本次要求未运行 `pnpm build`，未运行后端 pytest，也未做真实浏览器桌面/移动截图验收。
+- 未运行 Vite 官方路由生成链，因此 `routeTree.gen.ts` 仍保持未手改状态；新增路由是否被生成链和 TypeScript 完整接纳需要后续 build/开发服务器验证。
+- 未执行线上验收、DNS/Nginx/SMTP/GitHub OAuth 或生产部署；没有触碰旧项目、线上服务和凭据。
+
+## 6. Self-review
+
+- [x] 目录卡片由 `CatalogService` 返回数据驱动，无硬编码接口卡片。
+- [x] 目录搜索和筛选状态可分享，搜索防抖为 400ms。
+- [x] 详情页使用生成 client 的 path slug 形态，展示真实 schema/参数/错误/缓存/来源字段。
+- [x] 示例只包含 `<YOUR_API_KEY>`，没有新增浏览器凭据读取或在线调用控件。
+- [x] 复制按钮有可访问名称，成功状态有文字和图标反馈。
+- [x] 移动端表格、路径和代码块设置横向滚动边界。
+- [x] Biome 最终对本次 15 个文件通过。
+- [ ] Playwright、build、pytest 和真实浏览器验收：受用户要求/现有 setup 阻塞，未验证。
+
+## 7. 提交
+
+实现代码提交主题：`feat: add public catalog and api detail pages`
+
+提交 SHA：`c13adce`（实现提交；报告随后单独提交）。
+
+## 8. 独立审查 Important 修复（2026-10-02）
+
+本次修复范围仅覆盖独立审查报告中的五个 Important，不修改任务 2 认证/公共壳层，不手改 `frontend/src/routeTree.gen.ts`，不扩展在线调试、API Key 管理或第三方接口。
+
+### 8.1 示例 URL/path 边界
+
+- `frontend/src/components/ApiCatalog/catalog-types.ts` 新增 `normalizeInternalApiPath` 和 `buildPublicApiUrl`。
+- 只接受经过 trim 的单斜杠内部绝对路径，拒绝 `http(s)`、`//`、反斜杠、query/hash、百分号和 `..`。
+- `ApiDetailView` 的 curl、JavaScript、Python 示例统一使用受控路径和 `https://api.yeyubaka.top`；非法路径显示“路径不可用”和不可执行的占位说明，不回显后端任意绝对 URL。
+- 保留 `<YOUR_API_KEY>`，未增加任意 URL 输入或凭据读取。
+
+### 8.2 metadata 防御性脱敏
+
+- `sanitizeMetadata` 递归删除规范化后包含 `token`、`secret`、`password`、`authorization`、`cookie`、`apikey`、`credential`、`privatekey`、`providerref` 的大小写/下划线/连字符变体。
+- `formatMetadata` 在 JSON 格式化前过滤；响应 schema、参数、错误和 cache rules 的展示均使用过滤后的对象，敏感值不替换回显。
+
+### 8.3 目录分页
+
+- `CatalogSearchParams` 新增合法正整数 `page`，缺失或非法值默认为 1。
+- 目录 query key 和 `CatalogService.searchCatalog` 请求均使用 `page` 与 `page_size: 20`。
+- 新增单一职责文件 `frontend/src/components/ApiCatalog/CatalogPagination.tsx`，提供可访问的上一页/下一页、当前页和总页数；搜索、分类、状态变化会重置 `page=1`，分页导航保留其他 search params。
+- 增加分页 URL、请求 query 和上一页行为的 route-mock 回归断言。
+
+### 8.4 详情错误状态互斥
+
+- `frontend/src/routes/catalog/$slug.tsx` 改为 loading/error/success 三选一分支；`isError` 时不再渲染 React Query 保留的旧 detail。
+- 增加“先成功、导航返回后详情请求失败”的 stale detail 回归断言。
+
+### 8.5 Playwright mock 匹配可靠性
+
+- `frontend/tests/public-catalog.spec.ts` 将宽泛 `**/api/v1/catalog*` 改为分别匹配列表 URL 和 `/api/v1/catalog/time` 详情 URL 的正则，并允许 query string。
+- 列表和详情 route mock 不会再把详情请求误判为列表请求，也不会意外访问真实后端。
+
+## 9. 本次真实验证结果
+
+按用户要求没有运行长时间 Playwright、前端 build、后端 pytest、路由生成或线上验收。
+
+先写测试后的短静态检查：
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+exit 1
+原因：Biome 仅报告新增 expect.poll 的格式问题，未修改文件。
+```
+
+修复格式并完成实现后的静态检查：
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx E:\AI_projects\yeyu-api\frontend\src\index.css E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+exit 0
+Checked 7 files in 12ms. No fixes applied.
+
+git diff --check
+exit 0
+仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
+```
+
+### 未验证项
+
+- 本次新增/强化的 Playwright 行为测试未运行，因此不能宣称浏览器测试通过。
+- build、TypeScript 完整检查、后端接口实际分页/脱敏响应、真实浏览器尺寸验收和线上验收仍未验证。
+- 原有 Playwright `auth.setup.ts` 阻塞证据仍以本报告第 5 节为准；本次没有重试，也没有触碰认证配置或真实凭据。
+
+修复提交主题：`fix: close catalog review findings`
+
+## 10. 第二轮独立复审 Important 修复（2026-10-02）
+
+本轮只处理最新复审报告中的两个 Important，不修改任务 2、`frontend/src/routeTree.gen.ts`、后端、线上服务、DNS、Nginx 或真实凭据。
+
+### 10.1 参数示例值与认证头安全边界
+
+- `frontend/src/components/ApiCatalog/catalog-types.ts` 新增纯函数 `normalizeSafeQueryKey` 与 `normalizeSafeQueryValue`。
+- 参数名只接受以 ASCII 字母开头、长度受限且仅含字母数字、点、下划线和连字符的 query key；其他名称不进入代码示例，详情参数表也使用安全占位名称。
+- 参数值只接受严格字符 allowlist；拒绝空白、引号、反引号、shell 元字符、换行、百分号、query/hash、反斜杠、scheme/外部 URL、敏感词和 JWT-like 值。非字符串只接受有限的数字/布尔值转换。
+- `schema.examples` 会按顺序寻找第一个安全值，再考虑 `default`；恶意首项不会阻断后续合法值，因此 `Asia/Shanghai` 仍可生成。
+- 认证头不再读取目录 metadata，示例与鉴权说明固定使用 `X-API-Key`；curl 的 URL、header 和 query 参数使用单引号包裹并转义单引号，同时保留 `<YOUR_API_KEY>` 占位符。
+- `public-catalog.spec.ts` 的 unsafe detail 增加恶意参数名、外部 URL、空白、引号、shell 字符、换行、百分号、query/hash、反斜杠、敏感默认值和恶意认证头；新增安全路径场景，断言三种代码示例均不包含这些值，并断言合法 `Asia/Shanghai` 和 `X-API-Key` 仍存在。
+
+### 10.2 跨页真实 facets
+
+- `frontend/src/routes/catalog/index.tsx` 增加独立且缓存的公开目录 facets 查询，固定使用 `CatalogService.searchCatalog` 的无筛选请求、`page_size=100` 和 `staleTime=60_000`。
+- 查询按每个响应的 `count` 逐页读取，最多 100 页；达到 count 或空页即停止，避免不受控资源消耗。
+- `CatalogFilters` 改用完整已获取的真实 `CatalogItem[]` 计算分类/状态，并始终保留当前 URL 选择；主目录查询仍保留原有 query/category/status/page 和分页行为，facets 请求不携带这些筛选参数。
+- facets 请求失败时回退当前页真实 items，并显示现有 `CatalogErrorState`；没有新增后端接口、任意 URL、秘密或硬编码候选项。
+- 分页 route mock 返回 count=101，断言独立 facets 请求会请求 page=2/page_size=100，且不带 query、category、status。
+
+### 10.3 本轮真实验证
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+exit 0
+Checked 4 files in 10ms. No fixes applied.
+
+git diff --check
+exit 0
+仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
+```
+
+本轮没有运行 Playwright、前端 build、后端 pytest、路由生成、真实浏览器或线上验收；因此新增浏览器断言、TypeScript 完整检查、实际后端跨页响应和线上结果仍未验证。修复提交主题：`fix: harden catalog examples and filters`。
+
+## 11. 第二次复审 Important 收口（2026-10-02）
+
+本次仅修复 `task-7-3-second-fix-review.md` 指出的两个 Important；未修改 `frontend/src/routeTree.gen.ts`、认证/公共壳层、后端、线上服务、DNS、Nginx 或凭据。
+
+### 11.1 敏感 query 参数名和值
+
+- `normalizeSafeQueryKey` 现在在格式校验后复用统一的敏感字段规范化判定；`apiKey`、`API_KEY`、`api-key`、`access_token`、`Access-Token`、`ACCESS.TOKEN`、`client_secret`、`Client-Secret`、`CLIENT.SECRET` 等变体不会进入示例。
+- 回归夹具为这些敏感名称提供仅由合法字符组成的数值，断言三种代码示例均不包含名称或值；固定认证头仍为 `X-API-Key: <YOUR_API_KEY>`，既有内部路径和外部 URL 防护保持不变。
+
+### 11.2 facets 上限不完整状态
+
+- 新增 `CatalogFacetResult` 完成度类型；达到 100 页上限时返回 `complete: false`、`reason: "page-limit"`，并丢弃部分 items。
+- 页面显示 `catalog-facets-incomplete` 状态，且不会把被截断的部分结果传给 `CatalogFilters`；只有按 `count` 或空页停止时才使用已收集 facet。
+- 回归夹具第 1 页返回 100 条、第 2 页返回唯一 `data`/`deprecated` 项并断言其进入筛选选项；另以 `count=10001` 覆盖请求到第 100 页后的显式不完整状态及空筛选选项。
+
+### 11.3 本次真实静态验证
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+exit 0
+Checked 3 files in 12ms. No fixes applied.
+
+git diff --check
+exit 0
+仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
+```
+
+本次没有运行 Playwright、前端 build、后端测试、路由生成、TypeScript 完整检查或线上验收；因此新增浏览器回归断言和完整类型/运行时行为仍未验证。
diff --git a/plans/agent-reports/task-7-3-review.md b/plans/agent-reports/task-7-3-review.md
new file mode 100644
index 0000000..ee88224
--- /dev/null
+++ b/plans/agent-reports/task-7-3-review.md
@@ -0,0 +1,40 @@
+# Task 7-3 独立只读审查报告
+
+## Spec Compliance
+
+- ✅ 使用 CatalogService、TanStack Router search params 和 400ms 防抖：routes/catalog/index.tsx:21-77。
+- ✅ 目录卡片、详情字段、状态组件、占位 API Key、复制反馈和移动端滚动边界均有实现。
+- ❌ 示例 URL 不完全符合当前域名/禁止任意 URL 边界：ApiDetailView.tsx:36-47、:68。
+- ⚠️ 无法从 diff 验证 build、路由生成、Playwright 完整执行、真实后端响应、1280/390 浏览器验收；报告显示 Playwright 被既有 auth.setup.ts 阻塞。
+
+## Strengths
+
+- 目录数据来自真实 CatalogService，未硬编码候选接口或统计。
+- 搜索、分类、状态通过 URL 保存，并保留其他 search 参数。
+- 加载、错误、空结果有独立可读状态；详情展示鉴权、参数、响应、错误、缓存、来源和三种示例。
+- 代码复制按钮有可访问名称和 aria-live 成功/失败反馈；表格、路径和代码块具备移动端滚动边界。
+
+## Issues
+
+### Critical (Must Fix)
+
+- 无。
+
+### Important (Should Fix)
+
+- E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx:36-47,68：curl/Python 硬编码正式域名且 JavaScript 的 new URL 信任 detail.path；应只接受内部绝对路径并统一使用受控 API 基址。
+- E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts:53-65 与 ApiDetailView.tsx:232,316：response_schema 和 cache_rules 任意 metadata 直接 JSON 序列化回显；应增加前端敏感键过滤/脱敏，作为后端 DTO 清洗的防御层。
+- E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx:67-80 与 CatalogFilters.tsx:20-21：固定 page=1、page_size=20，无分页且筛选项只来自当前页，目录超过 20 条会静默遗漏；应增加分页 search param 或等价的继续加载。
+- E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx:38-42：详情重试失败而 React Query 保留旧 data 时会同时渲染错误和旧详情；应隐藏旧详情或明确标识 stale 状态。
+- E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts:84-93,149-157：mock 使用 **/api/v1/catalog* 可能不能可靠匹配带路径的详情请求；应使用正则或分别注册列表与详情精确路由。
+
+### Minor (Nice to Have)
+
+- public-catalog.spec.ts:168-181 的一次性 fill 加 150ms 等待不能完全证明 400ms 防抖；分类/状态只断言 URL，未断言请求参数。
+- public-catalog.spec.ts:88-121,184-251 未覆盖加载、错误、重试、详情移动端溢出和 clipboard 内容。
+
+## Assessment
+
+**Task quality:** Needs fixes
+
+**Reasoning:** 主流程和 UI 结构基本符合需求，但示例 URL 信任边界、分页、详情错误状态和 Playwright mock 存在明确风险；build、真实后端和浏览器验收尚未完成。
diff --git a/plans/agent-reports/task-7-3-second-fix-diff.md b/plans/agent-reports/task-7-3-second-fix-diff.md
new file mode 100644
index 0000000..c66303d
--- /dev/null
+++ b/plans/agent-reports/task-7-3-second-fix-diff.md
@@ -0,0 +1,679 @@
+# Review package: 04fcbd4..9c901eb
+
+## Commits
+9c901eb fix: harden catalog examples and filters
+
+## Files changed
+ .../src/components/ApiCatalog/ApiDetailView.tsx    |  54 +++++++----
+ .../src/components/ApiCatalog/catalog-types.ts     |  39 ++++++++
+ frontend/src/routes/catalog/index.tsx              |  38 +++++++-
+ frontend/tests/public-catalog.spec.ts              | 103 ++++++++++++++++++++-
+ plans/agent-reports/task-7-3-report.md             |  35 +++++++
+ 5 files changed, 246 insertions(+), 23 deletions(-)
+
+## Diff
+diff --git a/frontend/src/components/ApiCatalog/ApiDetailView.tsx b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+index 7c7f036..a650887 100644
+--- a/frontend/src/components/ApiCatalog/ApiDetailView.tsx
++++ b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+@@ -3,95 +3,114 @@ import { Link } from "@tanstack/react-router"
+ import type { ApiDetail } from "@/client"
+ 
+ import CodeExample from "./CodeExample"
+ import {
+   asRecord,
+   asText,
+   buildPublicApiUrl,
+   formatMetadata,
+   formatUpdatedAt,
+   normalizeInternalApiPath,
++  normalizeSafeQueryKey,
++  normalizeSafeQueryValue,
++  PUBLIC_API_AUTH_HEADER,
+   PUBLIC_API_BASE_URL,
+   responseProperties,
+   sanitizeMetadata,
+ } from "./catalog-types"
+ 
+ type QueryExample = {
+   name: string
+   value: string
+ }
+ 
+ function parameterExamples(detail: ApiDetail): QueryExample[] {
+   return detail.parameters.flatMap((parameter) => {
+     const safeParameter = asRecord(sanitizeMetadata(parameter))
+     if (!safeParameter || asText(safeParameter.in, "") !== "query") {
+       return []
+     }
+ 
+-    const name = asText(safeParameter.name, "")
++    const name = normalizeSafeQueryKey(safeParameter.name)
+     if (!name) return []
+ 
+     const schema = asRecord(safeParameter.schema)
+-    const examples = schema?.examples
+-    const example = Array.isArray(examples) ? examples[0] : undefined
+-    const value = asText(example ?? schema?.default, "value")
++    const candidates = [
++      ...(Array.isArray(schema?.examples) ? schema.examples : []),
++      schema?.default,
++    ]
++    const value = candidates
++      .map((candidate) => normalizeSafeQueryValue(candidate))
++      .find((candidate): candidate is string => candidate !== undefined)
++    if (!value) return []
++
+     return [{ name, value }]
+   })
+ }
+ 
+-function buildCodeExamples(detail: ApiDetail, authHeader: string) {
+-  const method = detail.method.toUpperCase()
++function quoteCurlArgument(value: string): string {
++  return `'${value.replaceAll("'", "'\\''")}'`
++}
++
++function buildCodeExamples(detail: ApiDetail) {
++  const candidateMethod = detail.method.toUpperCase()
++  const method = /^[A-Z]{1,16}$/.test(candidateMethod) ? candidateMethod : "GET"
+   const queryParameters = parameterExamples(detail)
+   const path = normalizeInternalApiPath(detail.path)
+   const absoluteUrl = buildPublicApiUrl(path)
+   if (!path || !absoluteUrl) {
+     const unavailable = "无法生成示例：目录路径不可用。"
+     return {
+       curl: unavailable,
+       javascript: unavailable,
+       python: unavailable,
+     }
+   }
+ 
+   const curlStart =
+     method === "GET"
+-      ? `curl -G "${absoluteUrl}"`
+-      : `curl -X ${method} "${absoluteUrl}"`
+-  const curlLines = [curlStart, `  -H "${authHeader}: <YOUR_API_KEY>"`]
++      ? `curl -G ${quoteCurlArgument(absoluteUrl)}`
++      : `curl -X ${method} ${quoteCurlArgument(absoluteUrl)}`
++  const curlLines = [
++    curlStart,
++    `  -H ${quoteCurlArgument(`${PUBLIC_API_AUTH_HEADER}: <YOUR_API_KEY>`)}`,
++  ]
+   for (const parameter of queryParameters) {
+-    curlLines.push(`  --data-urlencode "${parameter.name}=${parameter.value}"`)
++    curlLines.push(
++      `  --data-urlencode ${quoteCurlArgument(`${parameter.name}=${parameter.value}`)}`,
++    )
+   }
+ 
+   const javascriptLines = [
+     `const endpoint = new URL(${JSON.stringify(path)}, ${JSON.stringify(PUBLIC_API_BASE_URL)});`,
+     ...queryParameters.map(
+       (parameter) =>
+         `endpoint.searchParams.set(${JSON.stringify(parameter.name)}, ${JSON.stringify(parameter.value)});`,
+     ),
+     "",
+     "const response = await fetch(endpoint, {",
+     `  method: ${JSON.stringify(method)},`,
+     "  headers: {",
+-    `    ${JSON.stringify(authHeader)}: "<YOUR_API_KEY>",`,
++    `    ${JSON.stringify(PUBLIC_API_AUTH_HEADER)}: "<YOUR_API_KEY>",`,
+     "  },",
+     "});",
+     "const data = await response.json();",
+     "console.log(data);",
+   ]
+ 
+   const pythonLines = [
+     "import requests",
+     "",
+     "response = requests.request(",
+     `    ${JSON.stringify(method)},`,
+     `    ${JSON.stringify(absoluteUrl)},`,
+-    `    headers={${JSON.stringify(authHeader)}: "<YOUR_API_KEY>"},`,
++    `    headers={${JSON.stringify(PUBLIC_API_AUTH_HEADER)}: "<YOUR_API_KEY>"},`,
+     ...(queryParameters.length
+       ? [
+           `    params=${JSON.stringify(Object.fromEntries(queryParameters.map((parameter) => [parameter.name, parameter.value])))},`,
+         ]
+       : []),
+     "    timeout=10,",
+     ")",
+     "response.raise_for_status()",
+     "print(response.json())",
+   ]
+@@ -107,22 +126,22 @@ function readableCacheKey(key: string) {
+   return key
+     .replaceAll("_", " ")
+     .replace(/\b\w/g, (character) => character.toUpperCase())
+ }
+ 
+ interface ApiDetailViewProps {
+   detail: ApiDetail
+ }
+ 
+ export function ApiDetailView({ detail }: ApiDetailViewProps) {
+-  const authHeader = detail.auth.header ?? "X-API-Key"
+-  const examples = buildCodeExamples(detail, authHeader)
++  const authHeader = PUBLIC_API_AUTH_HEADER
++  const examples = buildCodeExamples(detail)
+   const responseFields = responseProperties(detail)
+   const safePath = normalizeInternalApiPath(detail.path)
+   const safeCacheRules = asRecord(sanitizeMetadata(detail.cache_rules)) ?? {}
+   const cacheEntries = Object.entries(safeCacheRules)
+ 
+   return (
+     <div className="api-detail-page">
+       <div className="api-detail-breadcrumbs">
+         <Link to="/catalog" className="public-text-link">
+           ← 返回公开目录
+@@ -191,24 +210,23 @@ export function ApiDetailView({ detail }: ApiDetailViewProps) {
+                       <th scope="col">位置</th>
+                       <th scope="col">必填</th>
+                       <th scope="col">类型 / 说明</th>
+                     </tr>
+                   </thead>
+                   <tbody>
+                     {detail.parameters.map((parameter, index) => {
+                       const safeParameter =
+                         asRecord(sanitizeMetadata(parameter)) ?? {}
+                       const schema = asRecord(safeParameter.schema)
+-                      const name = asText(
+-                        safeParameter.name,
+-                        `参数 ${index + 1}`,
+-                      )
++                      const name =
++                        normalizeSafeQueryKey(safeParameter.name) ??
++                        `参数 ${index + 1}`
+                       const schemaText = asText(schema?.type, "—")
+                       const description = asText(safeParameter.description, "")
+                       return (
+                         <tr
+                           key={`${name}-${asText(safeParameter.in, "unknown")}-${index}`}
+                         >
+                           <th scope="row">
+                             <code>{name}</code>
+                           </th>
+                           <td>{asText(safeParameter.in)}</td>
+diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
+index 248fd59..5e973cc 100644
+--- a/frontend/src/components/ApiCatalog/catalog-types.ts
++++ b/frontend/src/components/ApiCatalog/catalog-types.ts
+@@ -3,48 +3,87 @@ import type { ApiDetail, CatalogItem } from "@/client"
+ export type CatalogSearchParams = {
+   query?: string
+   category?: string
+   status?: string
+   page: number
+ }
+ 
+ export type CatalogMetadata = Record<string, unknown>
+ 
+ export const PUBLIC_API_BASE_URL = "https://api.yeyubaka.top"
++export const PUBLIC_API_AUTH_HEADER = "X-API-Key"
+ 
+ const SENSITIVE_METADATA_KEY_PARTS = [
+   "token",
+   "secret",
+   "password",
+   "authorization",
+   "cookie",
+   "apikey",
+   "credential",
+   "privatekey",
+   "providerref",
+ ]
++const SAFE_QUERY_KEY_PATTERN = /^[A-Za-z][A-Za-z0-9_.-]{0,63}$/
++const SAFE_QUERY_VALUE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/+:-]{0,127}$/
++const QUERY_VALUE_SCHEME_PATTERN = /^[A-Za-z][A-Za-z0-9+.-]*:/
++const SENSITIVE_QUERY_VALUE_PATTERN =
++  /(token|secret|password|authorization|cookie|api[-_]?key|credential|private[-_]?key|bearer)/i
++const JWT_LIKE_PATTERN =
++  /^[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}$/
+ 
+ function normalizedMetadataKey(key: string): string {
+   return key.toLowerCase().replace(/[^a-z0-9]/g, "")
+ }
+ 
+ function isSensitiveMetadataKey(key: string): boolean {
+   const normalized = normalizedMetadataKey(key)
+   return SENSITIVE_METADATA_KEY_PARTS.some((part) => normalized.includes(part))
+ }
+ 
+ export function normalizeSearchValue(value: unknown): string | undefined {
+   if (typeof value !== "string") return undefined
+   const normalized = value.trim()
+   return normalized || undefined
+ }
+ 
++export function normalizeSafeQueryKey(value: unknown): string | undefined {
++  return typeof value === "string" && SAFE_QUERY_KEY_PATTERN.test(value)
++    ? value
++    : undefined
++}
++
++export function normalizeSafeQueryValue(value: unknown): string | undefined {
++  const text =
++    typeof value === "string"
++      ? value
++      : typeof value === "number" && Number.isFinite(value)
++        ? String(value)
++        : typeof value === "boolean"
++          ? String(value)
++          : undefined
++
++  if (
++    !text ||
++    text !== text.trim() ||
++    !SAFE_QUERY_VALUE_PATTERN.test(text) ||
++    text.includes("://") ||
++    QUERY_VALUE_SCHEME_PATTERN.test(text) ||
++    SENSITIVE_QUERY_VALUE_PATTERN.test(text) ||
++    JWT_LIKE_PATTERN.test(text)
++  ) {
++    return undefined
++  }
++
++  return text
++}
++
+ export function normalizePage(value: unknown): number {
+   const page =
+     typeof value === "number"
+       ? value
+       : typeof value === "string" && value.trim()
+         ? Number(value)
+         : Number.NaN
+ 
+   return Number.isSafeInteger(page) && page > 0 ? page : 1
+ }
+diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
+index 9ad8056..ed1152a 100644
+--- a/frontend/src/routes/catalog/index.tsx
++++ b/frontend/src/routes/catalog/index.tsx
+@@ -1,31 +1,55 @@
+ import { useQuery } from "@tanstack/react-query"
+ import { createFileRoute } from "@tanstack/react-router"
+ import { useEffect, useState } from "react"
+ 
+-import { type CatalogPage, CatalogService } from "@/client"
++import { type CatalogItem, type CatalogPage, CatalogService } from "@/client"
+ import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
+ import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
+ import CatalogPagination from "@/components/ApiCatalog/CatalogPagination"
+ import CatalogSearch from "@/components/ApiCatalog/CatalogSearch"
+ import {
+   CatalogEmptyState,
+   CatalogErrorState,
+   CatalogLoadingState,
+ } from "@/components/ApiCatalog/CatalogStates"
+ import {
+   type CatalogSearchParams,
+   normalizeSearchValue,
+   parseCatalogSearch,
+ } from "@/components/ApiCatalog/catalog-types"
+ import PublicLayout from "@/components/PublicSite/PublicLayout"
+ 
++const FACET_PAGE_SIZE = 100
++const MAX_FACET_PAGES = 100
++
++async function fetchCatalogFacetItems(): Promise<CatalogItem[]> {
++  const items: CatalogItem[] = []
++
++  for (let page = 1; page <= MAX_FACET_PAGES; page += 1) {
++    const response = await CatalogService.searchCatalog({
++      query: {
++        page,
++        page_size: FACET_PAGE_SIZE,
++      },
++    })
++    const catalogPage = response.data
++    items.push(...catalogPage.data)
++
++    if (items.length >= catalogPage.count || catalogPage.data.length === 0) {
++      return items
++    }
++  }
++
++  return items
++}
++
+ export const Route = createFileRoute("/catalog/")({
+   validateSearch: (search): CatalogSearchParams => parseCatalogSearch(search),
+   component: CatalogRoutePage,
+   head: () => ({
+     meta: [
+       {
+         title: "API 目录 - Yeyu API",
+       },
+     ],
+   }),
+@@ -73,21 +97,28 @@ function CatalogRoutePage() {
+           category: search.category,
+           status: search.status,
+           page: search.page,
+           page_size: 20,
+         },
+       })
+       return response.data
+     },
+   })
+ 
++  const catalogFacetQuery = useQuery<CatalogItem[]>({
++    queryKey: ["public-catalog-facets"],
++    queryFn: fetchCatalogFacetItems,
++    staleTime: 60_000,
++  })
++
+   const items = catalogQuery.data?.data ?? []
++  const filterItems = catalogFacetQuery.data ?? items
+   const updateFilter = (key: "category" | "status", value: string) => {
+     void navigate({
+       search: (previous) => ({
+         ...previous,
+         [key]: normalizeSearchValue(value),
+         page: 1,
+       }),
+       replace: true,
+     })
+   }
+@@ -98,26 +129,29 @@ function CatalogRoutePage() {
+         <header className="catalog-page-header">
+           <p className="public-eyebrow">公开目录 / REAL DATA</p>
+           <h1 className="catalog-page-title">API 目录</h1>
+           <p className="catalog-page-lede">
+             只展示后端公开、健康或已发布的真实接口。先搜索，再阅读完整调用契约。
+           </p>
+         </header>
+ 
+         <CatalogSearch value={draftQuery} onChange={setDraftQuery} />
+         <CatalogFilters
+-          items={items}
++          items={filterItems}
+           category={search.category}
+           status={search.status}
+           onCategoryChange={(value) => updateFilter("category", value)}
+           onStatusChange={(value) => updateFilter("status", value)}
+         />
++        {catalogFacetQuery.isError && !catalogQuery.isError ? (
++          <CatalogErrorState onRetry={() => void catalogFacetQuery.refetch()} />
++        ) : null}
+ 
+         <section
+           className="catalog-results"
+           aria-labelledby="catalog-results-heading"
+         >
+           <div className="catalog-results-heading">
+             <div>
+               <p className="public-eyebrow">RESULTS</p>
+               <h2
+                 id="catalog-results-heading"
+diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
+index e190367..6f4968b 100644
+--- a/frontend/tests/public-catalog.spec.ts
++++ b/frontend/tests/public-catalog.spec.ts
+@@ -68,31 +68,55 @@ const timeDetail = {
+       request:
+         'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
+     },
+   ],
+   source: "Yeyu API",
+   cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
+ }
+ 
+ const unsafeDetail = {
+   ...timeDetail,
++  auth: {
++    type: "api_key",
++    header: 'X-Evil-Header: "<NON_SECRET_TEST_VALUE>"',
++  },
+   path: "https://evil.example/redirect?token=<NON_SECRET_TEST_VALUE>",
+   parameters: [
+     ...timeDetail.parameters,
+     {
+-      name: "metadata",
++      name: 'bad"name`$()',
++      in: "query",
++      required: false,
++      description: "恶意参数",
++      schema: {
++        type: "string",
++        examples: ["$(whoami)\n`id`"],
++        default: "<NON_SECRET_TEST_VALUE>",
++      },
++    },
++    {
++      name: "unsafe-value",
+       in: "query",
+       required: false,
+-      description: "可见参数",
++      description: "恶意默认值",
+       schema: {
+         type: "string",
+-        "client-secret": "<NON_SECRET_TEST_VALUE>",
++        examples: [
++          " https://evil.example/?next=<NON_SECRET_TEST_VALUE> ",
++          '"quoted"',
++          "percent%20",
++          "query?next=evil",
++          "hash#evil",
++          "back\\slash",
++          "Asia/Shanghai",
++        ],
++        default: "secret-token-<NON_SECRET_TEST_VALUE>",
+       },
+     },
+   ],
+   response_schema: {
+     ...timeDetail.response_schema,
+     token: "<NON_SECRET_TEST_VALUE>",
+     properties: {
+       ...timeDetail.response_schema.properties,
+       api_key: {
+         type: "string",
+@@ -109,20 +133,25 @@ const unsafeDetail = {
+       authorization: "<NON_SECRET_TEST_VALUE>",
+     },
+   ],
+   cache_rules: {
+     ...timeDetail.cache_rules,
+     "provider-ref": "<NON_SECRET_TEST_VALUE>",
+     safe: { nested_password: "<NON_SECRET_TEST_VALUE>" },
+   },
+ }
+ 
++const unsafeExamplesDetail = {
++  ...unsafeDetail,
++  path: "/v1/tools/time",
++}
++
+ type CatalogPage = {
+   data: (typeof timeItem)[]
+   count: number
+   page: number
+   page_size: number
+ }
+ 
+ const catalogListUrl = /\/api\/v1\/catalog(?:\?.*)?$/
+ const catalogTimeDetailUrl = /\/api\/v1\/catalog\/time(?:\?.*)?$/
+ 
+@@ -226,39 +255,82 @@ test("Catalog search is debounced and filters are shareable in the URL", async (
+   await expect
+     .poll(() => new URL(page.url()).searchParams.get("page"))
+     .toBe("1")
+   await expect(page).toHaveURL(/query=uuid.*category=tools.*status=published/)
+ })
+ 
+ test("Catalog pagination preserves search filters and requests the selected page", async ({
+   page,
+ }) => {
+   const catalogRequests: URL[] = []
++  const facetRequests: URL[] = []
+   await page.route(catalogListUrl, async (route) => {
+     const url = new URL(route.request().url())
++    const isFacetRequest =
++      url.searchParams.get("page_size") === "100" &&
++      !url.searchParams.has("query") &&
++      !url.searchParams.has("category") &&
++      !url.searchParams.has("status")
++    if (isFacetRequest) {
++      facetRequests.push(url)
++      const pageNumber = Number(url.searchParams.get("page") ?? "1")
++      const response: CatalogPage = {
++        data: pageNumber === 2 ? [uuidItem] : [timeItem],
++        count: 101,
++        page: pageNumber,
++        page_size: 100,
++      }
++      await route.fulfill({
++        status: 200,
++        contentType: "application/json",
++        body: JSON.stringify(response),
++      })
++      return
++    }
++
+     catalogRequests.push(url)
+     const pageNumber = Number(url.searchParams.get("page") ?? "1")
+     const response: CatalogPage = {
+       data: pageNumber === 2 ? [uuidItem] : [timeItem],
+       count: 21,
+       page: pageNumber,
+       page_size: 20,
+     }
+     await route.fulfill({
+       status: 200,
+       contentType: "application/json",
+       body: JSON.stringify(response),
+     })
+   })
+ 
+   await page.goto("/catalog?query=time&category=tools&status=published")
+   await expect(page.getByTestId("catalog-card-time")).toBeVisible()
++  await expect
++    .poll(() =>
++      facetRequests.some((request) => request.searchParams.get("page") === "2"),
++    )
++    .toBe(true)
++  expect(
++    facetRequests.every(
++      (request) => request.searchParams.get("query") === null,
++    ),
++  ).toBe(true)
++  expect(
++    facetRequests.every(
++      (request) => request.searchParams.get("category") === null,
++    ),
++  ).toBe(true)
++  expect(
++    facetRequests.every(
++      (request) => request.searchParams.get("status") === null,
++    ),
++  ).toBe(true)
+   await expect(page.getByRole("button", { name: "下一页" })).toBeEnabled()
+ 
+   await page.getByRole("button", { name: "下一页" }).click()
+   await expect(page).toHaveURL(
+     /query=time.*category=tools.*status=published.*page=2/,
+   )
+   await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
+ 
+   const secondRequest = catalogRequests.at(-1)
+   expect(secondRequest?.searchParams.get("page")).toBe("2")
+@@ -324,20 +396,45 @@ test("Detail rejects unsafe paths and hides sensitive metadata values", async ({
+   await page.goto("/catalog/time")
+ 
+   await expect(page.getByText("路径不可用", { exact: true })).toBeVisible()
+   await expect(page.locator("body")).not.toContainText("evil.example")
+   await expect(page.locator("body")).not.toContainText(
+     "<NON_SECRET_TEST_VALUE>",
+   )
+   await expect(page.getByText("可见错误描述", { exact: true })).toBeVisible()
+ })
+ 
++test("Detail omits unsafe parameter examples from every code sample", async ({
++  page,
++}) => {
++  await mockCatalogApi(page, unsafeExamplesDetail)
++  await page.goto("/catalog/time")
++
++  const codeSamples = await page
++    .locator(".code-example-block code")
++    .allTextContents()
++  expect(codeSamples).toHaveLength(3)
++
++  const renderedExamples = codeSamples.join("\n")
++  expect(renderedExamples).toContain("Asia/Shanghai")
++  expect(renderedExamples).toContain("X-API-Key")
++  expect(renderedExamples).toContain("<YOUR_API_KEY>")
++  expect(renderedExamples).not.toContain('bad"name`$()')
++  expect(renderedExamples).not.toContain(
++    "https://evil.example/?next=<NON_SECRET_TEST_VALUE>",
++  )
++  expect(renderedExamples).not.toContain("$(whoami)")
++  expect(renderedExamples).not.toContain("`id`")
++  expect(renderedExamples).not.toContain("secret-token-<NON_SECRET_TEST_VALUE>")
++  expect(renderedExamples).not.toContain("X-Evil-Header")
++})
++
+ test("Detail errors do not render stale detail data", async ({ page }) => {
+   let detailRequestCount = 0
+   await page.route(catalogTimeDetailUrl, async (route) => {
+     detailRequestCount += 1
+     if (detailRequestCount === 1) {
+       await route.fulfill({
+         status: 200,
+         contentType: "application/json",
+         body: JSON.stringify(timeDetail),
+       })
+diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
+index 14106a5..cf690f4 100644
+--- a/plans/agent-reports/task-7-3-report.md
++++ b/plans/agent-reports/task-7-3-report.md
+@@ -191,10 +191,45 @@ exit 0
+ 仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
+ ```
+ 
+ ### 未验证项
+ 
+ - 本次新增/强化的 Playwright 行为测试未运行，因此不能宣称浏览器测试通过。
+ - build、TypeScript 完整检查、后端接口实际分页/脱敏响应、真实浏览器尺寸验收和线上验收仍未验证。
+ - 原有 Playwright `auth.setup.ts` 阻塞证据仍以本报告第 5 节为准；本次没有重试，也没有触碰认证配置或真实凭据。
+ 
+ 修复提交主题：`fix: close catalog review findings`
++
++## 10. 第二轮独立复审 Important 修复（2026-10-02）
++
++本轮只处理最新复审报告中的两个 Important，不修改任务 2、`frontend/src/routeTree.gen.ts`、后端、线上服务、DNS、Nginx 或真实凭据。
++
++### 10.1 参数示例值与认证头安全边界
++
++- `frontend/src/components/ApiCatalog/catalog-types.ts` 新增纯函数 `normalizeSafeQueryKey` 与 `normalizeSafeQueryValue`。
++- 参数名只接受以 ASCII 字母开头、长度受限且仅含字母数字、点、下划线和连字符的 query key；其他名称不进入代码示例，详情参数表也使用安全占位名称。
++- 参数值只接受严格字符 allowlist；拒绝空白、引号、反引号、shell 元字符、换行、百分号、query/hash、反斜杠、scheme/外部 URL、敏感词和 JWT-like 值。非字符串只接受有限的数字/布尔值转换。
++- `schema.examples` 会按顺序寻找第一个安全值，再考虑 `default`；恶意首项不会阻断后续合法值，因此 `Asia/Shanghai` 仍可生成。
++- 认证头不再读取目录 metadata，示例与鉴权说明固定使用 `X-API-Key`；curl 的 URL、header 和 query 参数使用单引号包裹并转义单引号，同时保留 `<YOUR_API_KEY>` 占位符。
++- `public-catalog.spec.ts` 的 unsafe detail 增加恶意参数名、外部 URL、空白、引号、shell 字符、换行、百分号、query/hash、反斜杠、敏感默认值和恶意认证头；新增安全路径场景，断言三种代码示例均不包含这些值，并断言合法 `Asia/Shanghai` 和 `X-API-Key` 仍存在。
++
++### 10.2 跨页真实 facets
++
++- `frontend/src/routes/catalog/index.tsx` 增加独立且缓存的公开目录 facets 查询，固定使用 `CatalogService.searchCatalog` 的无筛选请求、`page_size=100` 和 `staleTime=60_000`。
++- 查询按每个响应的 `count` 逐页读取，最多 100 页；达到 count 或空页即停止，避免不受控资源消耗。
++- `CatalogFilters` 改用完整已获取的真实 `CatalogItem[]` 计算分类/状态，并始终保留当前 URL 选择；主目录查询仍保留原有 query/category/status/page 和分页行为，facets 请求不携带这些筛选参数。
++- facets 请求失败时回退当前页真实 items，并显示现有 `CatalogErrorState`；没有新增后端接口、任意 URL、秘密或硬编码候选项。
++- 分页 route mock 返回 count=101，断言独立 facets 请求会请求 page=2/page_size=100，且不带 query、category、status。
++
++### 10.3 本轮真实验证
++
++```text
++pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
++exit 0
++Checked 4 files in 10ms. No fixes applied.
++
++git diff --check
++exit 0
++仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
++```
++
++本轮没有运行 Playwright、前端 build、后端 pytest、路由生成、真实浏览器或线上验收；因此新增浏览器断言、TypeScript 完整检查、实际后端跨页响应和线上结果仍未验证。修复提交主题：`fix: harden catalog examples and filters`。
diff --git a/plans/agent-reports/task-7-3-second-fix-review.md b/plans/agent-reports/task-7-3-second-fix-review.md
new file mode 100644
index 0000000..9ef4bbf
--- /dev/null
+++ b/plans/agent-reports/task-7-3-second-fix-review.md
@@ -0,0 +1,41 @@
+# Task 7-3 第二次修复复审
+
+## 复审范围
+
+- 基线：`04fcbd4`
+- 当前修复：`9c901eb`
+- Diff：`E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-second-fix-diff.md`
+- 复审方式：独立只读子代理；未修改文件、未提交、未推送。
+
+## 结论
+
+**Approved：否。** 无 Critical，但上一轮两个 Important 均未完全关闭。
+
+## Important
+
+1. **代码示例仍可能泄露敏感 query 参数值。**
+
+   `normalizeSafeQueryKey` 只校验格式，没有拒绝 `apiKey`、`access_token`、`client_secret` 等参数名；值过滤也只能识别关键词、JWT 和特殊字符。类似 `apiKey=1234567890` 仍可能进入三种示例。
+
+   相关位置：
+
+   - `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
+   - `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`
+
+2. **facets 仍不能保证完整目录。**
+
+   当前最多请求 100 页，即最多约 10,000 条；达到上限时静默返回部分数据，没有 incomplete/error 信号。测试的 `count=101` 每页只返回 1 条，实际会继续请求到上限，但只断言请求过第 2 页，且没有证明后续页的分类/状态 facet 真正生效。
+
+   相关位置：
+
+   - `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`
+   - `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`
+
+## Minor
+
+- facets 请求失败时仍展示完整 `CatalogErrorState`，同时主目录结果可能正常显示，错误语义容易与“目录加载失败”混淆。
+- URL 同步链路和当前代码中的明显 TypeScript 错误未见新问题；本次未运行 Playwright、build 或 `tsc`。
+
+## Task gate
+
+Task 7-3 暂不通过，必须修复上述 Important 后重新运行覆盖测试并进行新鲜只读复审。
diff --git a/plans/agent-reports/task-7-3-third-fix-diff.md b/plans/agent-reports/task-7-3-third-fix-diff.md
new file mode 100644
index 0000000..553331c
--- /dev/null
+++ b/plans/agent-reports/task-7-3-third-fix-diff.md
@@ -0,0 +1,489 @@
+# Review package: 9c901eb..6d3c1636fa48e60e9e9d3eda04b19c612861fac5
+
+## Commits
+6d3c163 fix: close remaining catalog review findings
+
+## Files changed
+ .../src/components/ApiCatalog/catalog-types.ts     |  15 ++-
+ frontend/src/routes/catalog/index.tsx              |  24 ++++-
+ frontend/tests/public-catalog.spec.ts              | 101 ++++++++++++++++++++-
+ plans/agent-reports/task-7-3-report.md             |  29 ++++++
+ 4 files changed, 162 insertions(+), 7 deletions(-)
+
+## Diff
+diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
+index 5e973cc..ed14c2e 100644
+--- a/frontend/src/components/ApiCatalog/catalog-types.ts
++++ b/frontend/src/components/ApiCatalog/catalog-types.ts
+@@ -2,20 +2,31 @@ import type { ApiDetail, CatalogItem } from "@/client"
+ 
+ export type CatalogSearchParams = {
+   query?: string
+   category?: string
+   status?: string
+   page: number
+ }
+ 
+ export type CatalogMetadata = Record<string, unknown>
+ 
++export type CatalogFacetResult =
++  | {
++      items: CatalogItem[]
++      complete: true
++    }
++  | {
++      items: []
++      complete: false
++      reason: "page-limit"
++    }
++
+ export const PUBLIC_API_BASE_URL = "https://api.yeyubaka.top"
+ export const PUBLIC_API_AUTH_HEADER = "X-API-Key"
+ 
+ const SENSITIVE_METADATA_KEY_PARTS = [
+   "token",
+   "secret",
+   "password",
+   "authorization",
+   "cookie",
+   "apikey",
+@@ -40,21 +51,23 @@ function isSensitiveMetadataKey(key: string): boolean {
+   return SENSITIVE_METADATA_KEY_PARTS.some((part) => normalized.includes(part))
+ }
+ 
+ export function normalizeSearchValue(value: unknown): string | undefined {
+   if (typeof value !== "string") return undefined
+   const normalized = value.trim()
+   return normalized || undefined
+ }
+ 
+ export function normalizeSafeQueryKey(value: unknown): string | undefined {
+-  return typeof value === "string" && SAFE_QUERY_KEY_PATTERN.test(value)
++  return typeof value === "string" &&
++    SAFE_QUERY_KEY_PATTERN.test(value) &&
++    !isSensitiveMetadataKey(value)
+     ? value
+     : undefined
+ }
+ 
+ export function normalizeSafeQueryValue(value: unknown): string | undefined {
+   const text =
+     typeof value === "string"
+       ? value
+       : typeof value === "number" && Number.isFinite(value)
+         ? String(value)
+diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
+index ed1152a..fa2b395 100644
+--- a/frontend/src/routes/catalog/index.tsx
++++ b/frontend/src/routes/catalog/index.tsx
+@@ -6,48 +6,49 @@ import { type CatalogItem, type CatalogPage, CatalogService } from "@/client"
+ import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
+ import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
+ import CatalogPagination from "@/components/ApiCatalog/CatalogPagination"
+ import CatalogSearch from "@/components/ApiCatalog/CatalogSearch"
+ import {
+   CatalogEmptyState,
+   CatalogErrorState,
+   CatalogLoadingState,
+ } from "@/components/ApiCatalog/CatalogStates"
+ import {
++  type CatalogFacetResult,
+   type CatalogSearchParams,
+   normalizeSearchValue,
+   parseCatalogSearch,
+ } from "@/components/ApiCatalog/catalog-types"
+ import PublicLayout from "@/components/PublicSite/PublicLayout"
+ 
+ const FACET_PAGE_SIZE = 100
+ const MAX_FACET_PAGES = 100
+ 
+-async function fetchCatalogFacetItems(): Promise<CatalogItem[]> {
++async function fetchCatalogFacetItems(): Promise<CatalogFacetResult> {
+   const items: CatalogItem[] = []
+ 
+   for (let page = 1; page <= MAX_FACET_PAGES; page += 1) {
+     const response = await CatalogService.searchCatalog({
+       query: {
+         page,
+         page_size: FACET_PAGE_SIZE,
+       },
+     })
+     const catalogPage = response.data
+     items.push(...catalogPage.data)
+ 
+     if (items.length >= catalogPage.count || catalogPage.data.length === 0) {
+-      return items
++      return { items, complete: true }
+     }
+   }
+ 
+-  return items
++  return { items: [], complete: false, reason: "page-limit" }
+ }
+ 
+ export const Route = createFileRoute("/catalog/")({
+   validateSearch: (search): CatalogSearchParams => parseCatalogSearch(search),
+   component: CatalogRoutePage,
+   head: () => ({
+     meta: [
+       {
+         title: "API 目录 - Yeyu API",
+       },
+@@ -97,28 +98,32 @@ function CatalogRoutePage() {
+           category: search.category,
+           status: search.status,
+           page: search.page,
+           page_size: 20,
+         },
+       })
+       return response.data
+     },
+   })
+ 
+-  const catalogFacetQuery = useQuery<CatalogItem[]>({
++  const catalogFacetQuery = useQuery<CatalogFacetResult>({
+     queryKey: ["public-catalog-facets"],
+     queryFn: fetchCatalogFacetItems,
+     staleTime: 60_000,
+   })
+ 
+   const items = catalogQuery.data?.data ?? []
+-  const filterItems = catalogFacetQuery.data ?? items
++  const filterItems = catalogFacetQuery.data
++    ? catalogFacetQuery.data.complete
++      ? catalogFacetQuery.data.items
++      : []
++    : items
+   const updateFilter = (key: "category" | "status", value: string) => {
+     void navigate({
+       search: (previous) => ({
+         ...previous,
+         [key]: normalizeSearchValue(value),
+         page: 1,
+       }),
+       replace: true,
+     })
+   }
+@@ -135,20 +140,29 @@ function CatalogRoutePage() {
+         </header>
+ 
+         <CatalogSearch value={draftQuery} onChange={setDraftQuery} />
+         <CatalogFilters
+           items={filterItems}
+           category={search.category}
+           status={search.status}
+           onCategoryChange={(value) => updateFilter("category", value)}
+           onStatusChange={(value) => updateFilter("status", value)}
+         />
++        {catalogFacetQuery.data && !catalogFacetQuery.data.complete ? (
++          <p
++            className="catalog-facets-incomplete"
++            data-testid="catalog-facets-incomplete"
++            role="status"
++          >
++            筛选选项未完整加载，已隐藏未确认的部分结果。
++          </p>
++        ) : null}
+         {catalogFacetQuery.isError && !catalogQuery.isError ? (
+           <CatalogErrorState onRetry={() => void catalogFacetQuery.refetch()} />
+         ) : null}
+ 
+         <section
+           className="catalog-results"
+           aria-labelledby="catalog-results-heading"
+         >
+           <div className="catalog-results-heading">
+             <div>
+diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
+index 6f4968b..0c1c438 100644
+--- a/frontend/tests/public-catalog.spec.ts
++++ b/frontend/tests/public-catalog.spec.ts
+@@ -21,20 +21,34 @@ const uuidItem = {
+   summary: "生成一个随机 UUID v4，不接受任何查询参数。",
+   category: "tools",
+   method: "GET",
+   path: "/v1/tools/uuid",
+   auth_type: "api_key",
+   is_free: true,
+   status: "published",
+   updated_at: "2026-10-02T00:00:00Z",
+ }
+ 
++const lateFacetItem = {
++  ...uuidItem,
++  slug: "late-facet",
++  name: "后分页接口",
++  category: "data",
++  status: "deprecated",
++  path: "/v1/data/late-facet",
++}
++
++const facetPageOneItems = Array.from({ length: 100 }, (_, index) => ({
++  ...timeItem,
++  slug: `time-${index}`,
++}))
++
+ const timeDetail = {
+   ...timeItem,
+   auth: { type: "api_key", header: "X-API-Key" },
+   parameters: [
+     {
+       name: "timezone",
+       in: "query",
+       required: false,
+       description: "可选的 IANA 时区名称，省略时使用 UTC。",
+       schema: {
+@@ -66,20 +80,32 @@ const timeDetail = {
+     {
+       language: "curl",
+       request:
+         'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
+     },
+   ],
+   source: "Yeyu API",
+   cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
+ }
+ 
++const sensitiveQueryParameters = [
++  { name: "apiKey", value: "1234567890" },
++  { name: "API_KEY", value: "1234567891" },
++  { name: "api-key", value: "1234567892" },
++  { name: "access_token", value: "1234567893" },
++  { name: "Access-Token", value: "1234567894" },
++  { name: "ACCESS.TOKEN", value: "1234567895" },
++  { name: "client_secret", value: "1234567896" },
++  { name: "Client-Secret", value: "1234567897" },
++  { name: "CLIENT.SECRET", value: "1234567898" },
++] as const
++
+ const unsafeDetail = {
+   ...timeDetail,
+   auth: {
+     type: "api_key",
+     header: 'X-Evil-Header: "<NON_SECRET_TEST_VALUE>"',
+   },
+   path: "https://evil.example/redirect?token=<NON_SECRET_TEST_VALUE>",
+   parameters: [
+     ...timeDetail.parameters,
+     {
+@@ -136,20 +162,30 @@ const unsafeDetail = {
+   cache_rules: {
+     ...timeDetail.cache_rules,
+     "provider-ref": "<NON_SECRET_TEST_VALUE>",
+     safe: { nested_password: "<NON_SECRET_TEST_VALUE>" },
+   },
+ }
+ 
+ const unsafeExamplesDetail = {
+   ...unsafeDetail,
+   path: "/v1/tools/time",
++  parameters: [
++    ...unsafeDetail.parameters,
++    ...sensitiveQueryParameters.map(({ name, value }) => ({
++      name,
++      in: "query",
++      required: false,
++      description: "敏感查询参数测试",
++      schema: { type: "string", default: value },
++    })),
++  ],
+ }
+ 
+ type CatalogPage = {
+   data: (typeof timeItem)[]
+   count: number
+   page: number
+   page_size: number
+ }
+ 
+ const catalogListUrl = /\/api\/v1\/catalog(?:\?.*)?$/
+@@ -267,21 +303,21 @@ test("Catalog pagination preserves search filters and requests the selected page
+     const url = new URL(route.request().url())
+     const isFacetRequest =
+       url.searchParams.get("page_size") === "100" &&
+       !url.searchParams.has("query") &&
+       !url.searchParams.has("category") &&
+       !url.searchParams.has("status")
+     if (isFacetRequest) {
+       facetRequests.push(url)
+       const pageNumber = Number(url.searchParams.get("page") ?? "1")
+       const response: CatalogPage = {
+-        data: pageNumber === 2 ? [uuidItem] : [timeItem],
++        data: pageNumber === 1 ? facetPageOneItems : [lateFacetItem],
+         count: 101,
+         page: pageNumber,
+         page_size: 100,
+       }
+       await route.fulfill({
+         status: 200,
+         contentType: "application/json",
+         body: JSON.stringify(response),
+       })
+       return
+@@ -317,38 +353,97 @@ test("Catalog pagination preserves search filters and requests the selected page
+   expect(
+     facetRequests.every(
+       (request) => request.searchParams.get("category") === null,
+     ),
+   ).toBe(true)
+   expect(
+     facetRequests.every(
+       (request) => request.searchParams.get("status") === null,
+     ),
+   ).toBe(true)
++  await expect(page.getByLabel("分类").locator("option")).toContainText("data")
++  await expect(page.getByLabel("状态").locator("option")).toContainText(
++    "deprecated",
++  )
+   await expect(page.getByRole("button", { name: "下一页" })).toBeEnabled()
+ 
+   await page.getByRole("button", { name: "下一页" }).click()
+   await expect(page).toHaveURL(
+     /query=time.*category=tools.*status=published.*page=2/,
+   )
+   await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
+ 
+   const secondRequest = catalogRequests.at(-1)
+   expect(secondRequest?.searchParams.get("page")).toBe("2")
+   expect(secondRequest?.searchParams.get("page_size")).toBe("20")
+ 
+   await page.getByRole("button", { name: "上一页" }).click()
+   await expect(page).toHaveURL(
+     /query=time.*category=tools.*status=published.*page=1/,
+   )
+ })
+ 
++test("Catalog marks facet options incomplete after the page safety limit", async ({
++  page,
++}) => {
++  const facetRequests: URL[] = []
++  await page.route(catalogListUrl, async (route) => {
++    const url = new URL(route.request().url())
++    const isFacetRequest =
++      url.searchParams.get("page_size") === "100" &&
++      !url.searchParams.has("query") &&
++      !url.searchParams.has("category") &&
++      !url.searchParams.has("status")
++    if (isFacetRequest) {
++      facetRequests.push(url)
++      const pageNumber = Number(url.searchParams.get("page") ?? "1")
++      await route.fulfill({
++        status: 200,
++        contentType: "application/json",
++        body: JSON.stringify({
++          data: pageNumber === 100 ? [lateFacetItem] : [timeItem],
++          count: 10_001,
++          page: pageNumber,
++          page_size: 100,
++        }),
++      })
++      return
++    }
++
++    await route.fulfill({
++      status: 200,
++      contentType: "application/json",
++      body: JSON.stringify({
++        data: [timeItem],
++        count: 1,
++        page: 1,
++        page_size: 20,
++      }),
++    })
++  })
++
++  await page.goto("/catalog")
++
++  await expect(page.getByTestId("catalog-facets-incomplete")).toBeVisible()
++  await expect(
++    page.getByText("筛选选项未完整加载", { exact: false }),
++  ).toBeVisible()
++  await expect(page.getByLabel("分类").locator("option")).toHaveText([
++    "全部分类",
++  ])
++  await expect(page.getByLabel("状态").locator("option")).toHaveText([
++    "全部状态",
++  ])
++  await expect.poll(() => facetRequests.length).toBe(100)
++  expect(facetRequests.at(-1)?.searchParams.get("page")).toBe("100")
++})
++
+ test("Catalog displays an explicit empty state for an empty result", async ({
+   page,
+ }) => {
+   await mockCatalogApi(page)
+   await page.goto("/catalog?query=missing")
+ 
+   await expect(page.getByTestId("catalog-empty")).toBeVisible()
+   await expect(page.getByText("没有找到匹配的公开接口")).toBeVisible()
+   await expect(page.getByTestId("catalog-grid")).not.toBeVisible()
+ })
+@@ -419,20 +514,24 @@ test("Detail omits unsafe parameter examples from every code sample", async ({
+   expect(renderedExamples).toContain("X-API-Key")
+   expect(renderedExamples).toContain("<YOUR_API_KEY>")
+   expect(renderedExamples).not.toContain('bad"name`$()')
+   expect(renderedExamples).not.toContain(
+     "https://evil.example/?next=<NON_SECRET_TEST_VALUE>",
+   )
+   expect(renderedExamples).not.toContain("$(whoami)")
+   expect(renderedExamples).not.toContain("`id`")
+   expect(renderedExamples).not.toContain("secret-token-<NON_SECRET_TEST_VALUE>")
+   expect(renderedExamples).not.toContain("X-Evil-Header")
++  for (const { name, value } of sensitiveQueryParameters) {
++    expect(renderedExamples).not.toContain(name)
++    expect(renderedExamples).not.toContain(value)
++  }
+ })
+ 
+ test("Detail errors do not render stale detail data", async ({ page }) => {
+   let detailRequestCount = 0
+   await page.route(catalogTimeDetailUrl, async (route) => {
+     detailRequestCount += 1
+     if (detailRequestCount === 1) {
+       await route.fulfill({
+         status: 200,
+         contentType: "application/json",
+diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
+index cf690f4..2cdb6de 100644
+--- a/plans/agent-reports/task-7-3-report.md
++++ b/plans/agent-reports/task-7-3-report.md
+@@ -226,10 +226,39 @@ exit 0
+ pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+ exit 0
+ Checked 4 files in 10ms. No fixes applied.
+ 
+ git diff --check
+ exit 0
+ 仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
+ ```
+ 
+ 本轮没有运行 Playwright、前端 build、后端 pytest、路由生成、真实浏览器或线上验收；因此新增浏览器断言、TypeScript 完整检查、实际后端跨页响应和线上结果仍未验证。修复提交主题：`fix: harden catalog examples and filters`。
++
++## 11. 第二次复审 Important 收口（2026-10-02）
++
++本次仅修复 `task-7-3-second-fix-review.md` 指出的两个 Important；未修改 `frontend/src/routeTree.gen.ts`、认证/公共壳层、后端、线上服务、DNS、Nginx 或凭据。
++
++### 11.1 敏感 query 参数名和值
++
++- `normalizeSafeQueryKey` 现在在格式校验后复用统一的敏感字段规范化判定；`apiKey`、`API_KEY`、`api-key`、`access_token`、`Access-Token`、`ACCESS.TOKEN`、`client_secret`、`Client-Secret`、`CLIENT.SECRET` 等变体不会进入示例。
++- 回归夹具为这些敏感名称提供仅由合法字符组成的数值，断言三种代码示例均不包含名称或值；固定认证头仍为 `X-API-Key: <YOUR_API_KEY>`，既有内部路径和外部 URL 防护保持不变。
++
++### 11.2 facets 上限不完整状态
++
++- 新增 `CatalogFacetResult` 完成度类型；达到 100 页上限时返回 `complete: false`、`reason: "page-limit"`，并丢弃部分 items。
++- 页面显示 `catalog-facets-incomplete` 状态，且不会把被截断的部分结果传给 `CatalogFilters`；只有按 `count` 或空页停止时才使用已收集 facet。
++- 回归夹具第 1 页返回 100 条、第 2 页返回唯一 `data`/`deprecated` 项并断言其进入筛选选项；另以 `count=10001` 覆盖请求到第 100 页后的显式不完整状态及空筛选选项。
++
++### 11.3 本次真实静态验证
++
++```text
++pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
++exit 0
++Checked 3 files in 12ms. No fixes applied.
++
++git diff --check
++exit 0
++仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
++```
++
++本次没有运行 Playwright、前端 build、后端测试、路由生成、TypeScript 完整检查或线上验收；因此新增浏览器回归断言和完整类型/运行时行为仍未验证。
diff --git a/plans/agent-reports/task-7-3-third-fix-review.md b/plans/agent-reports/task-7-3-third-fix-review.md
new file mode 100644
index 0000000..d225784
--- /dev/null
+++ b/plans/agent-reports/task-7-3-third-fix-review.md
@@ -0,0 +1,24 @@
+# Task 7-3 第三次修复独立复审
+
+## 复审范围
+
+- 修复提交：`6d3c163`
+- Diff：`E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-third-fix-diff.md`
+- 关联问题计划：`E:\AI_projects\yeyu-api\plans\fix-task-7-3-second-review-findings.md`
+- 方式：全新只读子代理复审；未修改文件、未提交、未推送。
+
+## 结论
+
+**Approved。** 无 Critical、无 Important。
+
+## 已确认
+
+- 敏感参数名通过大小写及符号归一化拒绝；危险值仍有格式、URL scheme、敏感关键词和 JWT 过滤；示例固定使用 `X-API-Key: <YOUR_API_KEY>`。
+- facets 达到 100 页上限时返回 `complete: false`、清空部分集合并显示不完整提示；测试证明后续分页的 `data/deprecated` 会进入筛选项，截断时筛选项被隐藏。
+- 未发现新的 URL、分页、React 回归。
+
+## Minor / 未验证
+
+- facets 请求失败时仍使用通用错误提示，并回退到当前目录页生成筛选项，语义不够精确；这是既有 Minor，不阻塞本任务。
+- 完整 `tsc` 仍有既有的生成路由树、`replaceAll`/ES2020 等环境或基线错误；本次复审未发现本次变更新增相关类型错误。
+- 本次复审未运行 Playwright、build 或后端测试。
diff --git a/plans/fix-task-7-3-catalog-review-findings.md b/plans/fix-task-7-3-catalog-review-findings.md
new file mode 100644
index 0000000..9d91c89
--- /dev/null
+++ b/plans/fix-task-7-3-catalog-review-findings.md
@@ -0,0 +1,67 @@
+# Task 7-3 Catalog Review Findings Fix Plan
+
+> **For agentic workers:** Execute this plan in the current `E:\AI_projects\yeyu-api` worktree. Keep the existing public shell and generated route tree unchanged.
+
+**Goal:** Close the five Important findings from the Task 7-3 read-only review with the smallest safe frontend changes and focused regression coverage.
+
+**Architecture:** Keep catalog state in TanStack Router search params. Add pure path and metadata guards in `catalog-types.ts`, use those guards at every detail rendering boundary, and keep pagination as a focused `CatalogPagination` component. Make the detail route render exactly one loading, error, or success state.
+
+**Tech Stack:** React, TypeScript, TanStack Router, TanStack Query, generated `CatalogService`, Playwright route mocks, Biome.
+
+## Global Constraints
+
+- Modify only the Task 7-3 frontend catalog files, focused catalog tests, this plan, and the Task 7-3 report.
+- Do not edit `frontend\src\routeTree.gen.ts`, Task 2 authentication/public shell behavior, backend, online services, DNS, Nginx, or credentials.
+- Use `https://api.yeyubaka.top` only as the controlled public API base in generated examples.
+- Retain `<YOUR_API_KEY>` and use `<NON_SECRET_TEST_VALUE>` for any sensitive-looking test value.
+- Write or update regression tests before implementation; do not run long Playwright or build commands.
+
+### Task 1: Add failing regression coverage
+
+**Files:**
+- Modify: `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`
+
+- [ ] Replace the broad catalog glob with separate regular expressions for `/api/v1/catalog` list URLs with optional query strings and `/api/v1/catalog/time` detail URLs.
+- [ ] Add route-mocked assertions for page 2 and page 1 navigation while retaining `query`, `category`, and `status`.
+- [ ] Add route-mocked detail data containing an unsafe absolute path and sensitive nested keys, then assert the unsafe host and `<NON_SECRET_TEST_VALUE>` are absent from rendered examples/metadata.
+- [ ] Add a stale-detail failure flow that asserts the detail error state does not render the previous detail heading.
+- [ ] Run only the permitted short static check on the updated test file; do not run Playwright.
+
+### Task 2: Harden detail path and metadata boundaries
+
+**Files:**
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`
+
+**Interfaces:**
+- `normalizeInternalApiPath(value: unknown): string | undefined` trims and accepts only a single-slash internal path without `http(s)`, `//`, backslash, query/hash, percent encoding, or `..`.
+- `sanitizeMetadata(value: unknown): unknown` recursively removes object keys whose normalized lowercase form contains `token`, `secret`, `password`, `authorization`, `cookie`, `apikey`, `credential`, `privatekey`, or `providerref`.
+- `formatMetadata` sanitizes before JSON formatting; `responseProperties`, parameter display/examples, error display, and cache display consume sanitized values.
+
+- [ ] Implement the two pure guards in `catalog-types.ts` without changing generated client types.
+- [ ] Build curl, JavaScript, and Python snippets from the controlled base plus the normalized path; render `路径不可用` and a non-URL message when the backend path is rejected.
+- [ ] Keep `<YOUR_API_KEY>` unchanged and do not add arbitrary URL input or credential reads.
+
+### Task 3: Add legal page state and mutually exclusive detail states
+
+**Files:**
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
+- Create: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx`
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx`
+
+- [ ] Add `page: number` to parsed search state, normalize only positive safe integers, and default invalid/missing input to 1.
+- [ ] Include `page` in the query key and send `page` plus `page_size: 20` to `CatalogService.searchCatalog`.
+- [ ] Reset `page` to 1 on debounced query changes and category/status changes while preserving the other search params.
+- [ ] Render accessible previous/next controls using `count` and `page_size`; disable controls at boundaries and while fetching.
+- [ ] Render detail loading, error, and success as an exclusive branch so stale detail data is hidden when `isError` is true.
+
+### Task 4: Verify and record evidence
+
+**Files:**
+- Modify: `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-report.md`
+
+- [ ] Run targeted Biome on every changed frontend source/test file and record the real exit code/output.
+- [ ] Run `git diff --check` and record the real result, including any non-failure line-ending warning.
+- [ ] Do not claim Playwright, build, backend tests, route generation, or browser acceptance unless actually run; record them as unverified.
+- [ ] Inspect the final diff and status, append the five fixes and evidence to the report, then commit with `fix: close catalog review findings`.
diff --git a/plans/fix-task-7-3-second-review-findings.md b/plans/fix-task-7-3-second-review-findings.md
new file mode 100644
index 0000000..cb0d1f0
--- /dev/null
+++ b/plans/fix-task-7-3-second-review-findings.md
@@ -0,0 +1,26 @@
+# Task 7-3 第二次复审问题修复计划
+
+## 目标
+
+修复 `9c901eb` 之后独立复审发现的两个 Important，并保留真实验证边界：
+
+1. 代码示例不得从目录参数中带出敏感查询字段（包括 `apiKey`、`access_token`、`client_secret` 等），同时继续只使用固定 API Key 请求头和安全参数值。
+2. facets 不能在达到分页上限后静默伪装成完整目录；必须显式表达未完整加载，或采用可证明完整的停止条件，并补测试证明后续分页中的分类/状态进入筛选选项。
+
+## 允许修改范围
+
+- `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
+- `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`
+- `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`
+- `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`
+- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-report.md`
+
+禁止修改生成路由树、认证/公共壳层、后端、服务器、DNS、Nginx、旧项目和任何凭据。
+
+## 实施与验证要求
+
+- 先补充或改写针对敏感参数名、完整 facets 分页和截断/错误状态的回归断言，再实现最小修复。
+- 不得用静默截断作为“完整目录”；若保留客户端分页抓取，必须在达到上限时返回明确的不完整状态并避免将未加载值当成已知 facet。
+- 运行针对变更文件的 Biome 和 `git diff --check`，在报告中记录命令与真实结果。
+- 不运行或声称通过长时间 Playwright、构建、后端集成、路由生成或线上验收；如额外运行必须记录实际结果。
+- 修复完成后创建清晰提交，并等待新的独立只读复审。
diff --git a/plans/task-7-public-catalog-ui.md b/plans/task-7-public-catalog-ui.md
index a35a0c9..e5b8c4d 100644
--- a/plans/task-7-public-catalog-ui.md
+++ b/plans/task-7-public-catalog-ui.md
@@ -32,156 +32,160 @@
 ## Task 1: Add Idempotent Public Catalog Seeds
 
 **Files:**
 
 - Create E:\AI_projects\yeyu-api\backend\app\catalog_seed.py
 - Modify E:\AI_projects\yeyu-api\backend\app\initial_data.py
 - Create E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py
 
 ### Implementation
 
-- [ ] 在测试中构造 SQLite 或项目现有测试 session，验证初次调用 seed_public_catalog(session) 会创建且只创建 time、uuid 两条 ApiDefinition。
-- [ ] 在测试中验证两次调用结果完全幂等，第二次不增加记录、不重置 updated_at、不覆盖管理员已经修改的 summary、status、examples 或 cache_rules。
-- [ ] 在测试中验证种子数据的 adapter_name 只能是 builtin-tools，visibility 为 public，status 为 published 或 healthy，auth_type 为 api_key，is_free 为真，路径分别为 /v1/tools/time 与 /v1/tools/uuid。
-- [ ] 在测试中验证示例请求不包含真实密钥，示例只出现 <YOUR_API_KEY> 占位符；验证 time 具有可选 timezone 参数，uuid 不允许参数。
-- [ ] 在 catalog_seed.py 暴露不可变的 PUBLIC_CATALOG_SEEDS 和 seed_public_catalog(session)，使用显式 slug 查询缺失记录后新增，不调用会覆盖已有字段的批量 upsert。
-- [ ] 为 time 和 uuid 填写面向开发者的中文 name、summary、category、method、path、parameters、response_schema、error_codes、examples、source_label、cache_rules；元数据必须与实际 builtin adapter 返回值一致。
-- [ ] 在 initial_data.init() 的现有 init_db(session) 之后调用 seed_public_catalog(session)，保留原有超级用户初始化行为。
-- [ ] 不在种子文件中读取环境变量中的密钥，不调用第三方网络，不写日志中的敏感信息。
+- [x] 在测试中构造 SQLite 或项目现有测试 session，验证初次调用 seed_public_catalog(session) 会创建且只创建 time、uuid 两条 ApiDefinition。
+- [x] 在测试中验证两次调用结果完全幂等，第二次不增加记录、不重置 updated_at、不覆盖管理员已经修改的 summary、status、examples 或 cache_rules。
+- [x] 在测试中验证种子数据的 adapter_name 只能是 builtin-tools，visibility 为 public，status 为 published 或 healthy，auth_type 为 api_key，is_free 为真，路径分别为 /v1/tools/time 与 /v1/tools/uuid。
+- [x] 在测试中验证示例请求不包含真实密钥，示例只出现 <YOUR_API_KEY> 占位符；验证 time 具有可选 timezone 参数，uuid 不允许参数。
+- [x] 在 catalog_seed.py 暴露不可变的 PUBLIC_CATALOG_SEEDS 和 seed_public_catalog(session)，使用显式 slug 查询缺失记录后新增，不调用会覆盖已有字段的批量 upsert。
+- [x] 为 time 和 uuid 填写面向开发者的中文 name、summary、category、method、path、parameters、response_schema、error_codes、examples、source_label、cache_rules；元数据必须与实际 builtin adapter 返回值一致。
+- [x] 在 initial_data.init() 的现有 init_db(session) 之后调用 seed_public_catalog(session)，保留原有超级用户初始化行为。
+- [x] 不在种子文件中读取环境变量中的密钥，不调用第三方网络，不写日志中的敏感信息。
 
 ### Verification
 
-- [ ] 使用项目 conda 环境 yeyu-api 执行：
+- [x] 使用项目 conda 环境 yeyu-api 执行：
 
 ~~~powershell
 conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q
 ~~~
 
-- [ ] 使用项目 conda 环境执行：
+- [x] 使用项目 conda 环境执行：
 
 ~~~powershell
 conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app\catalog_seed.py E:\AI_projects\yeyu-api\backend\app\initial_data.py E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py
 ~~~
 
-- [ ] 记录 pytest 和 ruff 的真实输出；若数据库依赖导致环境阻塞，只记录阻塞原因，不将未运行结果标为通过。
-- [ ] 独立只读子代理检查种子幂等性、适配器字段一致性、敏感数据边界和测试充分性，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md。
-- [ ] 处理审查报告中的 Critical 或 Important 问题后重新运行上述测试，再创建提交 feat: seed public builtin catalog 并推送 origin/main。
+- [x] 记录 pytest 和 ruff 的真实输出；若数据库依赖导致环境阻塞，只记录阻塞原因，不将未运行结果标为通过。
+- [x] 独立只读子代理检查种子幂等性、适配器字段一致性、敏感数据边界和测试充分性，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md。
+- [x] 处理审查报告中的 Critical 或 Important 问题后重新运行上述测试，再创建提交 feat: seed public builtin catalog 并推送 origin/main。
 
 ## Task 2: Split Public and Protected Route Shells
 
 **Files:**
 
 - Create E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\routes\_layout\dashboard.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicLayout.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicFooter.tsx
 - Delete E:\AI_projects\yeyu-api\frontend\src\routes\_layout\index.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\routes\_layout.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\hooks\useAuth.ts
 - Modify E:\AI_projects\yeyu-api\frontend\src\routes\login.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\components\Sidebar\AppSidebar.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\components\Common\Logo.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\components\Common\Footer.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\index.css
+- Modify E:\AI_projects\yeyu-api\frontend\package.json
+- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx
 - Create or modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
 - Modify E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts
 
 ### Implementation
 
-- [ ] 先更新 Playwright 断言：匿名访问 / 不跳转 /login；匿名访问 /catalog 不跳转 /login；登录成功后的目标为 /dashboard；受保护的 /items 仍在未登录时跳转 /login。
-- [ ] 实现 PublicLayout、PublicHeader、PublicFooter，导航至少包含首页、API 目录、登录；移动端提供可访问的折叠菜单或等价的键盘可用导航；登录状态下显示控制台入口。
-- [ ] 将受保护根页面从 _layout/index.tsx 迁移为 _layout/dashboard.tsx，路由标题改为 Yeyu API 控制台，保留当前用户欢迎信息，不把公共首页内容复制到控制台。
-- [ ] 将 useAuth 登录成功跳转、GitHub callback 成功跳转和 login.tsx 的已登录重定向统一改为 /dashboard；登录失败、回调失败和登出行为保持现有语义。
-- [ ] 将侧边栏 Dashboard 链接改为 /dashboard，避免继续指向公共首页；更新 Logo 和 Footer，移除 FastAPI Template 品牌、链接和文案，替换为 Yeyu API 公益平台信息。
-- [ ] 让 E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx 使用 PublicLayout 作为公共首页入口，首页只渲染真实目录数据、搜索入口、公益说明和使用规范入口；数据加载失败时显示明确的错误状态，不伪造接口卡片。
-- [ ] 修改 index.css 建立设计变量：纸白背景、墨色正文、青绿色主色、浅青绿色表面、琥珀色警示色和可见焦点环；保留 Tailwind/shadcn 现有组件可用，不引入远程 CSS。
-- [ ] 保证公共壳层的 main、导航、按钮、表单控件有语义标签、键盘焦点、可读颜色和移动端溢出处理。
+- [x] 先更新 Playwright 断言：匿名访问 / 不跳转 /login；匿名访问 /catalog 不跳转 /login；登录成功后的目标为 /dashboard；受保护的 /items 仍在未登录时跳转 /login。
+- [x] 实现 PublicLayout、PublicHeader、PublicFooter，导航至少包含首页、API 目录、登录；移动端提供可访问的折叠菜单或等价的键盘可用导航；登录状态下显示控制台入口。
+- [x] 将受保护根页面从 _layout/index.tsx 迁移为 _layout/dashboard.tsx，路由标题改为 Yeyu API 控制台，保留当前用户欢迎信息，不把公共首页内容复制到控制台。
+- [x] 将 useAuth 登录成功跳转、GitHub callback 成功跳转和 login.tsx 的已登录重定向统一改为 /dashboard；登录失败、回调失败和登出行为保持现有语义。
+- [x] 将侧边栏 Dashboard 链接改为 /dashboard，避免继续指向公共首页；更新 Logo 和 Footer，移除 FastAPI Template 品牌、链接和文案，替换为 Yeyu API 公益平台信息。
+- [x] 让 E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx 使用 PublicLayout 作为公共首页入口，首页只渲染真实目录数据、搜索入口、公益说明和使用规范入口；数据加载失败时显示明确的错误状态，不伪造接口卡片。
+- [x] 修改 index.css 建立设计变量：纸白背景、墨色正文、青绿色主色、浅青绿色表面、琥珀色警示色和可见焦点环；保留 Tailwind/shadcn 现有组件可用，不引入远程 CSS。
+- [x] 保证公共壳层的 main、导航、按钮、表单控件有语义标签、键盘焦点、可读颜色和移动端溢出处理。
 
 ### Verification
 
-- [ ] 执行前端格式与类型构建：
+- [x] 执行前端格式与类型构建：
 
 ~~~powershell
 Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
 pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
 pnpm build
 ~~~
 
-- [ ] 执行只覆盖路由边界的 Playwright 测试：
+- [x] 执行只覆盖路由边界的 Playwright 测试：
 
 ~~~powershell
 Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
 pnpm exec playwright test tests/public-catalog.spec.ts tests/login.spec.ts
 ~~~
 
-- [ ] 记录构建、Biome 和 Playwright 的实际结果；没有运行 Docker 依赖时标明具体阻塞。
-- [ ] 独立只读子代理检查路由树迁移是否完整、匿名/登录边界、键盘可用性、品牌残留和是否误触及旧项目，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-2-review.md。
-- [ ] 处理审查问题后重新构建和运行边界测试，创建提交 feat: split public and protected web shells 并推送 origin/main。
+- [x] 记录构建、Biome 和 Playwright 的实际结果；没有运行 Docker 依赖时标明具体阻塞。
+- [x] 独立只读子代理检查路由树迁移是否完整、匿名/登录边界、键盘可用性、品牌残留和是否误触及旧项目，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-2-review.md。
+- [x] 处理审查问题后重新做静态检查和构建尝试，创建提交 feat: split public and protected web shells 并推送 origin/main；修复后的 Playwright 因 Chromium 缺失保持未验证。
 
 ## Task 3: Build Search-First Catalog and Detail Pages
 
 **Files:**
 
 - Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts
 - Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogSearch.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogFilters.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogCard.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogGrid.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogStates.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx
 - Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CodeExample.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
 - Modify E:\AI_projects\yeyu-api\frontend\src\index.css
 - Modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
 
 ### Implementation
 
-- [ ] 在测试中覆盖目录页匿名可访问、搜索参数能反映到 URL、分类筛选能反映到 URL、空结果有明确状态、详情页展示 /v1/tools/time、GET、API Key 鉴权、参数、响应字段和错误码。
-- [ ] 目录页通过生成的 CatalogService.getCatalog 和 React Query 获取分页数据，query、category、status 使用 TanStack Router search params 作为唯一可分享状态；输入搜索设置 300 至 500 毫秒防抖并避免逐键请求。
-- [ ] 目录页首屏顺序固定为页面标题与搜索框、分类/状态筛选、真实目录卡片；卡片包含名称、中文简介、请求方法、路径、免费标记、健康/发布状态和更新时间，点击后进入 /catalog/:slug。
-- [ ] 目录页只展示后端返回数据，不在前端硬编码候选接口；API 返回空、错误和加载状态分别使用可读的 Empty、Error、Skeleton 组件。
-- [ ] 详情页通过生成的 CatalogService.getCatalogDetail({ path: { slug } }) 获取数据；展示鉴权说明、参数表、响应结构、错误码、缓存规则、来源标签和 curl、JavaScript、Python 示例。
-- [ ] 代码示例只显示 <YOUR_API_KEY>，统一从当前域名拼接请求 URL，不保存或读取真实 API Key，不提供任意 URL 输入；复制按钮使用可访问名称并在成功后有非颜色反馈。
-- [ ] 首页保持索引台视觉：上方以一句清晰定位和主搜索入口为主，下面展示由真实目录 API 返回的精选工具卡片、一个可直接跳转的 Quick Start 区块和公益/使用边界说明；不展示假统计。
-- [ ] 公共导航在首页、目录页和详情页保持一致；目录页搜索框支持从首页带 query 参数跳转后继续搜索。
-- [ ] 移动端将详情页的参数表、代码块和路径行处理为可横向滚动而不撑破页面；桌面端使用窄内容列、明显分隔线和稳定状态色。
+- [x] 在测试中覆盖目录页匿名可访问、搜索参数能反映到 URL、分类筛选能反映到 URL、空结果有明确状态、详情页展示 /v1/tools/time、GET、API Key 鉴权、参数、响应字段和错误码。
+- [x] 目录页通过生成的 CatalogService.getCatalog 和 React Query 获取分页数据，query、category、status 使用 TanStack Router search params 作为唯一可分享状态；输入搜索设置 300 至 500 毫秒防抖并避免逐键请求。
+- [x] 目录页首屏顺序固定为页面标题与搜索框、分类/状态筛选、真实目录卡片；卡片包含名称、中文简介、请求方法、路径、免费标记、健康/发布状态和更新时间，点击后进入 /catalog/:slug。
+- [x] 目录页只展示后端返回数据，不在前端硬编码候选接口；API 返回空、错误和加载状态分别使用可读的 Empty、Error、Skeleton 组件。
+- [x] 详情页通过生成的 CatalogService.getCatalogDetail({ path: { slug } }) 获取数据；展示鉴权说明、参数表、响应结构、错误码、缓存规则、来源标签和 curl、JavaScript、Python 示例。
+- [x] 代码示例只显示 <YOUR_API_KEY>，统一从当前域名拼接请求 URL，不保存或读取真实 API Key，不提供任意 URL 输入；复制按钮使用可访问名称并在成功后有非颜色反馈。
+- [x] 首页保持索引台视觉：上方以一句清晰定位和主搜索入口为主，下面展示由真实目录 API 返回的精选工具卡片、一个可直接跳转的 Quick Start 区块和公益/使用边界说明；不展示假统计。
+- [x] 公共导航在首页、目录页和详情页保持一致；目录页搜索框支持从首页带 query 参数跳转后继续搜索。
+- [x] 移动端将详情页的参数表、代码块和路径行处理为可横向滚动而不撑破页面；桌面端使用窄内容列、明显分隔线和稳定状态色。
 
 ### Verification
 
-- [ ] 执行前端构建与静态检查：
+- [x] 执行前端静态检查：
 
 ~~~powershell
 Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
 pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
-pnpm build
 ~~~
 
-- [ ] 在项目 Docker Compose 测试环境可用时执行：
+- [ ] 前端构建：`pnpm build` 已实际尝试，但当前工作站的 `@swc/core` 原生绑定缺失且 SWC 缓存目录 DACL 阻止物化，未通过；不得把构建标为通过。
+
+- [ ] 在项目 Docker Compose 测试环境可用时执行（已实际尝试 Playwright setup，但认证页 30 秒内未出现 `email-input`，目录用例未执行）：
 
 ~~~powershell
 Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
 pnpm exec playwright test tests/public-catalog.spec.ts
 ~~~
 
-- [ ] 通过 API 测试确认种子后端实际提供目录数据：
+- [ ] 通过 API 测试确认种子后端实际提供目录数据（已实际尝试，测试收集被缺失 `backend\app\frontend` 构建目录阻塞）：
 
 ~~~powershell
 conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py -q
 ~~~
 
-- [ ] 使用真实浏览器尺寸至少检查 1280 像素桌面视口和 390 像素移动视口；记录页面 URL、公开/受保护结果、控制台错误和截图路径。截图若用于审查，只放在项目外部临时目录。
-- [ ] 独立只读子代理检查 API client 使用、URL 状态同步、错误/空状态、示例密钥脱敏、移动端溢出、可访问性和视觉方案偏离，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-review.md。
-- [ ] 处理审查问题后重跑构建、API 测试和浏览器测试，创建提交 feat: add public catalog and api detail pages 并推送 origin/main。
+- [ ] 使用真实浏览器尺寸至少检查 1280 像素桌面视口和 390 像素移动视口；当前 Playwright setup 阻塞，未获得有效桌面/移动验收证据。
+- [x] 独立只读子代理检查 API client 使用、URL 状态同步、错误/空状态、示例密钥脱敏、移动端溢出、可访问性和视觉方案偏离，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-review.md；后续 Important 修复及第三次 Approved 复审也已记录在同目录。
+- [x] 已处理审查中的 Critical/Important，创建实现与修复提交；代码提交在本地已完成，推送在本次证据整理后执行。
 
 ## Task 4: Whole-Phase Verification and Handoff
 
 **Files:**
 
 - Modify E:\AI_projects\yeyu-api\plans\task-7-public-catalog-ui.md
 - Create E:\AI_projects\yeyu-api\plans\agent-reports\task-7-final-review.md
 - Update E:\AI_projects\yeyu-api\.git\sdd\progress.md only if the subagent workflow has initialized this ledger
 
 ### Verification
