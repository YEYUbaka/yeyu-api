# Task 8：安全测试、迁移回滚与发布前资料实施计划

## 0. 状态与边界

- 状态：已通过独立计划复审，待实施。
- 项目根目录：`E:\AI_projects\yeyu-api`。
- 只修改本计划列出的安全测试、执行器必要修复、候选接口证据文档、发布清单和回滚手册。
- 不修改 `E:\AI_projects\yeyubakahome_Web`，不访问或修改 `new.api.yeyubaka.top`，不执行 DNS、Nginx、证书、服务器或生产凭据变更。
- 不注册真实内容 provider，不调用第三方公网，不替用户注册账号、接受协议或申请 API Key。
- 单元和安全回归测试只使用 fake resolver、fake HTTP client、fake response 和明确的非敏感占位值；迁移集成验证如具备条件，只能连接本 Task 独占、可销毁的临时 PostgreSQL，禁止连接开发共享库、已有业务库或生产库。未明确隔离库归属时不执行并记为 `not_verified`。

## 1. 目标与验收边界

1. 为现有 `AllowlistedHttpAdapter`、执行 runner、有限 JSON 边界、请求日志和 `RedactionService` 建立独立安全回归测试；优先复用已有实现，不新增平行 SSRF/代理抽象，也不复制现有单元测试。
2. 明确验证 provider target、DNS rebinding、私网/环回/云元数据、固定 host/port/path、重定向、请求/响应大小、超时/重试、runner worker slot、Redis/Policy concurrency lease 和错误 envelope 的拒绝行为；超时测试必须区分“HTTP 请求已返回”与“后台 adapter future 已完成”。
3. 明确验证日志、审计和公共错误响应不出现 API Key、Cookie、Authorization、密码、OAuth token、私钥、URL 或异常堆栈。
4. 为候选接口试验池补一份只含公开来源、官方文档、条款状态、额度与推荐动作的证据表；没有明确再分发许可的候选只能标记 `research_only` 或 `link_only`，不得进入公开 registry。
5. 编写发布验收清单和回滚手册，逐项区分 `verified`、`blocked`、`not_verified`，不把 `/health`、静态检查或构建结果冒充线上验收。
6. 迁移回滚只做本地/隔离环境验证设计；生产回滚默认只切换应用版本，不自动 downgrade 或删除数据库数据。

## 2. 现有实现复用边界

- SSRF/响应大小/重试逻辑以 `backend\app\services\execution\adapters\content.py` 现有 `AllowlistedHttpAdapter` 为被测对象。
- 通用有限 JSON 和公开错误 envelope 以 `backend\app\services\execution\models.py` 为被测对象；不另建第二套响应模型。
- 日志以 `backend\app\middleware\request_logging.py` 为被测对象；不读取请求 body、认证 header、完整 query 或原始 IP。
- 脱敏以 `backend\app\services\redaction.py` 为单一入口；测试应覆盖嵌套 mapping/list、大小限制和未知对象，不把异常对象 `repr` 写入日志。
- 迁移以当前 Alembic 链为准：`20261005_harden_catalog_boundaries` 是当前末端；Task 8 不创建不必要的业务迁移，但必须检查单 head、revision 链和现有 migration tests。

## 3. 文件范围

新增：

- `E:\AI_projects\yeyu-api\backend\tests\security\__init__.py`
- `E:\AI_projects\yeyu-api\backend\tests\security\test_ssrf_guards.py`
- `E:\AI_projects\yeyu-api\backend\tests\security\test_resource_limits.py`
- `E:\AI_projects\yeyu-api\backend\tests\security\test_secret_logging.py`
- `E:\AI_projects\yeyu-api\docs\candidate-api-trial-pool.md`
- `E:\AI_projects\yeyu-api\docs\release-checklist.md`
- `E:\AI_projects\yeyu-api\docs\rollback-runbook.md`

允许必要修复的现有文件：

