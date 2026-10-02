# Task 7：管理端、健康检查、审计与日志脱敏实施计划

## 0. 状态与边界

- 状态：待独立子代理审查，审查通过后执行。
- 项目根目录：E:\AI_projects\yeyu-api。
- 本阶段不修改 E:\AI_projects\yeyubakahome_Web，不访问或修改 new.api.yeyubaka.top，不执行 DNS、Nginx、证书、服务器或生产凭据变更。
- 本阶段不引入任意 URL、开放代理、任意第三方上游或试验池中的真实 Secret。
- 所有测试凭据只使用非敏感占位值；命令输出必须脱敏。

## 1. 目标与可验收结果

本阶段完成以下可在本地验证的能力：

1. 普通用户不能通过 API 路径、前端隐藏、伪造请求或直接访问管理路由获得管理权限；现有 superuser 保护统一复用并有独立测试。
2. 新增根路径 GET /health 和 GET /ready：
   - /health 只表示进程存活，不访问外部依赖；
   - /ready 检查 PostgreSQL、Redis 和 Alembic 迁移状态；
   - 响应不包含数据库 URL、Redis URL、异常堆栈、Secret 或连接字符串。
3. 审计事件以 PostgreSQL 权威保存，记录管理操作的操作者、动作、对象、结果、请求 ID 和经过脱敏/限长的元数据；不保存密码、API Key、OAuth token、Cookie 或请求正文。
4. 结构化请求日志只记录 request ID、固定 API slug（若可识别）、HTTP 状态、耗时、缓存命中/过期回退状态和错误分类；不记录请求正文、完整查询参数、认证头、原始 IP 或 IP 摘要。
5. 管理端可查看和维护用户、API 元数据、策略、status=trial 的候选接口池、依赖健康摘要和审计记录；页面权限只是体验层，后端仍强制校验。
6. 候选接口试验池复用现有 ApiDefinition.status = "trial"，只允许固定 adapter 和内部 provider_ref 标识；不创建可以填写任意 URL 的字段，也不把上游凭据回显到 API 或页面。
7. 迁移、单元测试、路由测试、前端类型检查、静态检查和独立安全审查都有真实证据；构建或 Playwright 受环境阻塞时要单独记录，不能以健康检查代替产品验收。

## 2. 对当前代码的事实约束

实现前以仓库当前代码为准，以下事实已只读确认：

- 后端使用 E:\AI_projects\yeyu-api\backend\app\api\deps.py 中的 get_current_active_superuser；不得另造一套互相不一致的 superuser 判断。
- E:\AI_projects\yeyu-api\backend\app\api\main.py 已注册 users、admin_catalog 和 admin_policies；新增路由要显式注册，且不要与现有路径冲突。
- E:\AI_projects\yeyu-api\backend\app\models.py 已有 ApiDefinition、ApiPolicy、UsageDaily、CacheEntry；ApiDefinition.provider_ref 是内部引用字符串，不是 URL。
- Alembic 版本位于 E:\AI_projects\yeyu-api\backend\app\alembic\versions\，不是 backend\alembic\。
- E:\AI_projects\yeyu-api\backend\app\main.py 当前无 /health、/ready，并且前端静态目录在某些本地测试环境可能不存在；测试必须能在没有前端构建产物时导入后端应用。
- 前端路由使用 TanStack Router 文件路由；E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts 只能由官方生成器刷新，禁止手工编辑。

## 3. 设计决定

### 3.1 管理权限

保留 get_current_active_superuser 作为唯一后端授权依赖。对需要审计操作者的 mutation 路由，不仅使用 decorator dependency，还显式注入 CurrentUser，以便将 current_user.id 写入审计事件。普通用户、未登录用户和失效会话均返回现有约定的 403/认证错误，不泄露管理资源存在性。

### 3.2 审计数据模型

新增 AuditEvent SQLModel 表，字段固定为：

    id: UUID primary key
    actor_id: UUID | None, foreign key user.id, on delete SET NULL
    request_id: str | None, max 128, indexed
    action: str, max 64, indexed
    object_type: str, max 64, indexed
    object_id: str, max 128
    outcome: str, max 32, indexed
    details: JSON, non-null, already sanitized and bounded
    created_at: UTC datetime, indexed

