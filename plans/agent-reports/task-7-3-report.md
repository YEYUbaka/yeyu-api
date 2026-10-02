# Task 3：公共目录与 API 详情页实现报告

日期：2026-10-02
项目：`E:\AI_projects\yeyu-api`
实现提交：`c13adce`

## 1. 实现范围

本次完成公共目录从占位页到真实搜索优先目录，以及公开 API 详情页：

- 目录页通过生成的 `CatalogService.searchCatalog` 和 React Query 请求后端公开目录；只渲染 API 返回的 `CatalogItem`。
- `query` 使用 400ms 防抖同步到 TanStack Router search params；`category`、`status` 立即同步 URL，并作为 React Query key 的一部分。
- 卡片展示名称、简介、方法、路径、免费标记、后端状态和更新时间，并链接到 `/catalog/:slug`。
- 分别实现加载、错误、空结果状态；空结果不创建前端候选卡片。
- 新增 `/catalog/$slug` 详情路由，使用 `CatalogService.getCatalogDetail({ path: { slug } })`。
- 详情展示 API Key 鉴权、参数表、响应字段和 schema、错误码、缓存规则、来源，以及 curl、JavaScript、Python 示例。
- 所有示例只使用 `<YOUR_API_KEY>`；JavaScript 使用当前页面 origin，curl/Python 使用正式 API 域名；未读取 localStorage、Cookie 或真实 API Key。
- 首页预览继续使用真实目录 API，并补充详情链接、真实状态/更新时间和搜索跳转入口。
- 公共导航改为 TanStack Router 链接；详情路径、表格和代码块在窄视口使用滚动/换行边界。
- 未修改 `frontend/src/routeTree.gen.ts`，未修改 dashboard 保护或认证逻辑，未实现在线调试和 API Key 管理 UI。

## 2. 修改文件

- `frontend/src/components/ApiCatalog/catalog-types.ts`
- `frontend/src/components/ApiCatalog/CatalogSearch.tsx`
- `frontend/src/components/ApiCatalog/CatalogFilters.tsx`
- `frontend/src/components/ApiCatalog/CatalogCard.tsx`
- `frontend/src/components/ApiCatalog/CatalogGrid.tsx`
- `frontend/src/components/ApiCatalog/CatalogStates.tsx`
- `frontend/src/components/ApiCatalog/ApiDetailView.tsx`
- `frontend/src/components/ApiCatalog/CodeExample.tsx`
- `frontend/src/routes/catalog/index.tsx`
- `frontend/src/routes/catalog/$slug.tsx`
- `frontend/src/routes/index.tsx`
- `frontend/src/components/PublicSite/PublicHeader.tsx`
- `frontend/src/components/PublicSite/PublicFooter.tsx`
- `frontend/src/index.css`
- `frontend/tests/public-catalog.spec.ts`

任务简报 `plans/agent-reports/task-7-3-brief.md` 是用户提供的未跟踪文件，本次未修改、未提交。

## 3. TDD RED/GREEN 证据

### RED

先更新了 `frontend/tests/public-catalog.spec.ts`，覆盖：匿名目录、搜索参数 URL 同步、防抖、分类/状态筛选 URL、空结果、`/catalog/time`、`/v1/tools/time`、GET、API Key、`timezone`、响应字段、错误码、三种代码示例和复制反馈。

真实命令与结果：

```text
pnpm exec playwright test tests/public-catalog.spec.ts
exit 1
Error: Environment variable FIRST_SUPERUSER is undefined
```

仅在进程内注入非真实测试值后重试：

```text
$env:FIRST_SUPERUSER='<NON_SECRET_TEST_EMAIL>'; $env:FIRST_SUPERUSER_PASSWORD='<NON_SECRET_TEST_VALUE>'; pnpm exec playwright test tests/public-catalog.spec.ts
exit 1
browserType.launch: Executable doesn't exist ... chrome-headless-shell.exe
1 failed [setup] auth.setup.ts; 5 did not run
```

