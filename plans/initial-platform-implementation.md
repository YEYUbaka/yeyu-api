# Yeyu API 首期平台实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` or `executing-plans` to implement this plan task-by-task. Each step uses checkbox syntax and ends with an independently verifiable result.

**Goal:** 在官方 Full Stack FastAPI Template 基础上，交付一个可本地验证、可审计、可回滚的 Yeyu API 首期平台：账号体系、API 目录、独立 API Key、限流/额度、受控接口执行、缓存降级、A+B 首页、管理端和部署验收资料。

**Architecture:** 采用模块化 FastAPI 单体，沿用官方模板的 React/Vite/TypeScript、SQLModel/PostgreSQL、JWT、邮件、Playwright 和基础管理面板；新增 Redis 负责短期缓存、分钟/IP/并发限流，PostgreSQL 保存权威业务数据、每日用量和审计元数据。浏览器管理登录与 `/v1/*` API Key 调用严格分离，第三方上游只允许固定适配器和 allowlist。

**Tech Stack:** FastAPI Template（固定 commit）、Python `>=3.14,<4.0`、独立 conda 环境 `yeyu-api`、SQLModel/PostgreSQL、Redis、React 19/Vite/TypeScript、Tailwind/shadcn/ui、pnpm、Authlib、pytest、Playwright、Docker Compose、宿主机 Nginx。

## Global Constraints

