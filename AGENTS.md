# Yeyu API 项目协作规则

## 项目身份与边界

- 项目根目录固定为 `E:\AI_projects\yeyu-api`。
- 正式域名为 `https://api.yeyubaka.top`。
- 这是独立公益 API 聚合平台，不是 NewAPI、模型中转站或开放代理。
- 严禁修改 `E:\AI_projects\yeyubakahome_Web`。
- 严禁触碰已有的 `new.api.yeyubaka.top` 及其他现有服务；历史项目只允许只读检查。
- 部署必须使用独立目录、Compose 项目、数据库、缓存、日志和 Nginx vhost。
- 不得覆盖 `/www/wwwroot/yeyubaka.top`。

## 文件与命令规则

- 所有本地文件操作必须使用带盘符和反斜杠的完整 Windows 绝对路径。
- 设计文档放在 `E:\AI_projects\yeyu-api\docs\`。
- 实施计划放在 `E:\AI_projects\yeyu-api\plans\`。
- 视觉草图、浏览器快照等临时产物不得进入项目；`.playwright-mcp\` 和 `.superpowers\` 必须被忽略。
- 修改文本文件使用 `apply_patch`；不得使用 `cat`、here-doc 或字符串重定向写文件。
- 发现已有用户文件或未预期改动时先只读检查，不覆盖、不删除。

## 技术栈与环境

- 后端基于官方 `Full Stack FastAPI Template` 改造，采用 FastAPI、SQLModel/PostgreSQL、React/Vite/TypeScript、Docker Compose。
- Redis 用于分钟/IP/并发限流和短期缓存；PostgreSQL 保存权威业务数据、每日用量和审计元数据。
- 前端包管理优先使用 pnpm。
- Python 使用项目独立 conda 环境 `yeyu-api`；禁止使用 conda base 和 Windows Store Python。
- 依赖版本必须锁定并记录来源、许可证和升级策略。

## 安全与隐私

- 密码、SMTP 密码、GitHub OAuth Secret、数据库密码、上游 API Key、私钥只能放在环境变量或服务器 Secret 文件中。
- 仓库只允许提交 `.env.example`，禁止提交真实凭据。
- API Key 只保存不可逆哈希和公开前缀；完整密钥只在创建或轮换成功时显示一次。
- 日志、请求记录和审计记录不得包含明文 API Key、密码、OAuth token 或敏感请求正文。
- `/v1/*` 公共调用必须使用独立 API Key，不能因为浏览器登录 Cookie 存在而绕过鉴权。
- 所有第三方上游必须是固定适配器和 allowlist；禁止用户提交任意 URL，禁止开放代理和 SSRF。
- 外部内容必须有超时、重试、缓存、stale 标记、大小限制和并发限制；不得用占位内容冒充实时数据。

## 测试与证据

- 新功能先写失败测试，再实现最小行为；使用 pytest、Playwright 和必要的 PostgreSQL/Redis 集成测试。
- 必须区分单元测试、集成测试、浏览器 E2E、部署检查和真实线上验收。
- 健康检查或构建通过不等于产品验收通过；没有 SMTP、GitHub OAuth、DNS 或服务器权限时明确标记为阻塞/未验证。
- 测试输出不得打印 Secret；失败日志需要脱敏。

## 部署与变更

- DNS、Nginx、证书、服务器账号/权限和生产配置变更前，必须说明影响文件、验证方式和回滚方案，并等待用户确认。
- 正式部署不得长期依赖 root；发布流程使用最小权限账号和可回滚版本目录。
- 每个重大阶段完成后创建清晰 Git 提交；没有确认的远程仓库时不得推送。
- 任何线上验收必须同时验证新服务和原有网站/服务未受影响。