随后执行了依赖安装：

```text
pnpm exec playwright install chromium
exit 0
Chrome for Testing and Chrome Headless Shell downloaded to the Playwright user cache
```

安装后再次以同样的非真实进程值运行：

```text
exit 1
Test timeout of 30000ms exceeded
at tests/auth.setup.ts:8:41, waiting for getByTestId('email-input')
1 failed [setup] auth.setup.ts; 5 did not run
```

因此 RED 阶段有测试收集/环境阻塞证据，但目标目录断言没有进入浏览器执行。

### GREEN

已完成对应静态实现，并执行 Biome 作为快速静态门禁；没有运行 Playwright/build，故不能宣称浏览器 GREEN、类型检查 GREEN 或产品验收 GREEN。

## 4. 静态验证

首次对 `src tests` 执行 Biome 的真实结果：

```text
exit 1
Checked 73 files in 46ms. No fixes applied.
Found 14 errors.
Found 2 warnings.
```

错误集中在新增 JSX 格式、无效 div `aria-label`、搜索容器 role，以及 CSS 特异性顺序。修正后只对本次改动的 15 个文件执行：

```text
pnpm exec biome check --write --no-errors-on-unmatched --files-ignore-unknown=true <15 absolute paths>
exit 0
Checked 15 files in 18ms. Fixed 9 files.

pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true <15 absolute paths>
exit 0
Checked 15 files in 14ms. No fixes applied.
```

另执行 `git diff --check`，未发现空白错误；Git 仅提示 Windows 工作树的 LF/CRLF 转换警告。

## 5. 未验证阻塞与边界

- Playwright 被既有 `auth.setup.ts` 的认证 setup 阻塞；缺少浏览器已安装，但 setup 后续仍在登录页 `email-input` 等待超时。未把 setup 失败算作目录测试通过。
- 按用户本次要求未运行 `pnpm build`，未运行后端 pytest，也未做真实浏览器桌面/移动截图验收。
- 未运行 Vite 官方路由生成链，因此 `routeTree.gen.ts` 仍保持未手改状态；新增路由是否被生成链和 TypeScript 完整接纳需要后续 build/开发服务器验证。
- 未执行线上验收、DNS/Nginx/SMTP/GitHub OAuth 或生产部署；没有触碰旧项目、线上服务和凭据。

## 6. Self-review

- [x] 目录卡片由 `CatalogService` 返回数据驱动，无硬编码接口卡片。
- [x] 目录搜索和筛选状态可分享，搜索防抖为 400ms。
- [x] 详情页使用生成 client 的 path slug 形态，展示真实 schema/参数/错误/缓存/来源字段。
- [x] 示例只包含 `<YOUR_API_KEY>`，没有新增浏览器凭据读取或在线调用控件。
- [x] 复制按钮有可访问名称，成功状态有文字和图标反馈。
- [x] 移动端表格、路径和代码块设置横向滚动边界。
- [x] Biome 最终对本次 15 个文件通过。
- [ ] Playwright、build、pytest 和真实浏览器验收：受用户要求/现有 setup 阻塞，未验证。

## 7. 提交

实现代码提交主题：`feat: add public catalog and api detail pages`

提交 SHA：`c13adce`（实现提交；报告随后单独提交）。

## 8. 独立审查 Important 修复（2026-10-02）

本次修复范围仅覆盖独立审查报告中的五个 Important，不修改任务 2 认证/公共壳层，不手改 `frontend/src/routeTree.gen.ts`，不扩展在线调试、API Key 管理或第三方接口。

### 8.1 示例 URL/path 边界

- `frontend/src/components/ApiCatalog/catalog-types.ts` 新增 `normalizeInternalApiPath` 和 `buildPublicApiUrl`。
- 只接受经过 trim 的单斜杠内部绝对路径，拒绝 `http(s)`、`//`、反斜杠、query/hash、百分号和 `..`。
- `ApiDetailView` 的 curl、JavaScript、Python 示例统一使用受控路径和 `https://api.yeyubaka.top`；非法路径显示“路径不可用”和不可执行的占位说明，不回显后端任意绝对 URL。
- 保留 `<YOUR_API_KEY>`，未增加任意 URL 输入或凭据读取。

