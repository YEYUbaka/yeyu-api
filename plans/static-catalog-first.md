# Static API Catalog First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先在 `E:\AI_projects\yeyu-api` 本地完成公益 API 平台，再单独生成一个不依赖后端、只展示审核资料的免费 API 静态目录站；动态 API、账号、Key、PostgreSQL、Redis、SMTP、OAuth 暂不上线。

**Architecture:** 现有 FastAPI + React/Vite 平台继续作为本地完整产品，服务器部署边界新增一个独立的静态目录产物。静态站使用现有前端的 React、Tailwind 和视觉 tokens，但使用独立 Vite entry、编译期目录数据和客户端搜索/筛选，不请求本项目后端、不代理第三方接口、不提供账号或调用能力。静态站未来只作为 Nginx 静态 root，使用独立发布目录和回滚版本。

**Tech Stack:** React 19、TypeScript、Vite 8、Tailwind CSS、pnpm、Playwright；静态发布不依赖 Docker、Python、PostgreSQL、Redis 或 Nginx upstream。

## Global Constraints

- 动态公益 API 平台只在 `E:\AI_projects\yeyu-api` 本地开发和验收，未完成前不部署生产后端。
- 静态站默认设计目标为 `https://api.yeyubaka.top`，但 DNS、证书、Nginx 和服务器发布执行前必须单独说明影响、验证和回滚并等待确认。
- 严禁修改 `E:\AI_projects\yeyubakahome_Web`、现有 `new.api.yeyubaka.top`、既有 Nginx vhost 和其他服务。
- 静态目录只发布已记录来源、官方文档、许可/再分发判断和更新时间的资料；未经授权的第三方接口只能标记为“资料链接/自行核验”，不能包装成我方 API。
- 静态站不得包含密码、Token、OAuth Secret、API Key、私钥、上游凭据或可调用的敏感 URL。
- Python 继续使用 conda 环境 `yeyu-api`；前端继续使用 pnpm；所有项目计划写入 `E:\AI_projects\yeyu-api\plans\`。
- 每个任务完成后先执行该任务的验证，再创建独立 Git 提交；没有用户确认不执行服务器、DNS、Nginx 或证书变更。

---

### Task 1: 建立静态目录内容契约与审核边界

**Files:**

- Create: `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\types.ts`
- Create: `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\data.json`
- Create: `E:\AI_projects\yeyu-api\frontend\scripts\validate-static-catalog.mjs`
- Modify: `E:\AI_projects\yeyu-api\frontend\package.json`
- Test: `E:\AI_projects\yeyu-api\frontend\scripts\validate-static-catalog.mjs`

**Interfaces:**

- `StaticCatalogEntry` 必须包含：`slug`、`name`、`category`、`summary`、`sourceUrl`、`officialDocsUrl`、`licenseStatus`、`redistributionMode`、`freeTier`、`authRequired`、`stability`、`updatedAt`、`displayStatus`。
- `redistributionMode` 只允许 `self-operated`、`reference-only`、`link-only`；只有 `self-operated` 可以在静态站显示“Yeyu 自营候选”，另外两类必须显示资料/外链性质。
- `sourceUrl` 和 `officialDocsUrl` 必须是 HTTPS；目录数据不得包含 `apiKey`、`token`、`secret`、`password`、`authorization`、`cookie`、私钥或任意用户提交 URL。
- `displayStatus` 只允许 `candidate`、`verified-reference`、`self-operated-ready`；没有真实验证证据的条目不得显示“稳定可用”或“已接入”。

- [x] **Step 1: 从 `E:\AI_projects\yeyu-api\docs\candidate-api-trial-pool.md` 和现有自营工具目录提取可公开展示字段。** 将经人工审核的目录写入 `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\data.json`；每条记录保留来源、官方文档、免费额度、协议/再分发结论和更新时间；未授权第三方只进入 `reference-only` 或 `link-only`。
- [x] **Step 2: 编写静态目录数据校验脚本。** 使用 Node 内置 `fs` 和 `JSON.parse` 读取 `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\data.json`，检查 slug 唯一、必填字段、HTTPS、状态枚举、敏感字段和外链格式；发现任何违规字段时以非零退出码结束。
- [x] **Step 3: 将校验命令加入前端脚本。** `E:\AI_projects\yeyu-api\frontend\package.json` 增加 `validate:static-catalog`，命令固定为 `node scripts/validate-static-catalog.mjs`。
- [x] **Step 4: 运行失败与通过验证。** 已记录数据文件缺失时校验器非零失败，恢复审核数据后运行 `pnpm --dir E:\AI_projects\yeyu-api\frontend run validate:static-catalog` 通过；输出不包含 Secret。非法字段专用 fixture 仍作为后续校验器增强项，不把缺失文件失败误写成 fixture 失败。
- [x] **Step 5: 提交。** 本阶段代码、数据校验和测试将在静态目录阶段提交；提交前执行 `git -C E:\AI_projects\yeyu-api diff --cached --check`。

### Task 2: 创建独立静态 Vite 入口并复用现有视觉基线

**Files:**

- Create: `E:\AI_projects\yeyu-api\frontend\static-catalog.html`
- Create: `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\main.tsx`
- Create: `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\StaticCatalogApp.tsx`
- Create: `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\StaticCatalogCard.tsx`
- Create: `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\StaticCatalogFilters.tsx`
- Create: `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\static-catalog.css`
- Create: `E:\AI_projects\yeyu-api\frontend\vite.static.config.ts`
- Modify: `E:\AI_projects\yeyu-api\frontend\package.json`
- Reuse: `E:\AI_projects\yeyu-api\frontend\src\index.css`

**Interfaces:**

- `StaticCatalogApp` 接收 `ReadonlyArray<StaticCatalogEntry>`，只在浏览器内执行搜索和分类筛选；状态和再分发结论作为卡片元数据展示。
- `StaticCatalogCard` 只渲染目录元数据和受控的官方来源/文档链接，不生成 Yeyu API 调用示例，不渲染 API Key 输入，不接受任意 URL。
- `vite.static.config.ts` 的输出目录固定为 `E:\AI_projects\yeyu-api\deploy\static-catalog`，源码入口固定为 `E:\AI_projects\yeyu-api\frontend\static-catalog.html`，并在构建收尾规范化为产物 `index.html`；不得复用动态平台的 `backend\app\frontend` 输出目录。

- [x] **Step 1: 创建静态 HTML 入口。** 只包含 `#root`、页面标题、描述和 `/src/staticCatalog/main.tsx` 入口，不加载 FastAPI、React Query、TanStack Router、登录状态或 OpenAPI client。
- [x] **Step 2: 复用视觉基线。** 在静态入口中导入现有 `E:\AI_projects\yeyu-api\frontend\src\index.css` 和已有颜色/间距 tokens；静态站保留搜索优先、简洁、可信的目录布局，不加入虚假统计、夸张渐变或商业计费模块。
- [x] **Step 3: 实现本地搜索和筛选。** 搜索只匹配 `name`、`summary`、`category`、`slug`；筛选只使用已审核的 category；空结果显示明确的静态状态，不请求网络。
- [x] **Step 4: 实现来源和合规提示。** 每张卡片显示“免费性质”“是否需要 Key”“协议/再分发状态”“更新时间”“来源/官方文档”；`reference-only` 和 `link-only` 显示资料/官方链接性质，不冒充 Yeyu 代理。
- [x] **Step 5: 配置独立静态构建。** `vite.static.config.ts` 只使用 React 和 Tailwind 插件，输出到 `E:\AI_projects\yeyu-api\deploy\static-catalog`；`package.json` 已增加 `build:static-catalog` 和 `preview:static`。
- [x] **Step 6: 运行构建验证。** 已运行目录校验、TypeScript、Biome、`pnpm --dir E:\AI_projects\yeyu-api\frontend run build:static-catalog`；产物仅包含静态 HTML、JS、CSS 资源，生成目录由 Git 忽略。
- [x] **Step 7: 提交。** 通过 `git -C E:\AI_projects\yeyu-api diff --check` 后提交本阶段静态目录实现。

