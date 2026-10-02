# Public Catalog and Home UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 将已确认的 A+B 视觉方案落地为可访问的公共首页、目录和详情页，并把现有登录后模板首页迁移到 /dashboard；同时为两个内置工具接口提供幂等的初始目录数据，保证公开目录只展示真实可执行且已审核的接口。

**Architecture:** 保留现有 Full Stack FastAPI Template 作为工程底座。后端通过独立的目录种子模块写入固定的 time 与 uuid 元数据，复用现有 catalog API 和 builtin-tools 执行适配器；前端使用 TanStack Router 的文件路由、生成的 OpenAPI client 和 React Query，新增无认证公共壳层，继续使用受保护的 pathless layout 承载 dashboard、items、settings、admin。公共页只消费白名单目录 API，不实现任意上游代理或临时调试代理。

**Tech Stack:** FastAPI、SQLModel、PostgreSQL、pytest、React 19、TypeScript、Vite、TanStack Router、TanStack Query、Tailwind CSS v4、Biome、Playwright、pnpm。

## Global Constraints

- [ ] 所有本阶段文件仅限 E:\AI_projects\yeyu-api；严禁读取后写入 E:\AI_projects\yeyubakahome_Web，严禁触碰 new.api.yeyubaka.top、现有服务器、DNS、Nginx 和其他线上服务。
- [ ] 所有计划和审查报告放在 E:\AI_projects\yeyu-api\plans\ 或其子目录；视觉临时截图不进入仓库。
- [ ] 不新增第三方免费接口代理，不提交 API Key、OAuth Secret、SMTP 密码、数据库密码、私钥或任何真实凭据。示例中的密钥只允许使用 <YOUR_API_KEY> 这类明确不可用占位符。
- [ ] 不改手生成的 E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts；由 TanStack Router/Vite 在构建期间生成。
- [ ] 不引入远程字体、远程图片、渐变背景、虚假统计或“接口数量/请求次数”营销数字。视觉使用本地 CSS 变量和已有图标依赖。
- [ ] 公共页面必须不依赖浏览器 Cookie 登录；受保护页面必须继续由 E:\AI_projects\yeyu-api\frontend\src\routes\_layout.tsx 的认证门禁保护。
- [ ] 本阶段不实现在线调试、API Key 管理、邮箱验证、GitHub OAuth、额度扣减或第三方内容接口；这些能力在既有计划中继续单独验收。
- [ ] 每个实现任务先写失败测试或明确的测试断言，再写最小实现。每个任务完成后先运行任务级验证，再由独立只读子代理审查，处理 Critical 和 Important 问题并复审，最后提交并推送。

## Current Foundation and Fixed Scope

- [ ] E:\AI_projects\yeyu-api\backend\app\api\routes\catalog.py 已提供 GET /api/v1/catalog 和 GET /api/v1/catalog/{slug}。
- [ ] E:\AI_projects\yeyu-api\backend\app\services\catalog.py 已限制公开记录为 visibility=public 且 status 为 healthy 或 published，并会清洗敏感 metadata。
- [ ] E:\AI_projects\yeyu-api\backend\app\services\execution\registry.py 已将 time 与 uuid 绑定到 builtin-tools 白名单适配器。
- [ ] E:\AI_projects\yeyu-api\frontend\src\client\ 已有生成的 CatalogService、CatalogItem、CatalogPage、ApiDetail 类型；实现时复用，不手写重复的 HTTP 类型。
- [ ] 当前 E:\AI_projects\yeyu-api\frontend\src\routes\_layout\index.tsx 占用受保护根路径 /，必须迁移到 _layout/dashboard.tsx，否则无法新增公共 /。

---

## Task 1: Add Idempotent Public Catalog Seeds

**Files:**

- Create E:\AI_projects\yeyu-api\backend\app\catalog_seed.py
- Modify E:\AI_projects\yeyu-api\backend\app\initial_data.py
- Create E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py

### Implementation

- [x] 在测试中构造 SQLite 或项目现有测试 session，验证初次调用 seed_public_catalog(session) 会创建且只创建 time、uuid 两条 ApiDefinition。
- [x] 在测试中验证两次调用结果完全幂等，第二次不增加记录、不重置 updated_at、不覆盖管理员已经修改的 summary、status、examples 或 cache_rules。
- [x] 在测试中验证种子数据的 adapter_name 只能是 builtin-tools，visibility 为 public，status 为 published 或 healthy，auth_type 为 api_key，is_free 为真，路径分别为 /v1/tools/time 与 /v1/tools/uuid。
- [x] 在测试中验证示例请求不包含真实密钥，示例只出现 <YOUR_API_KEY> 占位符；验证 time 具有可选 timezone 参数，uuid 不允许参数。
- [x] 在 catalog_seed.py 暴露不可变的 PUBLIC_CATALOG_SEEDS 和 seed_public_catalog(session)，使用显式 slug 查询缺失记录后新增，不调用会覆盖已有字段的批量 upsert。
- [x] 为 time 和 uuid 填写面向开发者的中文 name、summary、category、method、path、parameters、response_schema、error_codes、examples、source_label、cache_rules；元数据必须与实际 builtin adapter 返回值一致。
- [x] 在 initial_data.init() 的现有 init_db(session) 之后调用 seed_public_catalog(session)，保留原有超级用户初始化行为。
- [x] 不在种子文件中读取环境变量中的密钥，不调用第三方网络，不写日志中的敏感信息。

