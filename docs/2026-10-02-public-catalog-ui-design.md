# 公开目录与 A+B 首页设计说明

状态：方向已由用户确认为方案 B；本文写入后等待用户审阅，审阅通过后再生成实施计划。

项目根目录：`E:\AI_projects\yeyu-api`

## 1. 目标与边界

本阶段把现有模板首页改造成无需登录即可使用的 Yeyu API 公益目录闭环：用户访问 `/` 后可以搜索和浏览已经公开的自营工具接口，进入详情页阅读真实参数、响应、错误码和调用示例。已登录用户仍可以进入独立的 `/dashboard` 管理账号；浏览器登录状态不参与实际 `/api/v1/tools/*` 调用鉴权。

本阶段只公开已经实现且固定注册的 `time` 与 `uuid`。不新增第三方上游、不实现在线调试、不实现 API Key 管理界面、不实现内容试验池、不修改 DNS/Nginx/服务器。

## 2. 当前基线

只读检查确认：

- `E:\AI_projects\yeyu-api\backend\app\api\routes\catalog.py` 已提供公开列表和详情接口；服务层已经过滤 `visibility=public` 与 `status=healthy/published`。
- `E:\AI_projects\yeyu-api\frontend\src\client\` 已由 OpenAPI 生成 `CatalogService`、`CatalogItem`、`CatalogPage` 和 `ApiDetail` 类型。
- `E:\AI_projects\yeyu-api\backend\app\services\execution\registry.py` 只注册 `time`、`uuid`；`TimeAdapter` 只接受可验证的 `timezone`，`UuidAdapter` 不接受参数。
- `E:\AI_projects\yeyu-api\backend\app\initial_data.py` 当前只创建首个超级用户，没有幂等写入公开目录记录。
- `E:\AI_projects\yeyu-api\frontend\src\routes\_layout\index.tsx` 仍是受保护的模板 Dashboard，`E:\AI_projects\yeyu-api\frontend\src\components\Common\Logo.tsx` 和 Footer 仍显示 FastAPI 模板品牌。

## 3. 路由与兼容策略

采用公开站点与受保护控制台分离的方案：

| 路径 | 权限 | 用途 |
|---|---|---|
| `/` | 公开 | A+B 首页：搜索、少量推荐、公益说明、Quick Start |
| `/catalog` | 公开 | 完整目录、关键词搜索、分类筛选、状态和更新时间 |
| `/catalog/:slug` | 公开 | API 文档详情和代码示例 |
| `/dashboard` | 登录 | 原模板 Dashboard 的 Yeyu 控制台入口 |
| `/items`、`/settings`、`/admin` | 登录 | 保留现有受保护路由，继续挂在受保护布局下 |

`E:\AI_projects\yeyu-api\frontend\src\routes\_layout\index.tsx` 改为受保护的 `/dashboard` 子路由；`useAuth` 登录成功和登录页已登录重定向都改为 `/dashboard`。现有登录、登出、用户设置和管理员 E2E 断言同步更新，不能用公开首页绕过受保护布局。

公开页面使用新的轻量站点布局，不复用需要登录的 `AppSidebar`。页眉显示 Yeyu API 标识、目录入口、公益说明和登录/控制台入口；移动端使用折叠菜单，键盘焦点可见，所有导航均使用 TanStack Router 的类型安全链接。

## 4. 数据流与目录种子

前端只通过生成客户端访问现有公开接口：

1. 首页和目录页调用 `CatalogService.searchCatalog`，参数只使用 `query`、`category`、`status`、`page`、`page_size`。
2. 详情页调用 `CatalogService.getCatalogDetail`，按 slug 读取公开文档。
3. 页面不复制后端搜索规则，不读取 `provider_ref`，不接受任意 URL 或 adapter 名称。
4. 空结果、接口下线、网络错误和详情 404 都显示可行动的中文状态，不显示内部异常。

在 `E:\AI_projects\yeyu-api\backend\app\initial_data.py` 中加入幂等目录初始化，或抽取到职责单一的种子模块后由初始化入口调用。每条记录按 slug 查询后再创建/更新，重复执行不能产生重复数据，也不能覆盖管理员后来修改过的文档字段。初始记录必须与固定执行器一致：

- `time`：名称“时间戳与时区”、分类“开发工具”、路径 `/api/v1/tools/time`、GET、`api_key`、`builtin-tools`、`public + published`；参数只描述 `timezone`，默认 UTC，响应描述 `utc`、`unix_timestamp`、`timezone`、`local`。
- `uuid`：名称“UUID”、分类“开发工具”、路径 `/api/v1/tools/uuid`、GET、`api_key`、`builtin-tools`、`public + published`；参数为空，响应描述 `uuid` 与 `version=4`。

种子数据不伪造调用量、延迟或第三方来源；状态文案使用“自营工具 / 免费 / 已发布”等可由真实目录字段支持的内容。

## 5. A+B 视觉与内容系统

### A：索引台

- 背景使用低对比纸白和墨色文字，不使用大面积渐变、虚假统计或 SaaS 营销数字。
- 首屏主标题直接说明用途：“给学生和个人开发者的免费 API 工具箱”。
- 核心搜索框位于首屏主要视觉位置，placeholder 使用真实任务，例如“搜索时间戳、UUID、天气……”。
- 搜索结果卡片展示名称、简述、分类、`GET`、路径、免费标签、发布状态和更新时间；卡片整体可键盘聚焦并进入详情。

### B：开发者仪表盘

- 搜索区旁放一个窄幅 Quick Start 面板，以真实的 `/api/v1/tools/time` 和 `X-API-Key` 示例说明调用边界。
- 详情页采用“文档正文 + 请求摘要”双栏；窄屏改为单列，方法、路径、鉴权和参数保持在正文前部。
- 代码示例使用代码块复制按钮，示例中的 Key 使用 `<YOUR_API_KEY>` 占位符，仓库和页面绝不出现真实密钥。
- 状态使用少量语义色：已发布、试验中、不可用；本阶段公开页面只会出现已发布接口。

视觉 token 采用项目本地 CSS 变量，不新增远程字体或图片依赖：纸白 `#F4F3EE`、墨色 `#17211F`、青绿色主色 `#197C72`、浅青背景 `#DDEDE7`、警示色 `#B45309`。正文使用系统中文无衬线字体，路径/方法/代码使用等宽字体。唯一记忆点是“路径索引线”：卡片和详情页用细线把方法、路径、状态串成一条可扫描的开发者信息行。