### Task 3: 静态站浏览器验收和无后端证明

**Files:**

- Create: `E:\AI_projects\yeyu-api\frontend\playwright.static.config.ts`
- Create: `E:\AI_projects\yeyu-api\frontend\tests\static-catalog.spec.ts`
- Modify: `E:\AI_projects\yeyu-api\frontend\package.json`

**Interfaces:**

- Playwright 静态测试服务器只提供 `E:\AI_projects\yeyu-api\deploy\static-catalog`，通过 `pnpm run preview:static` 固定监听 `127.0.0.1:4174`，不连接远程服务器。
- 测试必须记录页面请求；除同源静态资源外不得出现 `/api/`、`/v1/`、OAuth、SMTP 或任意第三方上游请求。

- [x] **Step 1: 编写失败测试。** 覆盖首页标题、真实候选接口名称、搜索、分类筛选、官方文档链接、移动 viewport 和“仅资料汇总”提示；空结果也有实现状态。
- [x] **Step 2: 运行测试确认缺少静态入口时失败。** 已记录静态入口错误导致页面元素不存在的真实失败，未连接生产域名。
- [x] **Step 3: 完成静态页面后重跑。** 桌面和移动场景最终 10/10 通过；页面请求只包含测试静态服务器资源，官方链接只检查 href。
- [ ] **Step 4: 回归动态前端契约。** 运行现有 TypeScript、Biome 和 public catalog Playwright 测试；静态入口不得修改动态平台的登录、API Key、管理端或后端调用行为。
- [x] **Step 5: 提交。** 测试输出脱敏且通过后，运行 `git -C E:\AI_projects\yeyu-api diff --check`，并随本次静态目录阶段提交。

### Task 4: 动态公益 API 平台本地完成门禁

**Files:**

