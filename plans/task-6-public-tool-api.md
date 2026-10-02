# Task 6：固定自营工具公共调用路由

## 目标

在现有 Full Stack FastAPI Template 改造基础上，交付第一条可本地验证的公共 API 调用边界：

- `GET /api/v1/tools/time`
- `GET /api/v1/tools/uuid`

两条接口均只接受独立 `X-API-Key`，经过公开目录状态检查、账号/Key/IP/接口策略、Redis 分钟/IP/并发限流、PostgreSQL 每日额度后，才进入固定 `builtin-tools` 执行器。内容类第三方接口继续保持未批准、未注册和不可公开调用。

## 严格边界

- 只修改 `E:\AI_projects\yeyu-api`；不读取或修改旧个人网站仓库，不触碰 `new.api.yeyubaka.top`、DNS、Nginx 或服务器。
- 不接受 Cookie 作为公共调用凭据，不接受任意 URL、上游地址、代理参数或用户可控 adapter。
- 只允许注册表中固定的 `time`、`uuid`；数据库目录记录必须为 `visibility=public` 且 `status=healthy/published`，并与固定方法、路径、adapter 名称一致。
- Redis 或每日额度数据库出现不可用时 fail closed；不在错误响应中返回连接串、Secret、内部堆栈或请求正文。
- 本 Task 不实现邮箱、GitHub OAuth、内容接口、管理试验池、审计日志和线上部署。

## 预期接口契约

- 成功：`200`，返回 `success=true`、`data`、`error=null`、`meta.request_id`、`meta.cache_hit=false`、`meta.stale=false`、`meta.data_at`。
- 参数错误：`422`，返回统一 `error.code=INVALID_PARAMETERS` 或 `RESOURCE_LIMIT`。
- 无 Key/错误 Key/撤销 Key/未验证/封禁：沿用现有 API Key 错误结构和状态码。
- 策略拒绝：`403` 或 `429`，返回安全错误码，并在 `meta` 中仅保留剩余额度和重试秒数等非敏感信息。
- 执行超时/上游错误：分别映射 `504`/`502`，不伪造成功数据。
- 公共调用使用 `request.client.host` 作为 IP；不信任 `X-Forwarded-For` 等客户端头。

## 实施步骤

### 1. 先写失败测试

新增 `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py`，覆盖：

- 路由在 OpenAPI 中注册，并声明 `X-API-Key` security scheme；
- Cookie 单独访问被拒绝；无效和撤销 Key 被拒绝；
- 公开 healthy/published 的 `time`/`uuid` 可调用；draft/disabled/不存在的目录不可执行；
- `time` 只接受受控 `timezone`，`uuid` 不接受参数；异常参数不会进入 adapter；
- policy admission 只消费一次，成功执行后并发 lease 必须释放；分钟/IP/每日/并发拒绝映射为统一错误；
- Redis/每日额度依赖不可用时 fail closed；
- 不把 API Key、Cookie 或请求敏感字段写入响应。

先运行新增测试，记录其真实失败原因，再实现最小行为。

### 2. 接入依赖和路由

- 在 `app/api/deps.py` 增加可覆盖的 `RedisStore` 依赖；生产调用失败时映射为安全的 `QUOTA_UNAVAILABLE`。
- 新建 `app/api/routes/public_api.py`，只声明 `GET /tools/{slug}`；解析 query 参数时限制大小并交给固定 adapter 再次校验。
- 路由先鉴权，再查公开目录和固定 adapter，再 `PolicyService.evaluate()`，随后使用同一个 decision 调用 `acquire()`，用 `try/finally` 释放 `QuotaLease`。
- 使用请求内生成的 request id 构造 `ExecutionContext`；通过 `JSONResponse` 保持统一响应和准确 HTTP 状态码。
- 在 `app/api/main.py` 注册 router；同步更新 OpenAPI 契约测试。

### 3. 本地验证和交付

```powershell
conda run -n yeyu-api pytest -q --confcutdir="E:\AI_projects\yeyu-api\backend\tests\api\routes" "E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py"
conda run -n yeyu-api ruff check "E:\AI_projects\yeyu-api\backend\app\api\deps.py" "E:\AI_projects\yeyu-api\backend\app\api\main.py" "E:\AI_projects\yeyu-api\backend\app\api\routes\public_api.py" "E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py"
conda run -n yeyu-api python -m compileall -q "E:\AI_projects\yeyu-api\backend\app" "E:\AI_projects\yeyu-api\backend\tests"
git -C "E:\AI_projects\yeyu-api" diff --check
git -C "E:\AI_projects\yeyu-api" status --short --branch
```

通过后再运行相关 API Key、策略、执行层回归测试，检查 changed paths 和 secret safety，创建清晰 Git 提交并推送 `origin/main`。没有 Redis/PostgreSQL/Docker/外部凭据时，明确记录为未验证或阻塞，不将静态检查冒充线上验收。

## 完成判定

- [x] 新增测试先真实 RED，再真实 GREEN。
- [x] 公共工具路由只接受 API Key，Cookie 不得绕过。
- [x] 额度/限频/admission/lease/执行/错误响应边界有测试证据。
- [x] 内容适配器仍未注册，候选第三方接口仍未公开。
- [x] 本地静态检查和相关回归测试通过（聚焦路由 `16 passed`、策略/执行回归 `68 passed`、Ruff、compileall、diff-check 均通过；全量 API 夹具仍受本机 PostgreSQL 认证阻塞）。
- [x] Git 提交、推送和远端 CI 结果真实记录。

## 执行证据（2026-10-02）

- 新增测试首次运行真实 RED：收集阶段因待实现的 `get_client_ip` 依赖不存在而失败；实现后隔离运行结果为 `16 passed`。
- 隔离测试覆盖无 Key、Cookie 不绕过、有效 Key、无效/撤销 Key、healthy/published、trial/未注册 slug、固定路径、参数边界、策略 403/429、Redis/lease 故障 503、lease 清理、客户端 IP 和 OpenAPI API Key security，共 `16 passed`。
- Ruff：变更 Python 文件 `All checks passed`；compileall 退出码 0；`git diff --check` 无空白错误。
- 相关服务回归：`test_policy.py` 与 `test_execution.py` 共 `68 passed`。
- 全量 API 路由回归在本机未完成：根测试夹具会初始化默认 PostgreSQL，当前本地连接使用的测试配置认证失败；该范围标记为未验证，不能视为产品或线上验收通过。
- 独立只读安全审查代理完成：未发现 P0/P1；P2 指出的数据库异常统一映射已补为 503，runner/model 脱敏依赖已由执行层既有严格响应契约和测试覆盖。审查范围未包含 registry.py，但已人工核对当前 `BUILTIN_SLUGS=(time, uuid)`。
- Git 提交：`63fd4a3 feat: expose guarded public tool routes`；远端 `origin/main` 已确认指向 `63fd4a31748e9a57ff2588f325492352edfb795a`。
- 远端 CI 针对该提交全部成功：Test Backend `36973887958`、Test Docker Compose `36973887766`、Playwright Tests `36973887719`、Zizmor `36973887675`；Playwright 四个分片及报告合并也成功。