### Verification

- [x] 使用项目 conda 环境 yeyu-api 执行：

~~~powershell
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q
~~~

- [x] 使用项目 conda 环境执行：

~~~powershell
conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app\catalog_seed.py E:\AI_projects\yeyu-api\backend\app\initial_data.py E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py
~~~

- [x] 记录 pytest 和 ruff 的真实输出；若数据库依赖导致环境阻塞，只记录阻塞原因，不将未运行结果标为通过。
- [x] 独立只读子代理检查种子幂等性、适配器字段一致性、敏感数据边界和测试充分性，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md。
- [x] 处理审查报告中的 Critical 或 Important 问题后重新运行上述测试，再创建提交 feat: seed public builtin catalog 并推送 origin/main。

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
- Modify E:\AI_projects\yeyu-api\frontend\package.json
- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx
- Create or modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
- Modify E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts

### Implementation

- [x] 先更新 Playwright 断言：匿名访问 / 不跳转 /login；匿名访问 /catalog 不跳转 /login；登录成功后的目标为 /dashboard；受保护的 /items 仍在未登录时跳转 /login。
- [x] 实现 PublicLayout、PublicHeader、PublicFooter，导航至少包含首页、API 目录、登录；移动端提供可访问的折叠菜单或等价的键盘可用导航；登录状态下显示控制台入口。
- [x] 将受保护根页面从 _layout/index.tsx 迁移为 _layout/dashboard.tsx，路由标题改为 Yeyu API 控制台，保留当前用户欢迎信息，不把公共首页内容复制到控制台。
- [x] 将 useAuth 登录成功跳转、GitHub callback 成功跳转和 login.tsx 的已登录重定向统一改为 /dashboard；登录失败、回调失败和登出行为保持现有语义。
- [x] 将侧边栏 Dashboard 链接改为 /dashboard，避免继续指向公共首页；更新 Logo 和 Footer，移除 FastAPI Template 品牌、链接和文案，替换为 Yeyu API 公益平台信息。
- [x] 让 E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx 使用 PublicLayout 作为公共首页入口，首页只渲染真实目录数据、搜索入口、公益说明和使用规范入口；数据加载失败时显示明确的错误状态，不伪造接口卡片。
- [x] 修改 index.css 建立设计变量：纸白背景、墨色正文、青绿色主色、浅青绿色表面、琥珀色警示色和可见焦点环；保留 Tailwind/shadcn 现有组件可用，不引入远程 CSS。
- [x] 保证公共壳层的 main、导航、按钮、表单控件有语义标签、键盘焦点、可读颜色和移动端溢出处理。

### Verification

- [x] 执行前端格式与类型构建：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
pnpm build
~~~

- [x] 执行只覆盖路由边界的 Playwright 测试：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec playwright test tests/public-catalog.spec.ts tests/login.spec.ts
~~~

- [x] 记录构建、Biome 和 Playwright 的实际结果；没有运行 Docker 依赖时标明具体阻塞。
- [x] 独立只读子代理检查路由树迁移是否完整、匿名/登录边界、键盘可用性、品牌残留和是否误触及旧项目，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-2-review.md。
- [x] 处理审查问题后重新做静态检查和构建尝试，创建提交 feat: split public and protected web shells 并推送 origin/main；修复后的 Playwright 因 Chromium 缺失保持未验证。

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
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CodeExample.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\index.css
- Modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts

### Implementation

- [ ] 在测试中覆盖目录页匿名可访问、搜索参数能反映到 URL、分类筛选能反映到 URL、空结果有明确状态、详情页展示 /v1/tools/time、GET、API Key 鉴权、参数、响应字段和错误码。
- [ ] 目录页通过生成的 CatalogService.getCatalog 和 React Query 获取分页数据，query、category、status 使用 TanStack Router search params 作为唯一可分享状态；输入搜索设置 300 至 500 毫秒防抖并避免逐键请求。
- [ ] 目录页首屏顺序固定为页面标题与搜索框、分类/状态筛选、真实目录卡片；卡片包含名称、中文简介、请求方法、路径、免费标记、健康/发布状态和更新时间，点击后进入 /catalog/:slug。
- [ ] 目录页只展示后端返回数据，不在前端硬编码候选接口；API 返回空、错误和加载状态分别使用可读的 Empty、Error、Skeleton 组件。
- [ ] 详情页通过生成的 CatalogService.getCatalogDetail({ path: { slug } }) 获取数据；展示鉴权说明、参数表、响应结构、错误码、缓存规则、来源标签和 curl、JavaScript、Python 示例。
- [ ] 代码示例只显示 <YOUR_API_KEY>，统一从当前域名拼接请求 URL，不保存或读取真实 API Key，不提供任意 URL 输入；复制按钮使用可访问名称并在成功后有非颜色反馈。
- [ ] 首页保持索引台视觉：上方以一句清晰定位和主搜索入口为主，下面展示由真实目录 API 返回的精选工具卡片、一个可直接跳转的 Quick Start 区块和公益/使用边界说明；不展示假统计。
- [ ] 公共导航在首页、目录页和详情页保持一致；目录页搜索框支持从首页带 query 参数跳转后继续搜索。
- [ ] 移动端将详情页的参数表、代码块和路径行处理为可横向滚动而不撑破页面；桌面端使用窄内容列、明显分隔线和稳定状态色。

