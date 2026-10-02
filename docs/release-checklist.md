# Yeyu API 发布验收清单

## 1. 使用规则

每个条目必须填写以下固定字段：

- status：只能是 verified、blocked 或 not_verified。
- environment：执行环境、版本和是否隔离。
- commit_sha：实际被验证的提交；未提交时写“未提交”。
- checked_at：带时区的实际执行时间。
- command_or_steps：完整命令或人工步骤。
- actual_result：真实输出或人工观察，不写推测。
- evidence：日志、测试报告、截图或链接的绝对路径/来源。
- blocker_and_exit_condition：阻塞原因、解除条件和责任人。
- rollback_action：失败时采取的可回滚动作。

verified 只代表该条目在写明环境中真实完成，不代表整个平台可以发布。fake/mock 只证明本地契约；未执行不得标 verified。任何发布必需项不是 verified，结论必须为“不可发布/待验证”。

## 2. 当前基线记录

| 发布项 | status | environment | commit_sha | checked_at | command_or_steps | actual_result | evidence | blocker_and_exit_condition | rollback_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Task 8 安全跨组件回归 | not_verified | Windows；conda env yeyu-api；fake/SQLite 隔离 fixture | 未提交（本轮工作树） | 2026-10-02T20:30:09+08:00 | conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\security -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\security | 16 passed；2 个依赖弃用 warning；当前结果尚未绑定最终 commit SHA | E:\AI_projects\yeyu-api\plans\verification\task-8-implementation-evidence.md | 最终提交后重跑并填写最终 SHA/时间；负责人：开发者 | 保留前一可用提交，修复失败项后再提交 |
| 后端完整测试 | not_verified | Windows；缺少已确认的完整运行时配置 | 未提交 | 2026-10-02 Asia/Hong_Kong | 按项目 pytest 全量命令执行 | 本轮未将全量测试结果冒充通过 | E:\AI_projects\yeyu-api\plans\ | 需要非生产测试数据库、必需环境变量和隔离服务；负责人：项目运营者 | 不改变数据库；仅修复测试环境后重跑 |
| Alembic upgrade/downgrade/upgrade | not_verified | 独占、可销毁 PostgreSQL 才允许执行 | 未提交 | 2026-10-02 Asia/Hong_Kong | 在独占临时库执行 upgrade → downgrade -1 → upgrade | 未在真实隔离 PostgreSQL 执行，不能用 SQLite/fake 替代 | E:\AI_projects\yeyu-api\plans\task-8-security-release.md | 取得隔离库并记录连接方式后执行；不得使用共享/生产库 | 删除临时库或恢复临时库快照；生产默认不 downgrade |
| 单 Alembic head 与 migration tests | not_verified | Windows；conda env yeyu-api | 未提交 | 2026-10-02 Asia/Hong_Kong | 执行 test_migrations.py 与 backend 工作目录下 alembic heads | 待 Task 8 最终验证 | E:\AI_projects\yeyu-api\plans\ | 需要确认命令输出并写入报告 | 无生产变更 |
| 后端 lint/compile | not_verified | Windows；conda env yeyu-api | 未提交 | 2026-10-02 Asia/Hong_Kong | ruff check；compileall | 待 Task 8 最终验证 | E:\AI_projects\yeyu-api\plans\ | 失败则修复并复跑；负责人：开发者 | 回退未通过的代码提交 |
| 前端 TypeScript/格式检查 | not_verified | Windows；pnpm | 未提交 | 2026-10-02 Asia/Hong_Kong | pnpm exec tsc；pnpm exec biome check | Task 7 已有局部检查通过；Task 8 需按最终提交重跑 | E:\AI_projects\yeyu-api\plans\ | 依赖环境需完整；负责人：开发者 | 保留前一可用前端提交 |
| 前端生产构建 | blocked | Windows；pnpm；本机 SWC native binding 缺失 | 未提交 | 2026-10-02 Asia/Hong_Kong | pnpm run build | 当前被 @swc/core native binding/DACL 问题阻塞，不能宣称构建通过 | E:\AI_projects\yeyu-api\plans\ | 修复本机依赖/DACL 后重跑；不修改业务代码绕过 | 不发布未构建版本 |
| Docker Compose 与容器健康 | blocked | Windows；Docker CLI 当前不可用 | 未提交 | 2026-10-02 Asia/Hong_Kong | docker compose config/up/health | 本轮未执行，Docker command unavailable | E:\AI_projects\yeyu-api\plans\ | 安装/启用隔离 Docker 后执行；负责人：环境维护者 | 仅清理本 Task 隔离 Compose 资源 |
| /health 与 /ready | not_verified | 本地 fake/依赖隔离 | 未提交 | 2026-10-02 Asia/Hong_Kong | TestClient/容器 endpoint 检查 | 本地接口契约可测；未代表生产就绪 | E:\AI_projects\yeyu-api\plans\ | 需要容器和真实依赖环境 | 停止本 Task 版本并切回上一版本 |
| 邮箱注册、验证、密码重置 | blocked | 未提供 SMTP 凭据 | 未提交 | 2026-10-02 Asia/Hong_Kong | 使用测试邮箱完成注册、验证、重置 | 未执行；缺 SMTP 与可控测试邮箱 | E:\AI_projects\yeyu-api\plans\ | 由项目运营者提供并确认 SMTP/测试邮箱；不把凭据写入仓库 | 撤销测试账号/回滚应用版本 |
| GitHub OAuth 与身份绑定 | blocked | 未提供 OAuth Client/Secret 和回调配置 | 未提交 | 2026-10-02 Asia/Hong_Kong | 完成授权、回调、绑定和解绑验证 | 未执行；不替用户注册或接受协议 | E:\AI_projects\yeyu-api\plans\ | 由项目运营者配置 Secret 文件并确认回调域名 | 删除测试授权关联，切回上一版本 |
| API Key 创建/查看前缀/撤销/轮换 | not_verified | 本地隔离数据库 | 未提交 | 2026-10-02 Asia/Hong_Kong | 浏览器和 API 调用手工/E2E 测试 | Task 7 有局部实现证据；最终发布包需重跑 | E:\AI_projects\yeyu-api\plans\ | 完整登录与数据库环境可用后执行 | 撤销测试 Key，保留哈希不回显 Secret |
| API Key 独立鉴权与 Cookie 隔离 | not_verified | Windows；本地 SQLite/fake Redis | 未提交 | 2026-10-02T20:30:09+08:00 | security/public route tests | 缺 Key、错误 Key、Cookie 不绕过的本地契约已覆盖；最终提交和生产验收仍待完成 | E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py | 最终提交后重跑；生产验收仍待完成 | 禁用测试 Key，回滚应用版本 |
| 分钟/IP/每日/并发额度 | not_verified | 本地 fake Redis/SQLite | 未提交 | 2026-10-02 Asia/Hong_Kong | 隔离集成测试和真实 Redis 验证 | fake 仅证明契约；真实 Redis 未验证 | E:\AI_projects\yeyu-api\plans\ | 需要独占 Redis 与 PostgreSQL | 停止新版本，保留数据备份 |
| 工具接口与内容接口 stale fallback | not_verified | 工具为本地；内容 provider 未授权 | 未提交 | 2026-10-02 Asia/Hong_Kong | 至少一个工具和一个获授权内容接口的成功/超时/缓存测试 | 当前没有获授权的公开内容 provider | E:\AI_projects\yeyu-api\docs\candidate-api-trial-pool.md | 完成 provider 权利确认并在隔离环境验收 | 从 registry 移除未获授权 provider |
| 管理权限与审计 | not_verified | 本地隔离数据库 | 未提交 | 2026-10-02 Asia/Hong_Kong | 普通用户、API Key、过期/无效 token、superuser 对管理路由验证 | Task 7 有局部测试，最终发布包需重跑 | E:\AI_projects\yeyu-api\plans\ | 需要完整认证 fixture | 回滚管理端代码并保留审计数据 |
| 日志无 Secret/敏感正文 | not_verified | 本地 caplog/fake request | 未提交 | 2026-10-02T20:30:09+08:00 | security logging tests 与 redaction/audit tests | 本地联合链路已观察通过；最终提交 SHA 和真实日志采集器仍未验证 | E:\AI_projects\yeyu-api\plans\verification\task-8-implementation-evidence.md | 最终提交后重跑，并在部署后检查真实日志采集器；负责人：开发者 | 清理受影响日志并停止泄露版本 |
| DNS、HTTPS、证书、正式域名 | blocked | 公网/服务器，按边界本轮不触碰 | 未提交 | 2026-10-02 Asia/Hong_Kong | DNS 查询、TLS、域名首页与 API smoke | 未执行；需用户明确确认后才可变更 | E:\AI_projects\yeyu-api\plans\ | 需用户确认影响文件、验证和回滚 | 删除独立 vhost/证书并恢复 DNS |
| 移动端和桌面浏览器体验 | not_verified | 本地/正式域名未部署 | 未提交 | 2026-10-02 Asia/Hong_Kong | Playwright viewport smoke | 未执行 | E:\AI_projects\yeyu-api\plans\ | 前端构建和可访问环境具备后执行 | 回滚前端版本 |
| 原有网站、音乐 API、Waline 与 new.api 未受影响 | blocked | 旧服务/服务器按边界本轮不触碰 | 未提交 | 2026-10-02 Asia/Hong_Kong | 部署前后只读端口、vhost、首页和既有服务 smoke | 未执行；不得虚构未受影响 | E:\AI_projects\yeyu-api\plans\ | 需用户确认服务器只读 preflight 与验收范围 | 立即切回上一版本，保留旧服务配置不动 |

## 3. 发布门禁

当前结论：不可发布/待验证。前端生产构建、Docker、SMTP、GitHub OAuth、DNS/HTTPS、真实 PostgreSQL/Redis 和线上验收仍非 verified；候选外部接口也没有公开再分发授权。任何人不得仅凭局部 focused tests、/health 或静态检查宣布上线。

正式发布前必须把每个必需项的未提交占位替换为真实 commit SHA、带时区时间、命令/人工步骤、输出和证据位置。缺少外部凭据时必须保留 blocked，不得代替用户注册或接受协议。