不保存原始 IP，也不在本阶段生成 IP 摘要；details 只允许 JSON 基本类型、固定键名和最大深度/总长度，禁止将 Pydantic request body、异常对象或 ORM 对象直接传入。

AuditService 构造时接收 Session，公开接口为：

    record(
        actor_id: UUID | None,
        action: str,
        object_type: str,
        object_id: str,
        outcome: str,
        metadata: Mapping[str, object],
        *,
        request_id: str | None = None,
    ) -> None

服务内部先调用 RedactionService.sanitize_metadata，再校验 action/object/outcome 的长度和允许字符，创建 AuditEvent 并加入传入的 Session；AuditService.record 不得自行 commit。业务 mutation 与 AuditEvent 必须共用同一个 Session/事务，由 route/service 的唯一提交点统一 commit，任何异常统一 rollback。写审计失败不能把 Secret 写进日志；管理 mutation 在审计写失败时回滚并返回安全的 503，避免出现“操作成功但无审计”的静默状态。

### 3.3 脱敏与日志

新增 E:\AI_projects\yeyu-api\backend\app\services\redaction.py，至少提供：

    sanitize_headers(headers: Mapping[str, str]) -> dict[str, str]
    sanitize_metadata(metadata: Mapping[str, object]) -> dict[str, object]

大小写、连字符和下划线归一化后，以下键一律替换为 [REDACTED]：authorization、x-api-key、cookie、set-cookie、password、secret、client-secret、access-token、refresh-token、oauth-token 以及带有 token 的认证键。嵌套 mapping/list 递归处理；深度、字符串、列表和最终 JSON 字节数均设置上限，超限只保留安全的 [TRUNCATED] 标记。未知对象不调用其 repr，统一转为类型标记，避免异常对象或连接对象泄露信息。

新增请求日志中间件/日志辅助模块，禁止读取或记录 request body。public_api 在已有执行结果产生处向 request.state 写入 api_slug、request_id、cache_hit、stale 和安全错误分类；中间件只从 state 和响应头读取这些字段，记录 method、路由模板/固定 slug、status、latency_ms、request_id、cache_hit、stale、error_category。认证头、Cookie、查询值和正文不进入日志。

### 3.4 健康与就绪

新增 E:\AI_projects\yeyu-api\backend\app\api\routes\health.py，由应用根路由注册：

- GET /health：始终只返回固定结构 {"status": "ok"}，不连接数据库/Redis；
- GET /ready：依次执行数据库 SELECT 1、Redis PING、迁移版本检查；全部通过返回 200 {"status": "ready"}，任一失败返回 503 {"status": "not_ready", "checks": {"database": "failed", "redis": "failed", "migrations": "failed"}}。只返回固定依赖状态，不返回异常文本、URL 或版本表细节。

迁移检查读取 Alembic alembic_version 与代码当前 head 比较；当前迁移链末端是 20261003_add_usage_cache_tables，新迁移必须明确使用它作为 down_revision。当数据库尚未迁移或 head 不匹配时 /ready 必须失败。检查函数以依赖/可替换函数形式实现，RedisStore 增加只返回布尔/固定状态的 ping() 抽象；单元测试使用非敏感 fake，不要求本机真实 Redis/PostgreSQL 才能覆盖分支。

### 3.5 管理 API 与候选接口池

- 新增 GET /api/v1/admin/catalog，仅 superuser 可访问，支持 status（只允许 trial、healthy、published）和分页；返回 ApiDefinition 的公开管理元数据与内部 adapter/provider 引用，不返回任何凭据。
- 现有 admin_catalog mutation 增加审计，并继续通过固定 adapter/provider 校验；不得接受 arbitrary URL。
- status=trial 作为候选试验池，前端通过固定筛选呈现；不新增独立表，避免重复事实源。
- 现有 admin_policies、users mutation 增加审计，策略值继续复用现有 Pydantic/SQLModel 范围校验。
- 新增 GET /api/v1/admin/audit，仅 superuser 可访问，支持固定 action/outcome 过滤与分页，响应只包含已存储脱敏字段；不提供任意 JSON 查询或全文 grep。
- 新增 GET /api/v1/admin/health，仅 superuser 可访问，复用同一就绪检查器并返回固定的依赖状态摘要；不得返回连接字符串、异常文本或迁移版本值。