- Modify only the specific implementation files identified by the approved local task plans under `E:\AI_projects\yeyu-api\plans\`.
- Test: existing backend tests under `E:\AI_projects\yeyu-api\backend\tests\`
- Test: existing frontend tests under `E:\AI_projects\yeyu-api\frontend\tests\`

- [ ] **Step 1: 保持动态平台不部署。** 所有 SMTP、GitHub OAuth、PostgreSQL、Redis、API Key、限流、缓存、管理端工作只在本机隔离环境验证；没有真实凭据时保留 blocked/not_verified。
- [ ] **Step 2: 先解决本地构建环境门禁。** Docker Desktop/Engine 是否安装另行决定；若只使用远程 Docker CLI，不能把远程只读连通当成本地容器测试通过。前端 SWC native binding/DACL 问题必须通过环境修复验证，不修改业务代码绕过。
- [ ] **Step 3: 完成真实本地容器验证。** 取得隔离 Docker Engine 后，使用显式 `-f E:\AI_projects\yeyu-api\compose.yml` 或专用测试 Compose，禁止误加载生产配置；执行 `config`、依赖启动、迁移、健康检查、测试和清理，禁止对现有服务器资源执行 `down -v`。
- [ ] **Step 4: 运行发布门禁。** 更新 `E:\AI_projects\yeyu-api\docs\release-checklist.md`，逐项记录命令、版本、真实输出和证据；局部测试通过不得替代 SMTP、OAuth、真实 PostgreSQL/Redis 和线上验收。
- [ ] **Step 5: 每个本地重大阶段独立提交并安排只读审查。** 审查只检查对应任务差异和测试证据，不修改旧项目、服务器、DNS、Nginx 或凭据。

### Task 5: 静态站服务器发布准备（不执行发布）

**Files:**

- Create: `E:\AI_projects\yeyu-api\deploy\static-catalog-README.md`
- Create: `E:\AI_projects\yeyu-api\deploy\nginx\api.yeyubaka.top.static.conf.example`
- Create: `E:\AI_projects\yeyu-api\deploy\scripts\package-static-catalog.ps1`
- Modify: `E:\AI_projects\yeyu-api\docs\rollback-runbook.md`

- [x] **Step 1: 设计独立静态发布目录。** 目标服务器只使用 `/opt/yeyu-api-static/releases/<commit-sha>/` 和 `current` 指针；不使用 `/www/wwwroot/yeyubaka.top`，不复用 `new.api.yeyubaka.top`，不创建 Docker 容器。
- [x] **Step 2: 编写仅匹配目标域名的 Nginx 示例。** 示例只包含 `server_name api.yeyubaka.top`、静态 root、SPA fallback、静态资源缓存和基础安全响应头；不复制现有 Nginx 配置，不新增其他域名或动态 upstream。
- [x] **Step 3: 编写本地打包脚本。** 脚本只读取 `E:\AI_projects\yeyu-api\deploy\static-catalog`，输出带 commit SHA 的可回滚压缩包和文件清单；禁止敏感文件名，不读取 `.env`、私钥或任何 Secret。
- [x] **Step 4: 编写回滚步骤。** 发布失败时只把静态站 `current` 指针切回上一版本，并撤回 Yeyu API 独立 vhost；不得执行 `docker compose down`、删除共享卷或修改旧服务配置。
- [x] **Step 5: 提交发布准备文件。** 运行路径扫描，确认没有旧站覆盖写入、Secret 和破坏性清理命令后提交发布准备阶段。

### Task 6: 静态站正式变更前的单独确认门

- [ ] **Step 1: 重新做服务器只读 preflight。** 检查 `/opt/yeyu-api-static`、权限、磁盘、现有 Nginx、80/443、目标 DNS、TLS 和旧服务状态；不改任何文件。
- [ ] **Step 2: 提交变更说明。** 明确影响文件（仅新增静态发布目录和 `api.yeyubaka.top` 独立 vhost）、验证命令（`nginx -t`、域名 HTTPS、移动端静态资源、旧站点 smoke）和回滚命令（切回上一 release、撤回独立 vhost）。
- [ ] **Step 3: 等待用户确认后才修改 DNS/Nginx/服务器。** 没有确认时只保留本地静态产物和部署包，不执行远程上传、目录创建、vhost 写入、证书申请或 DNS 变更。
- [ ] **Step 4: 发布后只验收静态范围。** 验收首页、搜索/筛选、移动端、官方文档链接、HTTPS、日志和旧站点/`new.api.yeyubaka.top` 未受影响；不得把静态目录站验收结果宣称为动态 API 平台上线。

## Scope gaps recorded explicitly

- 静态目录站不提供动态 API 调用、API Key、账号、管理端、配额、限流、缓存、stale fallback 或上游代理。
- 第三方 API 的免费额度和条款可能变化；静态站必须展示核验时间和“调用前自行核验”提示，不能把历史调研当成当前授权。
- 动态平台仍需完成本地真实 PostgreSQL/Redis、前端生产构建、SMTP/OAuth 配置门禁后，才进入单独的生产部署设计。
