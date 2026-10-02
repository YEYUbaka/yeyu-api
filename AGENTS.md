# Yeyu API 项目协作规则

## 项目身份与边界

- 项目根目录固定为 `E:\AI_projects\yeyu-api`。
- 正式域名为 `https://api.yeyubaka.top`。
- 这是独立的静态公益 API 收集目录，不是 API 服务平台、NewAPI、模型中转站或开放代理。
- 当前范围只收集和展示第三方 API 的资料、分类、官方来源与文档链接；不提供 API 调用、代理、转发或账号体系。
- 严禁修改 `E:\AI_projects\yeyubakahome_Web`。
- 严禁触碰已有的 `new.api.yeyubaka.top` 及其他现有服务；历史项目只允许只读检查。
- 部署只发布独立的静态文件目录和 `api.yeyubaka.top` 专用 Nginx vhost；不新增 Compose、数据库、缓存或动态 upstream。
- 不得覆盖 `/www/wwwroot/yeyubaka.top`。

## 文件与命令规则

- 所有本地文件操作必须使用带盘符和反斜杠的完整 Windows 绝对路径。
- 设计文档放在 `E:\AI_projects\yeyu-api\docs\`。
- 实施计划放在 `E:\AI_projects\yeyu-api\plans\`。
- 视觉草图、浏览器快照等临时产物不得进入项目；`.playwright-mcp\` 和 `.superpowers\` 必须被忽略。
- 修改文本文件使用 `apply_patch`；不得使用 `cat`、here-doc 或字符串重定向写文件。
- 发现已有用户文件或未预期改动时先只读检查，不覆盖、不删除。

## 技术栈与环境

- 当前交付基于 React/Vite/TypeScript 的静态站，目录数据在构建时打包为本地 JSON，浏览器端只做搜索与筛选。
- 仓库中历史保留的 FastAPI/PostgreSQL/Redis 代码不属于当前交付范围，不得因为本项目继续收集 API 而扩展为运行时服务。
- 前端包管理优先使用 pnpm。
- Python 使用项目独立 conda 环境 `yeyu-api`；禁止使用 conda base 和 Windows Store Python。
- 依赖版本必须锁定并记录来源、许可证和升级策略。

## 安全与隐私

- 不在静态目录中存储密码、SMTP 密码、GitHub OAuth Secret、数据库密码、上游 API Key、私钥或任何调用凭据。
- 仓库只允许提交 `.env.example`，禁止提交真实凭据。
- 目录只允许人工审核后的固定 HTTPS 来源和官方文档链接；禁止用户提交任意 URL，禁止把目录变成开放代理或 SSRF 入口。
- 页面必须明确“仅资料收集、调用前阅读官方条款”，不得把第三方 API 伪装成 Yeyu 服务，不得虚构免费额度、健康状态或实时数据。

## 测试与证据

- 新功能先写失败测试，再实现最小行为；当前以 Playwright 静态页面测试、数据校验和构建检查为主。
- 必须区分单元测试、集成测试、浏览器 E2E、部署检查和真实线上验收。
- 构建通过不等于线上验收通过；没有 DNS、证书或服务器权限时明确标记为阻塞/未验证。
- 测试输出不得打印 Secret；失败日志需要脱敏。

## 部署与变更

- DNS、Nginx、证书、服务器账号/权限和生产配置变更前，必须说明影响文件、验证方式和回滚方案，并等待用户确认。
- 正式静态发布不得长期依赖 root；发布流程使用最小权限账号和可回滚版本目录。
- 每个重大阶段完成后创建清晰 Git 提交；没有确认的远程仓库时不得推送。
- 任何线上验收必须同时验证新服务和原有网站/服务未受影响。