### 8.2 metadata 防御性脱敏

- `sanitizeMetadata` 递归删除规范化后包含 `token`、`secret`、`password`、`authorization`、`cookie`、`apikey`、`credential`、`privatekey`、`providerref` 的大小写/下划线/连字符变体。
- `formatMetadata` 在 JSON 格式化前过滤；响应 schema、参数、错误和 cache rules 的展示均使用过滤后的对象，敏感值不替换回显。

### 8.3 目录分页

- `CatalogSearchParams` 新增合法正整数 `page`，缺失或非法值默认为 1。
- 目录 query key 和 `CatalogService.searchCatalog` 请求均使用 `page` 与 `page_size: 20`。
- 新增单一职责文件 `frontend/src/components/ApiCatalog/CatalogPagination.tsx`，提供可访问的上一页/下一页、当前页和总页数；搜索、分类、状态变化会重置 `page=1`，分页导航保留其他 search params。
- 增加分页 URL、请求 query 和上一页行为的 route-mock 回归断言。

### 8.4 详情错误状态互斥

- `frontend/src/routes/catalog/$slug.tsx` 改为 loading/error/success 三选一分支；`isError` 时不再渲染 React Query 保留的旧 detail。
- 增加“先成功、导航返回后详情请求失败”的 stale detail 回归断言。

### 8.5 Playwright mock 匹配可靠性

- `frontend/tests/public-catalog.spec.ts` 将宽泛 `**/api/v1/catalog*` 改为分别匹配列表 URL 和 `/api/v1/catalog/time` 详情 URL 的正则，并允许 query string。
- 列表和详情 route mock 不会再把详情请求误判为列表请求，也不会意外访问真实后端。

## 9. 本次真实验证结果

按用户要求没有运行长时间 Playwright、前端 build、后端 pytest、路由生成或线上验收。

先写测试后的短静态检查：

```text
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
exit 1
原因：Biome 仅报告新增 expect.poll 的格式问题，未修改文件。
```

修复格式并完成实现后的静态检查：

```text
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx E:\AI_projects\yeyu-api\frontend\src\index.css E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
exit 0
Checked 7 files in 12ms. No fixes applied.

git diff --check
exit 0
仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
```

### 未验证项

- 本次新增/强化的 Playwright 行为测试未运行，因此不能宣称浏览器测试通过。
- build、TypeScript 完整检查、后端接口实际分页/脱敏响应、真实浏览器尺寸验收和线上验收仍未验证。
- 原有 Playwright `auth.setup.ts` 阻塞证据仍以本报告第 5 节为准；本次没有重试，也没有触碰认证配置或真实凭据。

修复提交主题：`fix: close catalog review findings`

## 10. 第二轮独立复审 Important 修复（2026-10-02）

本轮只处理最新复审报告中的两个 Important，不修改任务 2、`frontend/src/routeTree.gen.ts`、后端、线上服务、DNS、Nginx 或真实凭据。

### 10.1 参数示例值与认证头安全边界