固定 adapter/provider 边界必须由三层共同保证：catalog schema 的 allowlist/格式校验、catalog service 的固定 registry 校验、执行 registry 的固定 adapter 校验。当前已有 builtin-tools schema/registry 校验和 content adapter 的内部 provider_ref 格式校验，本阶段要补齐覆盖测试并确保 admin mutation 不能绕过它们。任何包含 http://、https://、主机名、端口、协议相对 URL、未知 adapter 或未知 provider 的值都必须被拒绝；数据库约束至少限制 status/adapter_name/path/provider_ref 的长度、非空关系和 URL 形态。试验池只代表待审核的内部定义，不代表允许用户配置上游地址。

### 3.6 前端管理区

新增文件路由（文件路径以当前 TanStack Router 约定为准）：

- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-apis.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-policies.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-trial-pool.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-audit.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-health.tsx

调整 E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin.tsx 为管理入口/用户管理，并在管理入口提供到各子页面的明确导航。页面加载时调用 UsersService.readUserMe() 做体验级重定向，但所有数据请求仍依赖后端 403。普通用户直接访问这些路由只能回到公开页/登录页，不能因为前端菜单未显示就认为授权完成。

OpenAPI 客户端必须在后端契约稳定后使用仓库现有生成流程刷新，禁止手写 client service 与 routeTree.gen.ts；生成文件变化要单独检查 diff，避免覆盖此前公共目录路由。

## 4. 分步执行（TDD 顺序）

### Step 1：先写失败测试并建立可导入的测试边界

新增/修改：

- E:\AI_projects\yeyu-api\backend\tests\services\test_redaction.py
- E:\AI_projects\yeyu-api\backend\tests\api\routes\test_admin_authorization.py
- E:\AI_projects\yeyu-api\backend\tests\api\routes\test_health.py
- E:\AI_projects\yeyu-api\backend\tests\services\test_audit.py
- 必要时修改 E:\AI_projects\yeyu-api\backend\tests\conftest.py，只增加可复用的非敏感 fake/fixture，不改变现有数据清理语义。