- `E:\AI_projects\yeyu-api\backend\app\services\execution\runner.py`
- `E:\AI_projects\yeyu-api\backend\app\api\routes\public_api.py`
- `E:\AI_projects\yeyu-api\backend\app\services\policy.py`
- `E:\AI_projects\yeyu-api\backend\app\main.py`
- `E:\AI_projects\yeyu-api\backend\app\middleware\request_logging.py`
- `E:\AI_projects\yeyu-api\backend\app\services\audit.py`
- `E:\AI_projects\yeyu-api\backend\app\services\execution\adapters\content.py`
- `E:\AI_projects\yeyu-api\backend\app\services\execution\models.py`
- `E:\AI_projects\yeyu-api\backend\app\services\redaction.py`
- `E:\AI_projects\yeyu-api\backend\app\core\config.py`

若安全测试不证明实现缺陷，不修改上述生产文件；若发现缺陷，只做对应失败测试证明的最小修复，并更新同一威胁项的回归测试。

## 3.1 威胁项与既有测试复用矩阵

新增 `backend\tests\security\` 只承载跨组件攻击链和发布门禁，不复制已有单元测试：

| 威胁项 | 已有单元证据 | Task 8 新增缺口 |
| --- | --- | --- |
| SSRF、DNS、重定向、响应关闭/大小 | `test_execution.py` 的 http adapter、redirect、IPv6、response 用例 | 跨跳 pinned address tuple、redirect loop/最后一个 response 关闭、与发布状态的安全门禁 |
| 有限 JSON、runner worker slot、严格 envelope | `test_execution.py` 的 runner、cache、response 用例 | 真实 ASGI 路由错误响应与 header/body request ID 一致性 |
| 脱敏 | `test_redaction.py`、`test_audit.py` | middleware caplog、公共错误响应和审计/日志联合检查 |
| Redis/Policy concurrency lease | `test_policy.py`、`test_public_api.py` | timeout 后后台 future 未完成时，第二个同 key 请求仍不得绕过并发租约；若现状无法保证才修改 policy/public_api/runner |
| Alembic 链和 downgrade 保护 | `test_migrations.py` | 单 head、revision 链、命令证据和 PostgreSQL 未验证状态记录 |

## 4. TDD 执行顺序

### Step 1：先写失败的安全测试

`test_ssrf_guards.py` 只新增既有 `test_execution.py` 没有覆盖的跨组件/攻击链。协议、认证信息、allowlist、端口、地址分类、resolver fail-closed、pinned client、基础 redirect、响应关闭与大小上限由既有执行器单元测试提供证据；新文件只验证多跳 redirect 的连接地址联合生命周期、相对路径/fragment/重复或缺失 Location 的跨跳行为、达到 `MAX_REDIRECTS` 后最后一个 response 关闭，以及发布门禁需要的组合证据，不复制逐项单元矩阵。

`test_resource_limits.py` 只新增真实 ASGI/跨组件边界：

- query/parameter JSON 字节上限、嵌套深度、对象/数组项数、非有限数字、危险 target/path 参数；
- 固定 timeout、最大 retry、最大 redirect、runner worker admission 上限；并单独验证 Redis/Policy concurrency lease：adapter 超时但 future 未完成时，第二个同 Key 请求必须被 `CONCURRENCY_LIMIT` 拒绝，future 完成后才允许下一次；
- 通过真实 ASGI route 覆盖非法 slug、重复/超长 query、缺失/非法 API Key、404/405/422、quota/adapter 异常、响应 body 与 `X-Request-ID` 一致性；body/header 均不得出现 URL、堆栈、连接串、Token 或异常文本；
- `ApiResponse` 模型级一致性只引用已有测试，只有发现真实路由转换缺陷时才修改生产代码。

`test_secret_logging.py` 不复制既有 `test_redaction.py` 对嵌套脱敏、未知对象和超大 mapping 的单元矩阵；新增测试只验证 middleware—route—audit 联合链路的 caplog、公共错误响应和审计详情不出现敏感 header、query value、body、原始 IP、异常 repr、连接串或堆栈。

Step 1 运行 focused tests，必须保留真实 RED 输出；若已有实现直接通过，记录为“测试先于实现但现状已满足”，不为了制造失败而破坏代码。

安全测试套件必须自包含，只使用本文件声明的 fake 和隔离 fixture，不加载 `E:\AI_projects\yeyu-api\backend\tests\conftest.py`，避免意外连接真实数据库/Redis；因此验证命令中的 `--confcutdir=E:\AI_projects\yeyu-api\backend\tests\security` 是有意的。被复用的既有服务/路由测试另行按其原有 fixture 运行并单独记录阻塞。

### Step 2：只修复测试证明的生产缺陷

- 保持现有固定 adapter/provider registry；不让试验池、参数或管理页面产生任意 URL 执行能力。
- 保持错误信息固定、无连接串/Secret/堆栈；修复时先增加回归测试。
- 生产代码修改后运行 `ruff`、focused pytest 和 compileall。

### Step 3：写候选接口证据表

文档每一条记录必须包含：候选名称、来源/官方文档、账号/Key 要求、免费额度、服务条款版本/日期、授权主体、再分发许可、缓存许可、改写许可、署名、商业/非商业限制、地域限制、隐私限制、稳定性/延迟、返回格式、缓存规则、服务器成本、推荐动作、`registry_eligible` 和证据日期/链接。

- 只引用官方文档、官方条款或项目许可证页面；实时信息必须标注查询日期。
- 未找到明确再分发/缓存/改写授权的接口只能使用 `research_only` 或 `link_only`，不进入公开 API registry；`trial` 仅表示官方条款明确允许的内部受控试验，不表示允许注册账号、自动获取 Key、公开代理或再分发。
- 不写任何实际账号、Secret、Token、API Key、私钥或可恢复凭据。
- 暂不公开高滥用/高合规风险清单中列出的能力。

### Step 4：写发布与回滚资料

`release-checklist.md` 必须覆盖：本地环境、依赖/迁移、前后端构建、Compose、健康/就绪、邮箱、GitHub OAuth、API Key 生命周期、API Key 独立鉴权、限流/每日额度、工具接口、内容接口 stale fallback、管理权限、日志脱敏、DNS/HTTPS、移动端、原有站点无影响；每项固定包含 `status`（`verified|blocked|not_verified`）、环境、commit SHA、执行时间、命令/人工步骤、真实结果、证据位置、blocked/not_verified 原因、解除条件、责任人和失败/回滚动作。未执行不得标 `verified`；fake/mock 只证明本地契约；任何发布必需项非 verified 时结论必须是“不可发布/待验证”。

`rollback-runbook.md` 必须说明：发布目录、保留上一个可用版本、应用版本切换、健康检查失败处理、数据库 expand/contract 原则、禁止默认 downgrade、备份/恢复需单独确认、不得触碰旧网站和既有服务；不写服务器真实路径中的 Secret 或账号。

### Step 5：验证、独立审查和提交

验证顺序：

```powershell
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\security -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\security
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_execution.py -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\services
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_migrations.py -q
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_redaction.py E:\AI_projects\yeyu-api\backend\tests\services\test_audit.py E:\AI_projects\yeyu-api\backend\tests\services\test_policy.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py -q
Push-Location -LiteralPath E:\AI_projects\yeyu-api\backend
conda run -n yeyu-api alembic -c E:\AI_projects\yeyu-api\backend\alembic.ini heads
Pop-Location
conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app E:\AI_projects\yeyu-api\backend\tests
conda run -n yeyu-api python -m compileall -q E:\AI_projects\yeyu-api\backend\app E:\AI_projects\yeyu-api\backend\tests
pnpm --dir E:\AI_projects\yeyu-api\frontend exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json
pnpm --dir E:\AI_projects\yeyu-api\frontend exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src E:\AI_projects\yeyu-api\frontend\tests
git -C E:\AI_projects\yeyu-api diff --check
```

然后启动独立只读子代理审查 SSRF、资源耗尽、Secret 泄露、候选接口文档边界、迁移/回滚资料和测试证据。发现 Critical/Important 必须修复并复审后才能提交。

本 Task 不执行：真实公网 provider 请求、DNS/Nginx/证书/服务器变更、SMTP/GitHub OAuth 配置或线上验收。迁移 `upgrade` → `downgrade -1` → `upgrade` 只允许在本 Task 独占、可销毁的临时 PostgreSQL 上执行；Redis/Docker 也只能使用本 Task 独占的隔离实例，不得笼统宣称“只读”。未明确隔离实例归属或本机不具备条件时，相关状态固定为 `blocked` 或 `not_verified`，不得把 fake 测试替代为 `verified`。