- 项目根目录固定为 `E:\AI_projects\yeyu-api`；正式域名为 `https://api.yeyubaka.top`。
- 严禁修改 `E:\AI_projects\yeyubakahome_Web`、已有 `new.api.yeyubaka.top` 及其他现有服务；旧项目只允许只读检查。
- 不覆盖 `/www/wwwroot/yeyubaka.top`；生产部署必须使用独立目录、Compose 项目、数据库、缓存、日志和 Nginx vhost。
- 所有本地文件操作使用带盘符和反斜杠的完整 Windows 绝对路径；文本修改使用 `apply_patch`。
- 所有计划文件写入 `E:\AI_projects\yeyu-api\plans\`；本计划文件路径为 `E:\AI_projects\yeyu-api\plans\initial-platform-implementation.md`。
- Python 使用 conda 环境 `yeyu-api`，禁止 conda base 和 Windows Store Python；前端依赖使用 pnpm。
- 仓库只保留 `.env.example`；SMTP、GitHub OAuth、数据库、Redis、上游凭据和私钥只能进入环境变量或服务器 Secret 文件。
- API Key 只存不可逆哈希和公开前缀，完整值只显示一次；日志和请求记录不保存明文 Key、密码、OAuth token 或敏感正文。
- `/v1/*` 只接受独立 API Key，不把浏览器 Cookie 当作调用凭据；禁止任意 URL、开放代理、SSRF、端口扫描和未授权内容搬运。
- 默认策略为每日 1000 次、每分钟 60 次，但所有额度、权重、IP/并发限制必须可由管理端配置。
- 第三方免费服务未完成来源、条款、额度、再分发许可、署名、稳定性、缓存和隐私审查前，只进入试验池，不得公开包装。
- 健康检查、构建或静态测试通过不等于产品验收通过；外部凭据或线上条件缺失时标为阻塞/未验证。
- 每个任务结束都必须运行其验证命令并创建清晰 Git 提交；没有确认远程地址时不推送。

## Review resolutions and execution gates

以下闸门吸收了只读子代理对本计划的审查结果；它们优先于后续 Task 中较早的简写示例。设计方向和模板改造方向已经由用户确认，若设计文档再次变化，必须暂停实现并重新核对本计划。

- **模板与依赖可复现：** Task 1 必须按已解析的 $templateRef 检出，不得以浮动分支作为导入依据；保留模板随附的 uv.lock 作为上游来源证据，并从同一 SHA 生成并提交 E:\AI_projects\yeyu-api\backend\requirements-runtime.lock.txt 和 E:\AI_projects\yeyu-api\backend\requirements-dev.lock.txt。conda 环境仍是唯一运行环境，安装使用这些带 hash 的锁文件；若导出结果缺少 hash，任务失败而不是退回无版本约束的 pip install。记录 node --version、pnpm --version，在 E:\AI_projects\yeyu-api\frontend\package.json 固定 packageManager，后续安装统一使用 pnpm install --frozen-lockfile。
- **本地集成栈：** Compose project name 固定为 yeyu-api，服务名固定为 postgres、redis、mailpit、backend、frontend，并为依赖服务提供 healthcheck。集成测试前按顺序执行 docker compose ... up -d --wait postgres redis mailpit、conda run -n yeyu-api alembic upgrade head、测试数据初始化；Playwright 通过配置的 webServer 启动 backend/frontend 并在结束后清理。当前机器没有 Docker 时只报告 blocked，不安装 Docker 或修改服务器。
- **路由与 OpenAPI：** 每个新增 FastAPI router 必须在 E:\AI_projects\yeyu-api\backend\app\api\main.py 注册；每个后端 schema/路由 Task 结束都重新生成 E:\AI_projects\yeyu-api\frontend\src\client\，并运行 E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py，断言 /api/catalog、/v1/*、/health、/ready 和 API Key security scheme 存在。
- **GitHub OAuth 状态机：** state 使用随机 nonce、Redis 保存、10 分钟 TTL、严格单次消费；授权码流程使用 PKCE S256，callback URI 只接受配置中的精确值；管理会话 Cookie 使用 HttpOnly、Secure、SameSite=Lax，绑定动作要求当前登录、重新认证和 GitHub 已验证邮箱。provider/subject 唯一，禁止把两个已有账号自动合并；OAuth access token 交换后只用于当前请求，不落库、不写日志。
- **API Key 调试：** 列表、轮换历史和任何管理接口都不返回旧 secret；在线调试只能使用刚创建时内存中的 secret，或由用户再次粘贴 secret，关闭页面后清空。不得新增“查询完整 Key”接口；E2E 必须验证实际 X-API-Key 请求头、Cookie 不能替代 API Key，以及刷新后 secret 不可恢复。
- **额度与并发：** PolicyService 必须返回可释放的 QuotaLease；并发槽使用带 TTL 的 Redis 原子 acquire/release，并在 finally 释放；每日额度使用带条件的 PostgreSQL 更新，跨日按 UTC 计算。策略通过后即计入一次调用权重，策略拒绝不计入；上游失败不退回额度，但必须记录错误类别和 stale 结果。
- **试验池强制闸门：** 试验池必须有 TrialRecord 数据模型、证据状态、管理员审批路由和数据库约束；公开 registry 只接受数据库状态为 approved 且 adapter 在 allowlist 内的记录。E:\AI_projects\yeyu-api\docs\candidate-api-trial-pool.md 只能保存来源、条款和 Secret 引用名，严禁写实际账号、Key 或 Token。
- **SSRF 与资源限制：** allowlist 校验既要在 DNS 解析时执行，也要在实际连接前执行；默认禁用重定向，若业务需要则逐跳重新校验；覆盖 IPv4/IPv6 私网、环回、链路本地、云元数据、DNS rebinding、IDN/编码绕过。请求体和上游响应都必须流式限制大小，连接池、总超时、重试次数和并发槽有硬上限。
- **UI 验收：** Playwright 至少包含 Chromium desktop 和移动 viewport 两个 project，使用独立 storage state 和固定 seed；必须覆盖 A「索引台」搜索/分类/Quick Start、B「开发者仪表盘」Key/调试/额度，以及真实 method/path/auth/limits/cache 字段，不以静态截图或虚假统计代替。
- **数据库回滚：** 发布使用 expand/contract 迁移；迁移前有备份和恢复演练，旧应用必须能兼容 expand 阶段 schema。回滚脚本默认只回滚应用版本，不自动 downgrade 或删除数据库；数据库恢复必须是单独、经确认的操作。
- **迁移验证：** 每个新增 Alembic migration Task 都必须在隔离 PostgreSQL 上执行 upgrade head、downgrade -1、upgrade head，并验证空库和已有模板库；任何 downgrade 失败都不能标记 Task 完成。
- **文件保护：** 后续 Task 中所有 git add --all 简写均视为废弃；执行者必须先运行完整绝对路径的 git status，只对该 Task 的明确文件逐个 git add --，发现无关改动立即停止并报告。

## Scope and release gates

本计划覆盖首期可上线 MVP，但按独立可验收子系统拆分。先完成基础和身份，再完成 Key/策略，再完成执行器/缓存，再完成 UI/管理端，最后才准备部署。生产 DNS、Nginx、证书、服务器账号和权限变更不在默认执行授权内，必须在 Task 9 前另行说明影响、验证和回滚并等待确认。

内容接口是明确的发布闸门：Task 5 先交付适配器协议、缓存/降级和测试替身；只有候选接口试验记录达到“可公开”状态，才启用第一个真实内容适配器。计划不把任何第三方“免费”默认当作可再分发许可。

## File map

模板导入后，以下文件按职责维护；生成客户端文件不手工编辑。

- `E:\AI_projects\yeyu-api\backend\app\models.py`：SQLModel 业务实体和公共字段。
- `E:\AI_projects\yeyu-api\backend\app\schemas\`：请求/响应 DTO；新增域按文件拆分。
- `E:\AI_projects\yeyu-api\backend\app\api\routes\`：账号、目录、Key、公共调用、管理、健康路由。
- `E:\AI_projects\yeyu-api\backend\app\services\identity.py`：邮箱验证、管理登录上下文和账号合并规则。
- `E:\AI_projects\yeyu-api\backend\app\services\github_oauth.py`：Authlib GitHub 授权码流程和身份绑定。
- `E:\AI_projects\yeyu-api\backend\app\services\api_keys.py`：随机 Key、pepper 哈希、撤销和轮换。
- `E:\AI_projects\yeyu-api\backend\app\services\policy.py`：Key/账号/IP/接口权重策略和每日用量。
- `E:\AI_projects\yeyu-api\backend\app\services\quota.py`：Redis 并发租约、原子 acquire/release 和失败清理。
- `E:\AI_projects\yeyu-api\backend\app\services\trial_pool.py`：候选接口证据、审批状态和公开注册闸门。
- `E:\AI_projects\yeyu-api\backend\app\services\cache.py`：参数指纹、缓存元数据和 stale fallback。
- `E:\AI_projects\yeyu-api\backend\app\services\execution\`：执行上下文、统一响应、适配器注册和超时控制。
- `E:\AI_projects\yeyu-api\backend\app\services\execution\adapters\`：明确的自营工具和已批准内容适配器。
- `E:\AI_projects\yeyu-api\backend\app\core\config.py`：环境变量和 Secret 引用，不写 Secret 值。
- `E:\AI_projects\yeyu-api\backend\app\core\security.py`：密码、管理 Token、API Key 认证依赖和脱敏工具。
- `E:\AI_projects\yeyu-api\backend\app\alembic\versions\`：每个数据变更独立迁移。
- `E:\AI_projects\yeyu-api\backend\tests\`：后端单元、API、数据库和 Redis 集成测试。
- `E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py`：路由注册、鉴权 scheme 和健康端点契约。
- `E:\AI_projects\yeyu-api\frontend\src\routes\`：首页、目录、详情、用户中心和管理路由。
- `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\`：搜索、分类、卡片、状态和 Quick Start。
- `E:\AI_projects\yeyu-api\frontend\src\components\ApiKeys\`：创建、一次性显示、撤销和轮换交互。
- `E:\AI_projects\yeyu-api\frontend\src\components\Admin\`：沿用模板管理组件并扩展接口/策略/试验池页面。
- `E:\AI_projects\yeyu-api\frontend\src\client\`：OpenAPI 生成结果，只能由生成命令更新。
- `E:\AI_projects\yeyu-api\frontend\tests\`：Playwright 登录、目录、Key、调试和管理员隔离。
- `E:\AI_projects\yeyu-api\frontend\playwright.config.ts`：desktop/mobile project、webServer、storage state 和测试清理。
- `E:\AI_projects\yeyu-api\deploy\`：生产 Compose、Nginx 示例、只读 preflight、发布/回滚脚本。
- `E:\AI_projects\yeyu-api\docs\candidate-api-trial-pool.md`：第三方候选证据表和发布状态。
- `E:\AI_projects\yeyu-api\docs\release-checklist.md`：本地、部署和线上验收边界。

---

### Task 1: 导入并固定官方模板，建立本地开发基线

**Files:**
- Create: `E:\AI_projects\yeyu-api\backend\`、`E:\AI_projects\yeyu-api\frontend\`、`E:\AI_projects\yeyu-api\compose.yml`、`E:\AI_projects\yeyu-api\compose.override.yml`、`E:\AI_projects\yeyu-api\backend\pyproject.toml`、`E:\AI_projects\yeyu-api\frontend\package.json` 等官方模板文件。
- Modify: `E:\AI_projects\yeyu-api\.gitignore`、`E:\AI_projects\yeyu-api\README.md`、`E:\AI_projects\yeyu-api\frontend\package.json`。
- Create: `E:\AI_projects\yeyu-api\docs\framework-baseline.md`、`E:\AI_projects\yeyu-api\.env.example`、`E:\AI_projects\yeyu-api\frontend\pnpm-lock.yaml`、`E:\AI_projects\yeyu-api\frontend\.node-version`、`E:\AI_projects\yeyu-api\backend\requirements-runtime.lock.txt`、`E:\AI_projects\yeyu-api\backend\requirements-dev.lock.txt`。
- Test: `E:\AI_projects\yeyu-api\backend\tests\conftest.py`、`E:\AI_projects\yeyu-api\frontend\tests\config.ts`（沿用模板并只改路径/命令）。

**Interfaces:**
- Produces: 一个记录了模板仓库 URL、准确 commit SHA、MIT 许可证、Python 约束和 pnpm 迁移差异的基线文档。
- Produces: `conda run -n yeyu-api python`、`conda run -n yeyu-api pytest`、`pnpm run build` 和 `pnpm exec playwright test` 的可重复入口。

- [ ] **Step 1: 读取模板引用并固定 SHA**

```powershell
$templateUrl = 'https://github.com/fastapi/full-stack-fastapi-template.git'
$templateRef = (git ls-remote $templateUrl 'refs/heads/master' | ForEach-Object { ($_ -split '\s+')[0] })
if ([string]::IsNullOrWhiteSpace($templateRef)) { throw 'template ref unavailable' }
$templateRef
```

Expected: 输出一个 40 位 commit SHA；不把浮动的 `master` 直接写入项目配置。

- [ ] **Step 2: 在项目外创建只读模板暂存目录并核对清单**

```powershell
$staging = 'E:\AI_projects\yeyu-api-template-staging'
$templateUrl = 'https://github.com/fastapi/full-stack-fastapi-template.git'
$templateRef = (git ls-remote $templateUrl 'refs/heads/master' | ForEach-Object { ($_ -split '\s+')[0] })
if ([string]::IsNullOrWhiteSpace($templateRef)) { throw 'template ref unavailable' }
if (Test-Path -LiteralPath $staging) { throw "staging directory already exists: $staging" }
git clone --depth 1 'https://github.com/fastapi/full-stack-fastapi-template.git' $staging
$checkoutResult = git -C $staging checkout --detach $templateRef 2>&1
if ($LASTEXITCODE -ne 0) { throw "template SHA checkout failed: $checkoutResult" }
$stagingRef = git -C $staging rev-parse HEAD
if ($stagingRef -ne $templateRef) { throw "template changed during clone: expected $templateRef, got $stagingRef" }
$stagingRef
Get-ChildItem -Force -LiteralPath $staging | Select-Object Name
```

Expected: 暂存仓库 HEAD 等于 Step 1 的 SHA；暂存目录不在项目根目录内，且不包含用户 Secret。

- [ ] **Step 3: 写失败的基线检查**

在 `E:\AI_projects\yeyu-api\docs\framework-baseline.md` 记录以下必须成立的清单：模板 commit SHA、`backend\pyproject.toml` 的 `requires-python`、模板自带的 `compose.yml`/`backend`/`frontend`/`backend\tests` 路径、MIT 许可证和本项目不复用模板示例 `Item` 的说明。

- [ ] **Step 4: 导入模板文件但保留项目文档和规则**

只复制模板代码/配置清单到 `E:\AI_projects\yeyu-api`，不复制模板 `.git`、真实 `.env`、`bun.lock` 和模板的临时构建目录；保留现有 `AGENTS.md`、`docs\2026-09-30-yeyu-api-platform-design.md`、`plans\` 和项目 `.gitignore`，再把模板忽略项逐项合并。

- [ ] **Step 5: 创建独立 conda 环境并安装后端开发依赖**

```powershell
conda create -n yeyu-api python=3.14 -y
conda run -n yeyu-api python -m pip install --upgrade pip
conda run -n yeyu-api python -m pip install uv
conda run -n yeyu-api uv export --project 'E:\AI_projects\yeyu-api\backend' --locked --format requirements.txt --no-dev --output-file 'E:\AI_projects\yeyu-api\backend\requirements-runtime.lock.txt'
conda run -n yeyu-api uv export --project 'E:\AI_projects\yeyu-api\backend' --locked --format requirements.txt --all-groups --output-file 'E:\AI_projects\yeyu-api\backend\requirements-dev.lock.txt'
conda run -n yeyu-api python -m pip install --no-deps --editable 'E:\AI_projects\yeyu-api\backend'
conda run -n yeyu-api python -m pip install --require-hashes --requirement 'E:\AI_projects\yeyu-api\backend\requirements-runtime.lock.txt'
conda run -n yeyu-api python -m pip install --require-hashes --requirement 'E:\AI_projects\yeyu-api\backend\requirements-dev.lock.txt'
conda run -n yeyu-api python --version
conda run -n yeyu-api uv --version
```

Expected: Python 版本满足模板的 `>=3.14,<4.0`；命令没有使用 base 或 `WindowsApps\python.exe`。

- [ ] **Step 6: 把前端脚本从 Bun 入口迁移为 pnpm 入口**

将 `frontend\package.json` 中的 `bunx playwright` 改为 `pnpm exec playwright`，并使用 apply_patch 把 `packageManager` 固定为 `pnpm@10.28.2`、创建 `frontend\.node-version`（内容为 `24.18.0`），再运行以下命令生成并提交 pnpm 锁文件：

```powershell
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' install
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' run build
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' exec playwright --version
```

Expected: 生成 `frontend\pnpm-lock.yaml`，`build` 退出码为 0，脚本不再依赖 Bun。

- [ ] **Step 7: 运行基线测试**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests' -q
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' run build
docker compose -f 'E:\AI_projects\yeyu-api\compose.yml' config
```

Expected: 后端和前端基线通过；本机若无 Docker，只记录 `docker compose` 为未验证，不安装 Docker Desktop、不影响现有服务器。

- [ ] **Step 8: 提交**

```powershell
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "build: adopt FastAPI template baseline"
```

---

### Task 2: 邮箱验证、密码流程和 GitHub 身份绑定

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\models.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\login.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\users.py`、`E:\AI_projects\yeyu-api\backend\app\core\config.py`、`E:\AI_projects\yeyu-api\backend\app\core\security.py`、`E:\AI_projects\yeyu-api\backend\app\utils.py`。
- Create: `E:\AI_projects\yeyu-api\backend\app\services\identity.py`、`E:\AI_projects\yeyu-api\backend\app\services\github_oauth.py`、`E:\AI_projects\yeyu-api\backend\app\schemas\identity.py`、`E:\AI_projects\yeyu-api\backend\app\alembic\versions\20260930_add_identity_tables.py`。
- Create: `E:\AI_projects\yeyu-api\packages\react-email\emails\verify_email.tsx`；Generate: `E:\AI_projects\yeyu-api\backend\app\email-templates\verify_email.html`，沿用模板的 React Email 导出链路，不直接把生成 HTML 当作唯一源文件。
- Test: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_identity.py`、`E:\AI_projects\yeyu-api\backend\tests\services\test_identity.py`。

**Interfaces:**
- `EmailVerificationService.request(user_id: UUID) -> None`：生成一次性 token 哈希、写入过期时间并发送邮件；不存在用户时使用相同响应语义。
- `EmailVerificationService.verify(raw_token: str) -> User`：原子消费未过期 token，重复/过期/错误 token 统一失败。
- `GitHubOAuthService.start(request: Request) -> RedirectResponse` 和 `GitHubOAuthService.callback(request: Request) -> RedirectResponse`：只请求 `read:user user:email`，使用 PKCE S256；state 为随机 nonce，在 Redis 保存 10 分钟并严格单次消费；callback URI 必须精确匹配配置值，交换后读取身份并丢弃不需要的 OAuth access token。
- `IdentityService.link_github(user_id: UUID, provider_subject: str, email: str, email_verified: bool) -> OAuthIdentity`：已绑定到其他用户返回冲突；只有已验证匹配邮箱或当前已登录用户主动绑定才能合并。

- [ ] **Step 1: 写验证状态和 token 的失败测试**

```python
def test_verify_token_is_single_use(session, user_factory):
    user = user_factory(email_verified=False)
    raw_token = identity_service.issue_verification_token(session, user.id)
    assert identity_service.verify(raw_token).email_verified is True
    with pytest.raises(InvalidVerificationToken):
        identity_service.verify(raw_token)

def test_unknown_reset_email_has_non_enumerating_response(client):
    known = client.post('/api/auth/request-password-reset', json={'email': 'known@example.test'})
    unknown = client.post('/api/auth/request-password-reset', json={'email': 'unknown@example.test'})
    assert known.status_code == unknown.status_code == 202
    assert known.json()['message'] == unknown.json()['message']
```

- [ ] **Step 2: 运行失败测试**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_identity.py' -q
```

Expected: FAIL，失败原因是 `email_verified`、token service 或 OAuthIdentity 尚未存在。

- [ ] **Step 3: 添加模型、迁移和服务**

新增 `OAuthIdentity`、`EmailVerificationToken` 字段：provider subject 唯一约束、用户外键、token 哈希、过期时间、消费时间；token 表不保存原文。GitHub OAuth 使用 Authlib Starlette client，state nonce 由 Redis 保存并校验，Cookie 使用 HttpOnly、Secure、SameSite=Lax；主动绑定要求已登录并重新认证，禁止两个已有账号自动合并。邮件必须修改 `packages\react-email\emails\verify_email.tsx` 后执行模板现有导出命令，再校验生成的 HTML 已被 Mailpit 测试读取。

- [ ] **Step 4: 实现邮件验证、GitHub 登录和主动绑定**

邮箱注册后创建未验证用户；验证成功才允许 `/v1/*` API Key 创建和调用。GitHub 登录若匹配已验证邮箱，只在 GitHub email 标记为 verified 时自动关联；未满足条件时必须先登录既有账号再走“绑定 GitHub”。

- [ ] **Step 5: 运行身份测试和模板回归测试**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_identity.py' 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_login.py' 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_users.py' -q
```

Expected: 验证、重置、重复 token、账号冲突、GitHub callback state 错误均有明确结果；没有真实 SMTP/GitHub Secret 时只运行 Mailpit/mock 流程并标记 OAuth 线上验收未验证。

- [ ] **Step 6: 提交**

```powershell
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "feat: add verified account and GitHub identity flows"
```

---

### Task 3: API 目录、文档模型和搜索

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\models.py`、`E:\AI_projects\yeyu-api\backend\app\api\main.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\__init__.py`。
- Create: `E:\AI_projects\yeyu-api\backend\app\schemas\catalog.py`、`E:\AI_projects\yeyu-api\backend\app\services\catalog.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\catalog.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\admin_catalog.py`、`E:\AI_projects\yeyu-api\backend\app\alembic\versions\20261001_add_catalog_tables.py`。
- Test: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py`、`E:\AI_projects\yeyu-api\backend\tests\services\test_catalog.py`、`E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py`。
- Create: `E:\AI_projects\yeyu-api\docs\api-catalog-contract.md`。

**Interfaces:**
- `ApiCatalogService.search(query: str | None, category: str | None, status: str | None, page: int, page_size: int) -> CatalogPage`：只返回公开且已发布元数据。
- `ApiCatalogService.get_public(slug: str) -> ApiDetail`：返回请求方法、路径、鉴权、参数、响应、错误码、示例、状态、更新时间、来源和缓存规则。
- Public routes: `GET /api/catalog`, `GET /api/catalog/{slug}`；admin routes: `POST/PATCH/DELETE /api/admin/catalog/{slug}` 需要管理员依赖。
- `ApiDefinition` 不保存任意用户输入的上游 URL；只保存 `adapter_name`、状态和管理员维护的 provider 引用。

- [ ] **Step 1: 写搜索、分页、未发布隔离测试**

```python
def test_public_catalog_hides_draft_and_disabled(client, catalog_factory):
    catalog_factory(slug='uuid', visibility='public', status='healthy')
    catalog_factory(slug='draft-api', visibility='draft', status='trial')
    response = client.get('/api/catalog?query=api&page=1&page_size=20')
    assert response.status_code == 200
    assert [item['slug'] for item in response.json()['data']] == ['uuid']

def test_catalog_detail_contains_api_key_requirement(client, public_api_factory):
    response = client.get('/api/catalog/time')
    assert response.json()['auth']['type'] == 'api_key'
    assert response.json()['path'] == '/v1/tools/time'
```

- [ ] **Step 2: 运行失败测试并实现模型/服务/路由**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py' -q
```

Expected: 初次 FAIL；实现后 PASS，且公开目录不要求 API Key，调用接口本身仍要求 API Key。

- [ ] **Step 3: 注册路由、生成 OpenAPI 文档契约和前端客户端**

在 `backend\app\api\main.py` 显式注册 catalog/admin_catalog router；在 `docs\api-catalog-contract.md` 固定统一响应、分页和错误码；运行：

```powershell
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' run generate-client
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py' -q
git -C 'E:\AI_projects\yeyu-api' diff -- 'E:\AI_projects\yeyu-api\frontend\src\client'
```

Expected: `/api/catalog`、`/api/catalog/{slug}` 和 admin 路由出现在 OpenAPI；生成客户端只反映公开 schema，未手工编辑生成文件。

- [ ] **Step 4: 运行后端全量回归并提交**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests' -q
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "feat: add API catalog and documentation contract"
```

---

### Task 4: API Key 生命周期、独立鉴权和策略模型

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\models.py`、`E:\AI_projects\yeyu-api\backend\app\api\deps.py`、`E:\AI_projects\yeyu-api\backend\app\api\main.py`、`E:\AI_projects\yeyu-api\backend\app\core\security.py`、`E:\AI_projects\yeyu-api\backend\app\core\config.py`。
- Create: `E:\AI_projects\yeyu-api\backend\app\schemas\api_keys.py`、`E:\AI_projects\yeyu-api\backend\app\schemas\policy.py`、`E:\AI_projects\yeyu-api\backend\app\services\api_keys.py`、`E:\AI_projects\yeyu-api\backend\app\services\policy.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\api_keys.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\admin_policies.py`、`E:\AI_projects\yeyu-api\backend\app\alembic\versions\20261002_add_key_policy_tables.py`。
- Test: `E:\AI_projects\yeyu-api\backend\tests\services\test_api_keys.py`、`E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_keys.py`、`E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_auth_boundary.py`、`E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py`。

**Interfaces:**
- `ApiKeyService.create(user_id: UUID, label: str | None) -> CreatedApiKey`：返回 `{id, prefix, secret, created_at}`，secret 只进入该响应对象一次。
- `ApiKeyService.authenticate(raw_key: str) -> ApiKeyPrincipal | None`：使用带版本的 `HMAC-SHA256(server_pepper, raw_key)` 查询 hash，不把 raw key 写日志；pepper 只来自持久化 Secret 引用，支持明确的版本迁移。
- `ApiKeyService.revoke(key_id: UUID, user_id: UUID) -> None` 和 `rotate(key_id: UUID, user_id: UUID) -> CreatedApiKey`：轮换先撤销旧 Key，再创建新 Key。
- `get_api_key_principal(request: Request) -> ApiKeyPrincipal`：只读 `X-API-Key`，不读取管理 Cookie。
- `PolicyService.evaluate(principal: ApiKeyPrincipal, api: ApiDefinition, ip: IPvAnyAddress, now: datetime) -> PolicyDecision`：仅在账号已验证、未封禁、Key 未撤销时执行；Key 生成使用至少 256 位 CSPRNG，轮换失败时旧 Key 保持有效，审计只记录 prefix/id。

- [ ] **Step 1: 写 Key 一次显示、撤销、轮换和 Cookie 隔离测试**

```python
def test_created_secret_is_not_returned_by_list(authenticated_client, verified_user):
    created = authenticated_client.post('/api/keys', json={'label': 'local'}).json()['data']
    listed = authenticated_client.get('/api/keys').json()['data']
    assert 'secret' in created
    assert all('secret' not in item for item in listed)

def test_revoked_key_and_management_cookie_cannot_call_v1(authenticated_client, api_key, management_cookie):
    authenticated_client.post(f"/api/keys/{api_key.id}/revoke", cookies=management_cookie)
    assert authenticated_client.get('/v1/tools/uuid', headers={'X-API-Key': api_key.secret}).status_code == 401
    assert authenticated_client.get('/v1/tools/uuid', cookies=management_cookie).status_code == 401
```

- [ ] **Step 2: 运行失败测试并实现哈希/生命周期**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\services\test_api_keys.py' 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_keys.py' -q
```

Expected: 初次 FAIL；实现后 PASS，数据库只出现 prefix/hash，应用日志不出现完整 secret。

- [ ] **Step 3: 实现统一 API Key 依赖和错误结构**

固定错误结构：

```json
{
  "error": {
    "code": "API_KEY_REVOKED",
    "message": "API key is revoked",
    "request_id": "server-generated-id"
  }
}
```

错误码至少覆盖 `API_KEY_REQUIRED`、`API_KEY_INVALID`、`API_KEY_REVOKED`、`ACCOUNT_UNVERIFIED`、`ACCOUNT_SUSPENDED`、`RATE_LIMITED`、`DAILY_QUOTA_EXCEEDED`。

- [ ] **Step 4: 运行 Key/认证边界测试并提交**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_auth_boundary.py' -q
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "feat: add API key lifecycle and auth boundary"
```

---

### Task 5: Redis 限流、每日额度、执行器和缓存降级

**Files:**
- Modify: `E:\AI_projects\yeyu-api\compose.yml`、`E:\AI_projects\yeyu-api\compose.override.yml`、`E:\AI_projects\yeyu-api\backend\app\api\main.py`、`E:\AI_projects\yeyu-api\backend\app\core\config.py`。
- Create: `E:\AI_projects\yeyu-api\backend\app\services\redis.py`、`E:\AI_projects\yeyu-api\backend\app\services\quota.py`、`E:\AI_projects\yeyu-api\backend\app\services\cache.py`、`E:\AI_projects\yeyu-api\backend\app\services\trial_pool.py`、`E:\AI_projects\yeyu-api\backend\app\services\execution\models.py`、`E:\AI_projects\yeyu-api\backend\app\services\execution\registry.py`、`E:\AI_projects\yeyu-api\backend\app\services\execution\runner.py`、`E:\AI_projects\yeyu-api\backend\app\services\execution\adapters\tools.py`、`E:\AI_projects\yeyu-api\backend\app\services\execution\adapters\content.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\public_api.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\admin_trial_pool.py`、`E:\AI_projects\yeyu-api\backend\app\alembic\versions\20261003_add_usage_cache_tables.py`、`E:\AI_projects\yeyu-api\backend\app\alembic\versions\20261004_add_trial_pool_tables.py`。
- Create: `E:\AI_projects\yeyu-api\backend\tests\services\test_policy.py`、`E:\AI_projects\yeyu-api\backend\tests\services\test_cache.py`、`E:\AI_projects\yeyu-api\backend\tests\services\test_execution.py`、`E:\AI_projects\yeyu-api\backend\tests\services\test_trial_pool.py`、`E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py`、`E:\AI_projects\yeyu-api\backend\tests\api\routes\test_admin_trial_pool.py`。
- Create: `E:\AI_projects\yeyu-api\docs\candidate-api-trial-pool.md`（Task 8 只补充证据，不重复创建）。

**Interfaces:**
- `ApiAdapter.execute(context: ExecutionContext, params: Mapping[str, Any]) -> AdapterResult`；adapter 不接收用户任意 URL。
- `ExecutionContext` 包含 `request_id`、`api_slug`、`api_key_id`、`user_id`、`client_ip`、`timeout_ms` 和 `now`。
- `PolicyService.evaluate(...) -> PolicyDecision` 返回 `allowed`、`reason`、`retry_after_seconds`、`daily_remaining` 和 `minute_remaining`；`PolicyService.acquire(...) -> QuotaLease` 必须在 `finally` 释放并发槽。
- `CacheService.get(cache_key: str) -> CacheValue | None`、`set(...) -> None`、`stale_value(...) -> CacheValue | None`；响应元数据必须包含 `cache_hit`、`stale`、`stale_reason` 和 `data_at`，并受最大 stale age 限制。
- `TrialPoolService.approve(trial_id: UUID, actor_id: UUID) -> TrialRecord`：只有管理员能审批，registry 只接受 approved 且 allowlist 命中的记录，证据 Markdown 不参与运行时授权。
- `ApiRunner.run(slug: str, context: ExecutionContext, params: Mapping[str, Any]) -> ApiResponse`：统一成功、上游超时、无缓存、stale fallback 和参数错误。

- [ ] **Step 1: 写限流、额度、固定适配器和 stale 测试**

```python
def test_policy_blocks_second_request_when_minute_limit_is_one(redis, db, principal, api):
    now = datetime.now(timezone.utc)
    policy = PolicyService(redis=redis, session=db, minute_limit=1, daily_limit=1000)
    assert policy.evaluate(principal, api, ip_address('192.0.2.10'), now).allowed is True
    second = policy.evaluate(principal, api, ip_address('192.0.2.10'), now)
    assert second.allowed is False
    assert second.reason == 'MINUTE_LIMIT'

def test_stale_cache_is_explicit(cache):
    now = datetime.now(timezone.utc)
    expired_at = now - timedelta(hours=1)
    cache.seed('weather:city-a', data_at=expired_at, payload={'temperature': 20})
    value = cache.stale_value('weather:city-a', now=now)
    assert value is not None
    assert value.meta.stale is True
    assert value.meta.data_at < now

def test_adapter_registry_rejects_unknown_slug(registry):
    with pytest.raises(UnknownApiSlug):
        registry.get('user-supplied-url')
```

- [ ] **Step 2: 运行失败测试并接入 Redis/PostgreSQL**

```powershell
docker compose -p yeyu-api -f 'E:\AI_projects\yeyu-api\compose.yml' up -d --wait postgres redis mailpit
conda run -n yeyu-api alembic upgrade head
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\services\test_policy.py' 'E:\AI_projects\yeyu-api\backend\tests\services\test_cache.py' -q
```

Expected: 当前本机没有 Docker 时记录为未验证；在具备 Docker 的 CI/服务器环境中必须看到 Redis/PostgreSQL ready 后再运行测试。

- [ ] **Step 3: 实现 Redis 原子限流和 PostgreSQL 每日计数**

分钟/IP/并发计数使用 Redis 原子脚本，并设置到期时间；并发使用 `QuotaLease` 的 acquire/release 和崩溃 TTL；每日用量使用 PostgreSQL `usage_daily` 唯一键 `(utc_date, user_id, api_key_id, api_slug)` 的带条件更新；接口权重在同一事务内累加。任何一个限额拒绝都不执行上游，策略通过后即计费，上游失败不退回额度。

- [ ] **Step 4: 实现低风险工具适配器**

先实现 `time`、`uuid` 两个不依赖第三方的 adapter，并为随机字符串、Base64/URL 编解码保留同一协议。每个 adapter 固定参数 Schema、输出 Schema、最大响应大小和错误码。

- [ ] **Step 5: 实现内容适配器协议和试验池**

`content.py` 只实现 `AllowlistedHttpAdapter` 的安全边界、DNS/连接前目标复核、超时、有限重试、默认禁止重定向、响应大小限制和缓存/stale 流程；真实 provider 必须先建立 TrialRecord，补齐来源、条款、额度、再分发、署名、隐私和成本证据，由管理员批准且 adapter 在 allowlist 后才能注册到公开目录。Markdown 只作证据索引，不作授权来源。

- [ ] **Step 6: 实现公共调用路由和统一响应**

在 `backend\app\api\main.py` 注册 public_api 和 admin_trial_pool；将 `GET /v1/tools/time`、`GET /v1/tools/uuid` 接入 API Key、策略、执行器和审计元数据；上游内容接口只在 TrialRecord 满足发布条件后启用。成功响应包含 `request_id`、`data`、`meta`；失败响应使用 Task 4 的错误结构。

- [ ] **Step 7: 运行执行层测试并提交**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\services\test_execution.py' 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py' -q
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "feat: add guarded execution, quota and cache layers"
```

---

### Task 6: A+B 首页、目录详情、在线调试和用户中心

**Files:**
- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\_layout\index.tsx`、`E:\AI_projects\yeyu-api\frontend\src\routes\_layout.tsx`、`E:\AI_projects\yeyu-api\frontend\src\components\Sidebar\AppSidebar.tsx`、`E:\AI_projects\yeyu-api\frontend\src\index.css`。
- Create: `E:\AI_projects\yeyu-api\frontend\src\routes\_layout\catalog.tsx`、`E:\AI_projects\yeyu-api\frontend\src\routes\_layout\api-detail.tsx`、`E:\AI_projects\yeyu-api\frontend\src\routes\_layout\keys.tsx`、`E:\AI_projects\yeyu-api\frontend\src\routes\_layout\usage.tsx`、`E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\`、`E:\AI_projects\yeyu-api\frontend\src\components\ApiKeys\`、`E:\AI_projects\yeyu-api\frontend\src\components\DebugConsole\`。
- Modify: `E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts`、`E:\AI_projects\yeyu-api\frontend\tests\user-settings.spec.ts`。
- Create: `E:\AI_projects\yeyu-api\frontend\tests\api-catalog.spec.ts`、`E:\AI_projects\yeyu-api\frontend\tests\api-key-lifecycle.spec.ts`、`E:\AI_projects\yeyu-api\frontend\tests\debug-console.spec.ts`。

**Interfaces:**
- `ApiSearch` 使用生成客户端调用 `GET /api/catalog`，不在前端复制搜索规则。
- `QuickStartPanel` 接收 `ApiDetail`，只展示文档中声明的 method/path/auth/limits/cache，不拼接用户输入 URL。
- `ApiKeyRevealDialog` 只接受 `CreatedApiKey`，关闭后清空 secret state；列表只使用 `ApiKeySummary`。
- `DebugConsole` 只能对已加载的 `ApiDetail` 执行；secret 只接受创建成功后内存中的值或用户再次粘贴的值，未登录、无 Key 或刷新后丢失 secret 时显示明确阻塞原因。

- [ ] **Step 1: 写首页和用户中心 E2E 失败测试**

```typescript
test('homepage exposes search and quick start without fake metrics', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('textbox', { name: /搜索/ })).toBeVisible();
  await expect(page.getByText('时间戳与时区')).toBeVisible();
  await expect(page.getByText(/每日调用量|用户数|调用次数/)).toHaveCount(0);
});

test('API key secret is shown once and cannot be retrieved from list', async ({ page }) => {
  await page.goto('/keys');
  await page.getByRole('button', { name: '创建 API Key' }).click();
  await expect(page.getByText(/shown once|仅显示一次/)).toBeVisible();
  await page.getByRole('button', { name: /关闭|我已保存/ }).click();
  await expect(page.getByText(/yk_live_/)).toHaveCount(0);
});

test('mobile layout keeps search, quick start, and debug entry usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('textbox', { name: /搜索/ })).toBeVisible();
  await expect(page.getByText('时间戳与时区')).toBeVisible();
});
```

- [ ] **Step 2: 运行失败测试**

```powershell
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' exec playwright test 'E:\AI_projects\yeyu-api\frontend\tests\api-catalog.spec.ts' --project=chromium --project=mobile-chromium
```

Expected: 初次 FAIL，原因是新的 route/component 尚未存在。

- [ ] **Step 3: 实现 A+B 首页和目录**

A 的搜索/分类/状态作为主布局，B 的 Quick Start 作为首屏右侧或移动端紧随搜索区的面板；所有示例状态来自 API 元数据，不写死“正常”或延迟数字。

- [ ] **Step 4: 实现详情、在线调试和 Key 生命周期页面**

详情页渲染参数、响应、错误码、curl/JavaScript/Python 示例；调试页要求管理登录，并使用创建成功后仍在内存中的 secret 或用户再次粘贴的 secret，公共请求仍通过 `X-API-Key`；E2E 监听真实请求，断言存在 `X-API-Key` 且不能只靠 Cookie；列表和刷新页面都不能恢复旧 secret。

- [ ] **Step 5: 运行前端构建和 E2E，并提交**

```powershell
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' run build
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' exec playwright test 'E:\AI_projects\yeyu-api\frontend\tests\api-catalog.spec.ts' 'E:\AI_projects\yeyu-api\frontend\tests\api-key-lifecycle.spec.ts' 'E:\AI_projects\yeyu-api\frontend\tests\debug-console.spec.ts' --project=chromium --project=mobile-chromium
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "feat: add A+B catalog and developer console UI"
```

---

### Task 7: 管理端、健康检查、审计和日志脱敏

**Files:**
- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin.tsx`、`E:\AI_projects\yeyu-api\frontend\src\components\Admin\`、`E:\AI_projects\yeyu-api\backend\app\api\routes\users.py`。
- Create: `E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-apis.tsx`、`E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-policies.tsx`、`E:\AI_projects\yeyu-api\frontend\src\routes\_layout\admin-trial-pool.tsx`、`E:\AI_projects\yeyu-api\backend\app\api\routes\admin_users.py`、`E:\AI_projects\yeyu-api\backend\app\api\routes\admin_health.py`、`E:\AI_projects\yeyu-api\backend\app\services\audit.py`、`E:\AI_projects\yeyu-api\backend\app\services\redaction.py`。
- Test: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_admin_authorization.py`、`E:\AI_projects\yeyu-api\backend\tests\services\test_redaction.py`、`E:\AI_projects\yeyu-api\frontend\tests\admin-isolation.spec.ts`。

**Interfaces:**
- `AdminAuthorization.require_superuser(user: CurrentUser) -> User`：普通用户统一返回 403，不能通过路径参数或前端隐藏绕过。
- `AuditService.record(actor_id: UUID | None, action: str, object_type: str, object_id: str, outcome: str, metadata: Mapping[str, str]) -> None`：metadata 先脱敏再写入。
- `RedactionService.sanitize_headers(headers: Mapping[str, str]) -> dict[str, str]`：至少脱敏 `X-API-Key`、`Authorization`、Cookie、Set-Cookie、密码和 OAuth token。
- `GET /health` 只检查进程存活；`GET /ready` 检查 PostgreSQL、Redis 和迁移状态，不把 Secret 或连接串返回给客户端。

- [ ] **Step 1: 写管理员隔离、健康和脱敏失败测试**

```python
def test_normal_user_cannot_read_admin_catalog(normal_client):
    response = normal_client.get('/api/admin/catalog')
    assert response.status_code == 403

def test_redaction_removes_credentials():
    result = RedactionService.sanitize_headers({
        'X-API-Key': 'yk_live_secret-value',
        'Authorization': 'Bearer oauth-secret-value',
        'Content-Type': 'application/json',
    })
    assert result['X-API-Key'] == '[REDACTED]'
    assert result['Authorization'] == '[REDACTED]'
    assert result['Content-Type'] == 'application/json'
```

- [ ] **Step 2: 实现管理资源、试验池和健康路由**

管理端只能编辑元数据、策略和 provider 引用名称，不能回显完整 Secret；健康路由返回固定字段 `status`、`dependencies` 和 `version`，不返回环境变量。

- [ ] **Step 3: 实现脱敏日志和审计**

将请求 ID、接口 slug、状态码、耗时、缓存命中和错误类别写入结构化日志；请求正文默认不记录，IP 仅按隐私策略保存；管理员操作写入审计表。

- [ ] **Step 4: 运行测试、静态检查并提交**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\api\routes\test_admin_authorization.py' 'E:\AI_projects\yeyu-api\backend\tests\services\test_redaction.py' -q
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' exec playwright test 'E:\AI_projects\yeyu-api\frontend\tests\admin-isolation.spec.ts' --project=chromium
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "feat: add admin controls and redacted audit trail"
```

---

### Task 8: 安全测试、迁移回滚和发布前资料

**Files:**
- Create: `E:\AI_projects\yeyu-api\backend\tests\security\test_ssrf_guards.py`、`E:\AI_projects\yeyu-api\backend\tests\security\test_resource_limits.py`、`E:\AI_projects\yeyu-api\backend\tests\security\test_secret_logging.py`。
- Modify: `E:\AI_projects\yeyu-api\docs\candidate-api-trial-pool.md`（补充 Task 5 结构模板的证据，不保存任何实际账号、Key 或 Token）、`E:\AI_projects\yeyu-api\docs\release-checklist.md`、`E:\AI_projects\yeyu-api\docs\rollback-runbook.md`。
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\execution\adapters\content.py`、`E:\AI_projects\yeyu-api\backend\app\services\redaction.py`、`E:\AI_projects\yeyu-api\backend\app\core\config.py`。

**Interfaces:**
- `ProviderTargetValidator.validate(url: AnyHttpUrl, allowlist: ProviderAllowlist) -> NormalizedTarget`：拒绝非 HTTPS、用户名密码、私网/环回/链路本地/云元数据 IP、未允许 host 和未允许端口，并在 DNS 解析和实际连接前重复校验。
- `ResourceLimit.validate_request(body_size: int, json_depth: int, query_length: int, timeout_ms: int) -> None`：超限返回固定错误码。
- `ReleaseChecklist` 必须区分 `verified`、`blocked`、`not_verified`，不能用 readiness 代替线上产品验收。

- [ ] **Step 1: 写 SSRF、资源耗尽和日志泄露失败测试**

```python
@pytest.mark.parametrize('url', [
    'http://127.0.0.1:8000/admin',
    'http://169.254.169.254/latest/meta-data',
    'http://10.0.0.5/internal',
    'https://unapproved.example/data',
])
def test_provider_target_is_rejected(url, allowlist):
    with pytest.raises(ProviderTargetRejected):
        ProviderTargetValidator.validate(url, allowlist)

def test_secret_never_appears_in_structured_log(caplog):
    request_id = 'request-test-1'
    log_request(api_key='yk_live_secret-value', authorization='Bearer secret', request_id=request_id)
    assert 'yk_live_secret-value' not in caplog.text
    assert 'Bearer secret' not in caplog.text

@pytest.mark.parametrize('url', [
    'http://[::1]:8000/admin',
    'http://[fe80::1]/internal',
    'https://127.0.0.1.nip.io/data',
])
def test_private_ipv6_and_dns_rebinding_targets_are_rejected(url, allowlist):
    with pytest.raises(ProviderTargetRejected):
        ProviderTargetValidator.validate(url, allowlist)

def test_redirect_target_is_revalidated(http_client, allowlist):
    response = http_client.get('https://approved.example/data', follow_redirects=False)
    assert response.headers['location'].startswith('http://127.0.0.1')
    with pytest.raises(ProviderTargetRejected):
        fetch_allowlisted('https://approved.example/data', allowlist)
```

- [ ] **Step 2: 运行安全测试并修正真实失败**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests\security' -q
```

Expected: SSRF、任意重定向、超大请求、过深 JSON、无限重试和 Secret 日志泄露都有拒绝或脱敏证据。

- [ ] **Step 3: 编写候选接口试验池记录**

每条记录至少包含来源/官方文档、账号或 Key 的引用名（不写实际凭据）、额度、服务条款/再分发、署名、稳定性/延迟、返回格式、缓存、隐私/合规、成本、推荐动作和证据链接；没有许可证据的条目状态必须是 `trial` 或 `link_only`。

- [ ] **Step 4: 编写发布与回滚清单**

清单包含本地安装、迁移、构建、容器、DNS/HTTPS、邮箱、GitHub OAuth、Key 生命周期、限流/额度、工具接口、内容接口、stale fallback、管理隔离、日志脱敏和原有服务无影响；每项写明证据命令、预期结果和失败后的回滚动作。

- [ ] **Step 5: 运行全量检查并提交**

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests' -q
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' run build
conda run -n yeyu-api alembic upgrade head
conda run -n yeyu-api alembic downgrade -1
conda run -n yeyu-api alembic upgrade head
git -C 'E:\AI_projects\yeyu-api' diff --check
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "test: add security and release readiness checks"
```

---

### Task 9: 独立部署包和只读 preflight

**Files:**
- Create: `E:\AI_projects\yeyu-api\deploy\compose.production.yml`、`E:\AI_projects\yeyu-api\deploy\nginx\api.yeyubaka.top.conf.example`、`E:\AI_projects\yeyu-api\deploy\scripts\preflight.sh`、`E:\AI_projects\yeyu-api\deploy\scripts\deploy.sh`、`E:\AI_projects\yeyu-api\deploy\scripts\rollback.sh`、`E:\AI_projects\yeyu-api\deploy\README.md`。
- Modify: `E:\AI_projects\yeyu-api\docs\rollback-runbook.md`、`E:\AI_projects\yeyu-api\AGENTS.md`（仅补充已验证的部署命令和目录，不写 Secret）。

**Interfaces:**
- `preflight.sh` 只读检查 CPU、内存、磁盘、Docker/Compose、80/443/应用端口、现有 Nginx vhost、DNS、证书、独立部署目录和回滚空间，退出码非 0 时不允许 deploy。
- `deploy.sh release_dir` 只接受已构建版本目录，先校验目录解析路径在独立发布根目录内且不含 symlink/path traversal，使用最小权限发布账号，保留上一版本并在 `/health`、`/ready` 和 smoke endpoint 失败时自动停止切换。
- `rollback.sh release_id` 只切换到已保留且通过健康检查的上一版本，不删除数据库卷、不触碰其他 Compose 项目；数据库只允许 expand/contract 兼容迁移，默认不执行 downgrade，恢复数据库必须单独确认。

- [ ] **Step 1: 写部署脚本的 shell 单测/静态检查**

```powershell
rg -n --hidden --glob '*' 'rm -rf|docker compose down -v|/www/wwwroot/yeyubaka.top|new\.api\.yeyubaka\.top|curl.*X-API-Key|password=|secret=' 'E:\AI_projects\yeyu-api\deploy'
rg -n 'api\.yeyubaka\.top|proxy_pass|server_name' 'E:\AI_projects\yeyu-api\deploy\nginx\api.yeyubaka.top.conf.example'
docker compose -p yeyu-api -f 'E:\AI_projects\yeyu-api\deploy\compose.production.yml' config
```

Expected: 不出现删除数据库卷、覆盖个人网站、触碰既有 NewAPI 或硬编码 Secret 的命令；脚本使用显式路径和固定 Compose project name。

- [ ] **Step 2: 实现生产 Compose 和 Nginx 示例**

生产 Compose 只定义 Yeyu API、PostgreSQL、Redis 和必要的迁移/worker 服务；应用端口绑定到本机未占用的 loopback 端口，Nginx 示例只匹配 `api.yeyubaka.top`，不包含现有站点配置内容。

- [ ] **Step 3: 实现只读 preflight**

使用 SSH 只读命令收集资源、监听端口、Docker 项目、Nginx 文件名、DNS 和证书状态；不执行 `nginx -s reload`、DNS 更新、证书签发、容器重启或目录创建。

- [ ] **Step 4: 编写发布/回滚说明并运行本地静态检查**

```powershell
bash.exe 'E:\AI_projects\yeyu-api\deploy\scripts\preflight.sh' --help
docker compose -p yeyu-api -f 'E:\AI_projects\yeyu-api\deploy\compose.production.yml' config
git -C 'E:\AI_projects\yeyu-api' diff -- 'E:\AI_projects\yeyu-api\deploy'
git -C 'E:\AI_projects\yeyu-api' diff --check
```

本机没有 Docker 时明确记录 compose config 未验证；不因为缺少本地 Docker 而触碰服务器。

- [ ] **Step 5: 提交部署包**

```powershell
git -C 'E:\AI_projects\yeyu-api' status --short --branch
# 仅对本 Task Files/Test 列出的完整路径逐项执行 git -C 'E:\AI_projects\yeyu-api' add --；禁止暂存无关改动。
git -C 'E:\AI_projects\yeyu-api' commit -m "ops: add isolated deployment and rollback package"
```

---

## Final verification gate

在任何“首期完成”声明前，按以下顺序取得新鲜证据，并把结果写入 `E:\AI_projects\yeyu-api\docs\release-checklist.md`：

```powershell
conda run -n yeyu-api python -m pytest 'E:\AI_projects\yeyu-api\backend\tests' -q
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' run build
pnpm --dir 'E:\AI_projects\yeyu-api\frontend' exec playwright test --project=chromium --project=mobile-chromium
git -C 'E:\AI_projects\yeyu-api' diff --check
git -C 'E:\AI_projects\yeyu-api' status --short --branch
```

线上验收另需用户确认 DNS/Nginx/证书/服务器变更后执行，至少覆盖：DNS/HTTPS、桌面和移动端、邮箱验证、GitHub OAuth、Key 创建/调用/撤销/轮换、无效/撤销 Key、分钟限流、每日额度、工具接口、获批准的内容接口、缓存 stale、管理权限、健康检查、日志脱敏和原有服务无影响。

## Known external gates

- SMTP 凭据、GitHub OAuth Client ID/Secret、正式 DNS 控制权、证书发行权限和目标服务器最小权限发布账号均不是仓库内资产；缺失时只能验证本地 mock/测试流。
- 当前本机未安装 Docker；Task 1 和 Task 5 的 Compose 验证需要 CI 或目标服务器上的独立环境，不能把未执行写成通过。
- 第一个真实内容接口的公开资格取决于试验池证据，计划不预先授权任何第三方再分发。