必须先写出的失败断言包括：

    def test_sensitive_headers_are_redacted() -> None:
        safe = sanitize_headers({
            "Authorization": "Bearer <NON_SECRET_TOKEN>",
            "X-API-Key": "<NON_SECRET_API_KEY>",
            "X-Request-ID": "req-test-001",
        })
        assert safe["Authorization"] == "[REDACTED]"
        assert safe["X-API-Key"] == "[REDACTED]"
        assert safe["X-Request-ID"] == "req-test-001"


    def test_normal_user_cannot_read_admin_catalog_or_audit(
        client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        assert client.get(
            "/api/v1/admin/catalog", headers=normal_user_token_headers
        ).status_code == 403
        assert client.get(
            "/api/v1/admin/audit", headers=normal_user_token_headers
        ).status_code == 403


    def test_health_does_not_require_dependencies(client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


    def test_ready_hides_dependency_details(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        # fake checks return failure without exposing connection strings or exception text
        monkeypatch.setattr("app.api.routes.health.check_readiness", lambda: {
            "database": "failed", "redis": "ok", "migrations": "ok"
        })
        response = client.get("/ready")
        assert response.status_code == 503
        assert "postgresql" not in response.text.lower()
        assert "redis://" not in response.text.lower()

应用导入测试前先修正 E:\AI_projects\yeyu-api\backend\app\main.py 的静态目录挂载：只有 FRONTEND_DIR.is_dir() 时才挂载前端，避免本地未执行前端构建导致纯后端测试在 collection 阶段失败；这不改变生产构建存在时的挂载行为。

### Step 2：实现脱敏、审计模型和迁移

新增：

- E:\AI_projects\yeyu-api\backend\app\services\redaction.py
- E:\AI_projects\yeyu-api\backend\app\services\audit.py
- E:\AI_projects\yeyu-api\backend\app\alembic\versions\20261004_add_audit_events.py

修改：

- E:\AI_projects\yeyu-api\backend\app\models.py
- E:\AI_projects\yeyu-api\backend\tests\services\test_migrations.py（增加模型/迁移字段与 downgrade 安全检查）

先让 test_redaction.py、test_audit.py 通过，再运行 Alembic 离线 SQL 检查。20261004_add_audit_events.py 必须声明 down_revision = "20261003_add_usage_cache_tables"，创建 actor_id 的可空外键（ondelete=SET NULL）、request_id/action/object_type/outcome/created_at 查询索引和非空 details JSON；downgrade 在审计表有数据时必须 fail closed，不得静默删除真实审计记录。AuditService.record 的事务行为要有测试：脱敏后只 add 不 commit；敏感字段不出现在序列化 details；非法/过大的 metadata 被拒绝或截断；业务提交与审计写入同一事务；写入异常不打印 details。

### Step 3：实现根健康、就绪和结构化请求日志

新增/修改：

- E:\AI_projects\yeyu-api\backend\app\api\routes\health.py
- E:\AI_projects\yeyu-api\backend\app\api\routes\admin_health.py
- E:\AI_projects\yeyu-api\backend\app\core\readiness.py（或同等职责的单一模块）
- E:\AI_projects\yeyu-api\backend\app\middleware\request_logging.py（若目录不存在则创建）
- E:\AI_projects\yeyu-api\backend\app\main.py
- E:\AI_projects\yeyu-api\backend\app\api\main.py
- E:\AI_projects\yeyu-api\backend\app\api\routes\public_api.py

先用 fake DB/Redis/migration checker 让 test_health.py 通过，再补：

- /health 不触发 DB/Redis fake；
- /ready 任何一个依赖失败均 503；
- 在 E:\AI_projects\yeyu-api\backend\app\main.py 中先注册根级 health router，再按 FRONTEND_DIR.is_dir() 条件挂载前端 catch-all，确保静态首页不能遮蔽 /health 或 /ready；
- 日志字段固定且不含认证头、Cookie、query value、body、原始 IP；
- public_api 的成功、限流和上游失败都能写入 request state 的安全字段；
- 日志异常不改变 API 响应，但日志内容经过 RedactionService，不能用 repr(request) 或 repr(exception) 直接输出。

### Step 4：实现管理 API、审计接入和候选池

新增：

- E:\AI_projects\yeyu-api\backend\app\api\routes\admin_audit.py
- E:\AI_projects\yeyu-api\backend\app\schemas\admin.py（若现有 schema 无法表达分页/管理响应，则创建；避免把 ORM 模型直接作为不受控响应）

修改：

- E:\AI_projects\yeyu-api\backend\app\api\main.py
- E:\AI_projects\yeyu-api\backend\app\api\routes\admin_catalog.py
- E:\AI_projects\yeyu-api\backend\app\api\routes\admin_policies.py
- E:\AI_projects\yeyu-api\backend\app\api\routes\users.py
- 相关现有 schema/service/test 文件

实现顺序：

1. 加入 superuser-only 的 catalog list、audit list 和 admin health；固定分页上限，过滤值使用 allowlist。
2. 在创建/修改/删除用户、API 定义、策略的成功路径写审计；object_id 用 UUID/slug 等非敏感标识，metadata 只传字段名、状态、结果等安全摘要。
3. AuditService 只 add 不 commit；每个 mutation 的业务变更和 AuditEvent 共用一个 Session/事务，统一 commit/rollback；审计失败时 mutation 失败关闭，并有测试证明不会出现已提交 mutation 无审计的静默成功。
4. trial pool 只查询 status=trial 的 ApiDefinition，确认 provider ref 只能是内部标识；不得新增 URL 输入框或通用上游代理。
5. 加入 superuser-only 的 admin health 摘要；它只能复用固定 readiness check 结果，不得绕过检查或返回依赖细节。
6. 对 status、adapter_name、provider_ref、path 做固定 allowlist/格式测试，覆盖 trial + URL、未知 adapter、外部 host 和协议相对 URL；管理 API 响应不包含 hashed_password、key_hash、完整 API Key、OAuth 身份 token 或凭据配置值。

### Step 5：实现前端管理页面并刷新生成客户端

新增/修改：

- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-apis.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-policies.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-trial-pool.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-audit.tsx
- E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-health.tsx
- E:\AI_projects\yeyu-api\frontend\src\components\Admin\ 下必要的可复用表格/编辑组件
- E:\AI_projects\yeyu-api\frontend\src\components\Sidebar\AppSidebar.tsx
- E:\AI_projects\yeyu-api\frontend\tests\admin-isolation.spec.ts

先用 API contract fixtures 写组件/权限测试，再使用当前官方 OpenAPI 生成流程刷新 frontend\src\client\。以文件路由生成器刷新 frontend\src\routeTree.gen.ts，检查 diff 只包含预期路由；不直接编辑生成文件。

前端 E2E 最低覆盖：

- 未登录访问 /admin* 被导向登录/公开页；
- 普通登录用户直接打开 /admin-apis、/admin-policies、/admin-trial-pool、/admin-audit 时不能看到管理数据；
- 普通登录用户直接打开 /admin-health 时不能看到健康摘要；
- API Key 请求、未验证/非活动会话访问所有 /api/v1/admin/* 均被后端拒绝；
- superuser 可以看到页面，但 provider ref 只显示内部名称，不能显示任何 Secret；
- UI 不以隐藏菜单代替后端权限。

### Step 6：验证、独立审查、修复和提交

按以下顺序真实执行，逐项记录命令、退出码、摘要和未验证原因：

    conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_redaction.py E:\AI_projects\yeyu-api\backend\tests\services\test_audit.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_health.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_admin_authorization.py -q
    conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app E:\AI_projects\yeyu-api\backend\tests
    pnpm --dir E:\AI_projects\yeyu-api\frontend exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json
    pnpm --dir E:\AI_projects\yeyu-api\frontend exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
    git -C E:\AI_projects\yeyu-api diff --check

如环境具备 PostgreSQL/Redis，再执行迁移和集成测试；若前端 SWC/native cache、数据库、Redis 或浏览器端口阻塞，保留完整错误证据，不把静态检查通过描述为线上验收。

完成实现后启动一次独立只读审查，审查范围包括：权限绕过、固定 adapter/provider 与 SSRF 边界、审计事务一致性、日志/响应 Secret 泄露、健康检查信息泄露、迁移 downgrade 数据安全、前端生成路由和普通用户隔离。计划审查报告位于 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-plan-review.md；实现审查报告必须写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-review.md，明确 Critical/Important/Minor 和 Approved/Needs changes。发现 Critical/Important 时先写修复计划、修复后重新审查，不能直接提交。

每个重大阶段分别提交清晰 commit，建议：

- feat: add redaction and audit events
- feat: add health readiness and safe request logs
- feat: add admin catalog audit and trial pool
- feat: add admin management views
- docs: record task 7 verification and review

每次提交前确认：

    git -C E:\AI_projects\yeyu-api status --short
    git -C E:\AI_projects\yeyu-api diff --check
    git -C E:\AI_projects\yeyu-api diff --name-only

提交后只推送已确认的 origin/main；不得凭空创建或推送未知远程。

## 5. 明确不在本阶段完成的事项

- 不执行正式服务器 preflight、SSH、Docker Compose 生产部署、Nginx/DNS/证书变更。
- 不配置或申请 SMTP、GitHub OAuth、上游 API Key，不替用户接受第三方服务协议。
- 不把候选试验池中的第三方接口自动公开；实际上游适配器和服务条款评估继续按独立调研任务执行。
- 不宣称已完成线上注册、OAuth、真实邮件、域名 HTTPS、限流或原有网站无影响验收。