## 6. 文件职责

- 创建 `E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx`：公开首页。
- 创建 `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`：目录搜索与筛选。
- 创建 `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx`：详情页。
- 创建 `E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\`：站点页眉、页脚、状态徽章、空状态和公共布局。
- 创建 `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\`：搜索框、筛选栏、卡片、详情文档和代码示例。
- 修改 `E:\AI_projects\yeyu-api\frontend\src\routes\_layout\index.tsx`、`E:\AI_projects\yeyu-api\frontend\src\routes\_layout.tsx`、`E:\AI_projects\yeyu-api\frontend\src\hooks\useAuth.ts`、`E:\AI_projects\yeyu-api\frontend\src\routes\login.tsx`、`E:\AI_projects\yeyu-api\frontend\src\components\Sidebar\AppSidebar.tsx`：完成 `/dashboard` 迁移。
- 修改 `E:\AI_projects\yeyu-api\frontend\src\components\Common\Logo.tsx`、`E:\AI_projects\yeyu-api\frontend\src\components\Common\Footer.tsx` 和 `E:\AI_projects\yeyu-api\frontend\src\index.css`：移除模板品牌，建立本地视觉 token。
- 修改 `E:\AI_projects\yeyu-api\backend\app\initial_data.py`，必要时创建 `E:\AI_projects\yeyu-api\backend\app\catalog_seed.py`：幂等写入两个固定目录记录。
- 修改 `E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts`、`E:\AI_projects\yeyu-api\frontend\tests\user-settings.spec.ts`；创建 `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts` 和必要的组件单测。
- `E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts` 只能由生成命令更新，不手工维护。

## 7. 安全、可访问性和错误状态

- 公开页面不把登录 Cookie 当作工具调用凭据；详情页只展示 `X-API-Key` 文档。
- 所有目录文本按 React 默认文本渲染，不使用未经清洗的 `dangerouslySetInnerHTML`。
- 搜索输入使用后端已有长度限制；前端不拼接 URL 上游地址、不生成代理请求。
- 复制按钮不记录完整 Key；代码示例只使用占位符。
- loading 使用骨架或明确的“正在读取目录”；空结果提供清除搜索操作；网络错误提供重试按钮；404 提供返回目录链接。
- 使用语义 HTML、`aria-label`、可见焦点、`prefers-reduced-motion`，并覆盖窄屏宽度。

## 8. 验收与测试边界

先写失败测试，再实现：

- 未登录访问 `/`、`/catalog`、`/catalog/time` 成功，不被重定向到 `/login`。
- 首页显示真实的“时间戳与时区”和“UUID”，不显示 FastAPI Template 文案或虚假统计。
- 搜索 `UUID` 只展示匹配目录；分类筛选和清除筛选可用；空结果和网络错误可恢复。
- 详情页展示 GET、路径、`X-API-Key`、参数、响应结构、错误码和 curl/JavaScript/Python 示例；不出现 `provider_ref`、Secret 或内部异常。
- 登录成功进入 `/dashboard`，现有 `/settings`、`/admin` 权限测试继续通过；退出后不能访问这些受保护路由。
- Chromium 与 mobile Chromium 覆盖公开首页、搜索、详情和登录迁移；前端 TypeScript 构建、Biome 检查和后端目录/初始化测试通过。
- 本阶段不把 `/health`、CI、构建或本地页面加载等同于线上验收；DNS、SMTP、GitHub OAuth 和服务器部署继续标记为未验证。

## 9. 不纳入本阶段的决定

- 不加入天气、新闻、热榜等第三方内容适配器。
- 不实现在线调试的 API Key 输入、调用历史或浏览器端 API 请求。
- 不实现 API Key 创建、撤销、轮换 UI；这些功能继续使用已完成的后端边界，另设用户中心任务。
- 不修改生产服务器、DNS、证书、Nginx、旧个人网站或 `new.api.yeyubaka.top`。