- `frontend/src/components/ApiCatalog/catalog-types.ts` 新增纯函数 `normalizeSafeQueryKey` 与 `normalizeSafeQueryValue`。
- 参数名只接受以 ASCII 字母开头、长度受限且仅含字母数字、点、下划线和连字符的 query key；其他名称不进入代码示例，详情参数表也使用安全占位名称。
- 参数值只接受严格字符 allowlist；拒绝空白、引号、反引号、shell 元字符、换行、百分号、query/hash、反斜杠、scheme/外部 URL、敏感词和 JWT-like 值。非字符串只接受有限的数字/布尔值转换。
- `schema.examples` 会按顺序寻找第一个安全值，再考虑 `default`；恶意首项不会阻断后续合法值，因此 `Asia/Shanghai` 仍可生成。
- 认证头不再读取目录 metadata，示例与鉴权说明固定使用 `X-API-Key`；curl 的 URL、header 和 query 参数使用单引号包裹并转义单引号，同时保留 `<YOUR_API_KEY>` 占位符。
- `public-catalog.spec.ts` 的 unsafe detail 增加恶意参数名、外部 URL、空白、引号、shell 字符、换行、百分号、query/hash、反斜杠、敏感默认值和恶意认证头；新增安全路径场景，断言三种代码示例均不包含这些值，并断言合法 `Asia/Shanghai` 和 `X-API-Key` 仍存在。

### 10.2 跨页真实 facets

- `frontend/src/routes/catalog/index.tsx` 增加独立且缓存的公开目录 facets 查询，固定使用 `CatalogService.searchCatalog` 的无筛选请求、`page_size=100` 和 `staleTime=60_000`。
- 查询按每个响应的 `count` 逐页读取，最多 100 页；达到 count 或空页即停止，避免不受控资源消耗。
- `CatalogFilters` 改用完整已获取的真实 `CatalogItem[]` 计算分类/状态，并始终保留当前 URL 选择；主目录查询仍保留原有 query/category/status/page 和分页行为，facets 请求不携带这些筛选参数。
- facets 请求失败时回退当前页真实 items，并显示现有 `CatalogErrorState`；没有新增后端接口、任意 URL、秘密或硬编码候选项。
- 分页 route mock 返回 count=101，断言独立 facets 请求会请求 page=2/page_size=100，且不带 query、category、status。

### 10.3 本轮真实验证

```text
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
exit 0
Checked 4 files in 10ms. No fixes applied.

git diff --check
exit 0
仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
```

本轮没有运行 Playwright、前端 build、后端 pytest、路由生成、真实浏览器或线上验收；因此新增浏览器断言、TypeScript 完整检查、实际后端跨页响应和线上结果仍未验证。修复提交主题：`fix: harden catalog examples and filters`。

## 11. 第二次复审 Important 收口（2026-10-02）

本次仅修复 `task-7-3-second-fix-review.md` 指出的两个 Important；未修改 `frontend/src/routeTree.gen.ts`、认证/公共壳层、后端、线上服务、DNS、Nginx 或凭据。

### 11.1 敏感 query 参数名和值

- `normalizeSafeQueryKey` 现在在格式校验后复用统一的敏感字段规范化判定；`apiKey`、`API_KEY`、`api-key`、`access_token`、`Access-Token`、`ACCESS.TOKEN`、`client_secret`、`Client-Secret`、`CLIENT.SECRET` 等变体不会进入示例。
- 回归夹具为这些敏感名称提供仅由合法字符组成的数值，断言三种代码示例均不包含名称或值；固定认证头仍为 `X-API-Key: <YOUR_API_KEY>`，既有内部路径和外部 URL 防护保持不变。

### 11.2 facets 上限不完整状态

- 新增 `CatalogFacetResult` 完成度类型；达到 100 页上限时返回 `complete: false`、`reason: "page-limit"`，并丢弃部分 items。
- 页面显示 `catalog-facets-incomplete` 状态，且不会把被截断的部分结果传给 `CatalogFilters`；只有按 `count` 或空页停止时才使用已收集 facet。
- 回归夹具第 1 页返回 100 条、第 2 页返回唯一 `data`/`deprecated` 项并断言其进入筛选选项；另以 `count=10001` 覆盖请求到第 100 页后的显式不完整状态及空筛选选项。

### 11.3 本次真实静态验证

```text
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
exit 0
Checked 3 files in 12ms. No fixes applied.

git diff --check
exit 0
仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
```

本次没有运行 Playwright、前端 build、后端测试、路由生成、TypeScript 完整检查或线上验收；因此新增浏览器回归断言和完整类型/运行时行为仍未验证。