### Verification

- [ ] 执行前端构建与静态检查：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
pnpm build
~~~

- [ ] 在项目 Docker Compose 测试环境可用时执行：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec playwright test tests/public-catalog.spec.ts
~~~

- [ ] 通过 API 测试确认种子后端实际提供目录数据：

~~~powershell
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py -q
~~~

- [ ] 使用真实浏览器尺寸至少检查 1280 像素桌面视口和 390 像素移动视口；记录页面 URL、公开/受保护结果、控制台错误和截图路径。截图若用于审查，只放在项目外部临时目录。
- [ ] 独立只读子代理检查 API client 使用、URL 状态同步、错误/空状态、示例密钥脱敏、移动端溢出、可访问性和视觉方案偏离，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-review.md。
- [ ] 处理审查问题后重跑构建、API 测试和浏览器测试，创建提交 feat: add public catalog and api detail pages 并推送 origin/main。

## Task 4: Whole-Phase Verification and Handoff

**Files:**

- Modify E:\AI_projects\yeyu-api\plans\task-7-public-catalog-ui.md
- Create E:\AI_projects\yeyu-api\plans\agent-reports\task-7-final-review.md
- Update E:\AI_projects\yeyu-api\.git\sdd\progress.md only if the subagent workflow has initialized this ledger

### Verification

- [ ] 检查工作树只包含本阶段预期文件，使用：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api'
git status --short
git diff --check
git diff --name-only
~~~

- [ ] 检查代码和文档没有凭据模式、真实密钥或不应出现的旧项目路径：

~~~powershell
rg -n --hidden --glob '!frontend/node_modules/**' --glob '!frontend/dist/**' --glob '!.git/**' 'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|ghp_[A-Za-z0-9]+|github.*secret|smtp.*password|DATABASE_PASSWORD|new\.api\.yeyubaka\.top|yeyubakahome_Web' E:\AI_projects\yeyu-api
~~~

- [ ] 使用项目 conda 环境运行后端语法与相关测试：

~~~powershell
conda run -n yeyu-api python -m compileall -q E:\AI_projects\yeyu-api\backend\app
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py -q
~~~

- [ ] 运行前端构建和本阶段 Playwright 测试；把 Docker、数据库、SMTP、GitHub OAuth 或外部服务器不可用项分成未验证/阻塞，不得写成通过。
- [ ] 让独立只读子代理对本阶段合并结果做一次整体审查，重点检查无意修改旧项目、公共访问边界、生成文件、密钥泄露、路径冲突和用户确认的视觉约束；报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-final-review.md。
- [ ] 处理整体审查的 Critical 和 Important 问题并复审；只在工作树清洁、验证证据已记录后创建提交 docs: record public catalog ui verification 并推送 origin/main。
- [ ] 将本计划中已真实完成的步骤勾选，将未运行的线上 DNS、HTTPS、SMTP、GitHub OAuth、移动真机和服务器部署项保持未勾选，并在交付说明中明确未验证原因。

## Execution and Review Protocol

- [ ] 执行前保存当前基线 SHA，并在 E:\AI_projects\yeyu-api\plans\agent-reports\ 为每个任务生成任务简报；实现子代理只能修改该任务的文件清单。
- [ ] 实现子代理必须在自己的任务结束时报告修改文件、测试命令及原始输出摘要、提交 SHA 和未解决风险；不得声称执行了未运行的命令。
- [ ] 审查子代理必须使用与实现子代理不同的新鲜上下文，只读检查，不修改工作树；审查输入包含任务简报、实现报告和相对基线的 diff。
- [ ] 审查结论为 Critical 或 Important 时，主代理负责最小修复、重新运行受影响测试并再次提交审查；Minor 问题记录处理决定。
- [ ] 每个任务审查通过后立即推送 origin/main；不创建或推送未知远程，不修改 DNS/Nginx/服务器。
- [ ] 最终交付只报告可由命令、提交、审查报告或浏览器日志支持的事实。
