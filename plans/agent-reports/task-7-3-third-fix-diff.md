# Review package: 9c901eb..6d3c1636fa48e60e9e9d3eda04b19c612861fac5

## Commits
6d3c163 fix: close remaining catalog review findings

## Files changed
 .../src/components/ApiCatalog/catalog-types.ts     |  15 ++-
 frontend/src/routes/catalog/index.tsx              |  24 ++++-
 frontend/tests/public-catalog.spec.ts              | 101 ++++++++++++++++++++-
 plans/agent-reports/task-7-3-report.md             |  29 ++++++
 4 files changed, 162 insertions(+), 7 deletions(-)

## Diff
diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
index 5e973cc..ed14c2e 100644
--- a/frontend/src/components/ApiCatalog/catalog-types.ts
+++ b/frontend/src/components/ApiCatalog/catalog-types.ts
@@ -2,20 +2,31 @@ import type { ApiDetail, CatalogItem } from "@/client"
 
 export type CatalogSearchParams = {
   query?: string
   category?: string
   status?: string
   page: number
 }
 
 export type CatalogMetadata = Record<string, unknown>
 
+export type CatalogFacetResult =
+  | {
+      items: CatalogItem[]
+      complete: true
+    }
+  | {
+      items: []
+      complete: false
+      reason: "page-limit"
+    }
+
 export const PUBLIC_API_BASE_URL = "https://api.yeyubaka.top"
 export const PUBLIC_API_AUTH_HEADER = "X-API-Key"
 
 const SENSITIVE_METADATA_KEY_PARTS = [
   "token",
   "secret",
   "password",
   "authorization",
   "cookie",
   "apikey",
@@ -40,21 +51,23 @@ function isSensitiveMetadataKey(key: string): boolean {
   return SENSITIVE_METADATA_KEY_PARTS.some((part) => normalized.includes(part))
 }
 
 export function normalizeSearchValue(value: unknown): string | undefined {
   if (typeof value !== "string") return undefined
   const normalized = value.trim()
   return normalized || undefined
 }
 
 export function normalizeSafeQueryKey(value: unknown): string | undefined {
-  return typeof value === "string" && SAFE_QUERY_KEY_PATTERN.test(value)
+  return typeof value === "string" &&
+    SAFE_QUERY_KEY_PATTERN.test(value) &&
+    !isSensitiveMetadataKey(value)
     ? value
     : undefined
 }
 
 export function normalizeSafeQueryValue(value: unknown): string | undefined {
   const text =
     typeof value === "string"
       ? value
       : typeof value === "number" && Number.isFinite(value)
         ? String(value)
diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
index ed1152a..fa2b395 100644
--- a/frontend/src/routes/catalog/index.tsx
+++ b/frontend/src/routes/catalog/index.tsx
@@ -6,48 +6,49 @@ import { type CatalogItem, type CatalogPage, CatalogService } from "@/client"
 import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
 import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
 import CatalogPagination from "@/components/ApiCatalog/CatalogPagination"
 import CatalogSearch from "@/components/ApiCatalog/CatalogSearch"
 import {
   CatalogEmptyState,
   CatalogErrorState,
   CatalogLoadingState,
 } from "@/components/ApiCatalog/CatalogStates"
 import {
+  type CatalogFacetResult,
   type CatalogSearchParams,
   normalizeSearchValue,
   parseCatalogSearch,
 } from "@/components/ApiCatalog/catalog-types"
 import PublicLayout from "@/components/PublicSite/PublicLayout"
 
 const FACET_PAGE_SIZE = 100
 const MAX_FACET_PAGES = 100
 
-async function fetchCatalogFacetItems(): Promise<CatalogItem[]> {
+async function fetchCatalogFacetItems(): Promise<CatalogFacetResult> {
   const items: CatalogItem[] = []
 
   for (let page = 1; page <= MAX_FACET_PAGES; page += 1) {
     const response = await CatalogService.searchCatalog({
       query: {
         page,
         page_size: FACET_PAGE_SIZE,
       },
     })
     const catalogPage = response.data
     items.push(...catalogPage.data)
 
     if (items.length >= catalogPage.count || catalogPage.data.length === 0) {
-      return items
+      return { items, complete: true }
     }
   }
 
-  return items
+  return { items: [], complete: false, reason: "page-limit" }
 }
 
 export const Route = createFileRoute("/catalog/")({
   validateSearch: (search): CatalogSearchParams => parseCatalogSearch(search),
   component: CatalogRoutePage,
   head: () => ({
     meta: [
       {
         title: "API 目录 - Yeyu API",
       },
@@ -97,28 +98,32 @@ function CatalogRoutePage() {
           category: search.category,
           status: search.status,
           page: search.page,
           page_size: 20,
         },
       })
       return response.data
     },
   })
 
-  const catalogFacetQuery = useQuery<CatalogItem[]>({
+  const catalogFacetQuery = useQuery<CatalogFacetResult>({
     queryKey: ["public-catalog-facets"],
     queryFn: fetchCatalogFacetItems,
     staleTime: 60_000,
   })
 
   const items = catalogQuery.data?.data ?? []
-  const filterItems = catalogFacetQuery.data ?? items
+  const filterItems = catalogFacetQuery.data
+    ? catalogFacetQuery.data.complete
+      ? catalogFacetQuery.data.items
+      : []
+    : items
   const updateFilter = (key: "category" | "status", value: string) => {
     void navigate({
       search: (previous) => ({
         ...previous,
         [key]: normalizeSearchValue(value),
         page: 1,
       }),
       replace: true,
     })
   }
@@ -135,20 +140,29 @@ function CatalogRoutePage() {
         </header>
 
         <CatalogSearch value={draftQuery} onChange={setDraftQuery} />
         <CatalogFilters
           items={filterItems}
           category={search.category}
           status={search.status}
           onCategoryChange={(value) => updateFilter("category", value)}
           onStatusChange={(value) => updateFilter("status", value)}
         />
+        {catalogFacetQuery.data && !catalogFacetQuery.data.complete ? (
+          <p
+            className="catalog-facets-incomplete"
+            data-testid="catalog-facets-incomplete"
+            role="status"
+          >
+            筛选选项未完整加载，已隐藏未确认的部分结果。
+          </p>
+        ) : null}
         {catalogFacetQuery.isError && !catalogQuery.isError ? (
           <CatalogErrorState onRetry={() => void catalogFacetQuery.refetch()} />
         ) : null}
 
         <section
           className="catalog-results"
           aria-labelledby="catalog-results-heading"
         >
           <div className="catalog-results-heading">
             <div>
diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
index 6f4968b..0c1c438 100644
--- a/frontend/tests/public-catalog.spec.ts
+++ b/frontend/tests/public-catalog.spec.ts
@@ -21,20 +21,34 @@ const uuidItem = {
   summary: "生成一个随机 UUID v4，不接受任何查询参数。",
   category: "tools",
   method: "GET",
   path: "/v1/tools/uuid",
   auth_type: "api_key",
   is_free: true,
   status: "published",
   updated_at: "2026-10-02T00:00:00Z",
 }
 
+const lateFacetItem = {
+  ...uuidItem,
+  slug: "late-facet",
+  name: "后分页接口",
+  category: "data",
+  status: "deprecated",
+  path: "/v1/data/late-facet",
+}
+
+const facetPageOneItems = Array.from({ length: 100 }, (_, index) => ({
+  ...timeItem,
+  slug: `time-${index}`,
+}))
+
 const timeDetail = {
   ...timeItem,
   auth: { type: "api_key", header: "X-API-Key" },
   parameters: [
     {
       name: "timezone",
       in: "query",
       required: false,
       description: "可选的 IANA 时区名称，省略时使用 UTC。",
       schema: {
@@ -66,20 +80,32 @@ const timeDetail = {
     {
       language: "curl",
       request:
         'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
     },
   ],
   source: "Yeyu API",
   cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
 }
 
+const sensitiveQueryParameters = [
+  { name: "apiKey", value: "1234567890" },
+  { name: "API_KEY", value: "1234567891" },
+  { name: "api-key", value: "1234567892" },
+  { name: "access_token", value: "1234567893" },
+  { name: "Access-Token", value: "1234567894" },
+  { name: "ACCESS.TOKEN", value: "1234567895" },
+  { name: "client_secret", value: "1234567896" },
+  { name: "Client-Secret", value: "1234567897" },
+  { name: "CLIENT.SECRET", value: "1234567898" },
+] as const
+
 const unsafeDetail = {
   ...timeDetail,
   auth: {
     type: "api_key",
     header: 'X-Evil-Header: "<NON_SECRET_TEST_VALUE>"',
   },
   path: "https://evil.example/redirect?token=<NON_SECRET_TEST_VALUE>",
   parameters: [
     ...timeDetail.parameters,
     {
@@ -136,20 +162,30 @@ const unsafeDetail = {
   cache_rules: {
     ...timeDetail.cache_rules,
     "provider-ref": "<NON_SECRET_TEST_VALUE>",
     safe: { nested_password: "<NON_SECRET_TEST_VALUE>" },
   },
 }
 
 const unsafeExamplesDetail = {
   ...unsafeDetail,
   path: "/v1/tools/time",
+  parameters: [
+    ...unsafeDetail.parameters,
+    ...sensitiveQueryParameters.map(({ name, value }) => ({
+      name,
+      in: "query",
+      required: false,
+      description: "敏感查询参数测试",
+      schema: { type: "string", default: value },
+    })),
+  ],
 }
 
 type CatalogPage = {
   data: (typeof timeItem)[]
   count: number
   page: number
   page_size: number
 }
 
 const catalogListUrl = /\/api\/v1\/catalog(?:\?.*)?$/
@@ -267,21 +303,21 @@ test("Catalog pagination preserves search filters and requests the selected page
     const url = new URL(route.request().url())
     const isFacetRequest =
       url.searchParams.get("page_size") === "100" &&
       !url.searchParams.has("query") &&
       !url.searchParams.has("category") &&
       !url.searchParams.has("status")
     if (isFacetRequest) {
       facetRequests.push(url)
       const pageNumber = Number(url.searchParams.get("page") ?? "1")
       const response: CatalogPage = {
-        data: pageNumber === 2 ? [uuidItem] : [timeItem],
+        data: pageNumber === 1 ? facetPageOneItems : [lateFacetItem],
         count: 101,
         page: pageNumber,
         page_size: 100,
       }
       await route.fulfill({
         status: 200,
         contentType: "application/json",
         body: JSON.stringify(response),
       })
       return
@@ -317,38 +353,97 @@ test("Catalog pagination preserves search filters and requests the selected page
   expect(
     facetRequests.every(
       (request) => request.searchParams.get("category") === null,
     ),
   ).toBe(true)
   expect(
     facetRequests.every(
       (request) => request.searchParams.get("status") === null,
     ),
   ).toBe(true)
+  await expect(page.getByLabel("分类").locator("option")).toContainText("data")
+  await expect(page.getByLabel("状态").locator("option")).toContainText(
+    "deprecated",
+  )
   await expect(page.getByRole("button", { name: "下一页" })).toBeEnabled()
 
   await page.getByRole("button", { name: "下一页" }).click()
   await expect(page).toHaveURL(
     /query=time.*category=tools.*status=published.*page=2/,
   )
   await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
 
   const secondRequest = catalogRequests.at(-1)
   expect(secondRequest?.searchParams.get("page")).toBe("2")
   expect(secondRequest?.searchParams.get("page_size")).toBe("20")
 
   await page.getByRole("button", { name: "上一页" }).click()
   await expect(page).toHaveURL(
     /query=time.*category=tools.*status=published.*page=1/,
   )
 })
 
+test("Catalog marks facet options incomplete after the page safety limit", async ({
+  page,
+}) => {
+  const facetRequests: URL[] = []
+  await page.route(catalogListUrl, async (route) => {
+    const url = new URL(route.request().url())
+    const isFacetRequest =
+      url.searchParams.get("page_size") === "100" &&
+      !url.searchParams.has("query") &&
+      !url.searchParams.has("category") &&
+      !url.searchParams.has("status")
+    if (isFacetRequest) {
+      facetRequests.push(url)
+      const pageNumber = Number(url.searchParams.get("page") ?? "1")
+      await route.fulfill({
+        status: 200,
+        contentType: "application/json",
+        body: JSON.stringify({
+          data: pageNumber === 100 ? [lateFacetItem] : [timeItem],
+          count: 10_001,
+          page: pageNumber,
+          page_size: 100,
+        }),
+      })
+      return
+    }
+
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify({
+        data: [timeItem],
+        count: 1,
+        page: 1,
+        page_size: 20,
+      }),
+    })
+  })
+
+  await page.goto("/catalog")
+
+  await expect(page.getByTestId("catalog-facets-incomplete")).toBeVisible()
+  await expect(
+    page.getByText("筛选选项未完整加载", { exact: false }),
+  ).toBeVisible()
+  await expect(page.getByLabel("分类").locator("option")).toHaveText([
+    "全部分类",
+  ])
+  await expect(page.getByLabel("状态").locator("option")).toHaveText([
+    "全部状态",
+  ])
+  await expect.poll(() => facetRequests.length).toBe(100)
+  expect(facetRequests.at(-1)?.searchParams.get("page")).toBe("100")
+})
+
 test("Catalog displays an explicit empty state for an empty result", async ({
   page,
 }) => {
   await mockCatalogApi(page)
   await page.goto("/catalog?query=missing")
 
   await expect(page.getByTestId("catalog-empty")).toBeVisible()
   await expect(page.getByText("没有找到匹配的公开接口")).toBeVisible()
   await expect(page.getByTestId("catalog-grid")).not.toBeVisible()
 })
@@ -419,20 +514,24 @@ test("Detail omits unsafe parameter examples from every code sample", async ({
   expect(renderedExamples).toContain("X-API-Key")
   expect(renderedExamples).toContain("<YOUR_API_KEY>")
   expect(renderedExamples).not.toContain('bad"name`$()')
   expect(renderedExamples).not.toContain(
     "https://evil.example/?next=<NON_SECRET_TEST_VALUE>",
   )
   expect(renderedExamples).not.toContain("$(whoami)")
   expect(renderedExamples).not.toContain("`id`")
   expect(renderedExamples).not.toContain("secret-token-<NON_SECRET_TEST_VALUE>")
   expect(renderedExamples).not.toContain("X-Evil-Header")
+  for (const { name, value } of sensitiveQueryParameters) {
+    expect(renderedExamples).not.toContain(name)
+    expect(renderedExamples).not.toContain(value)
+  }
 })
 
 test("Detail errors do not render stale detail data", async ({ page }) => {
   let detailRequestCount = 0
   await page.route(catalogTimeDetailUrl, async (route) => {
     detailRequestCount += 1
     if (detailRequestCount === 1) {
       await route.fulfill({
         status: 200,
         contentType: "application/json",
diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
index cf690f4..2cdb6de 100644
--- a/plans/agent-reports/task-7-3-report.md
+++ b/plans/agent-reports/task-7-3-report.md
@@ -226,10 +226,39 @@ exit 0
 pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
 exit 0
 Checked 4 files in 10ms. No fixes applied.
 
 git diff --check
 exit 0
 仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
 ```
 
 本轮没有运行 Playwright、前端 build、后端 pytest、路由生成、真实浏览器或线上验收；因此新增浏览器断言、TypeScript 完整检查、实际后端跨页响应和线上结果仍未验证。修复提交主题：`fix: harden catalog examples and filters`。
+
+## 11. 第二次复审 Important 收口（2026-10-02）
+
+本次仅修复 `task-7-3-second-fix-review.md` 指出的两个 Important；未修改 `frontend/src/routeTree.gen.ts`、认证/公共壳层、后端、线上服务、DNS、Nginx 或凭据。
+
+### 11.1 敏感 query 参数名和值
+
+- `normalizeSafeQueryKey` 现在在格式校验后复用统一的敏感字段规范化判定；`apiKey`、`API_KEY`、`api-key`、`access_token`、`Access-Token`、`ACCESS.TOKEN`、`client_secret`、`Client-Secret`、`CLIENT.SECRET` 等变体不会进入示例。
+- 回归夹具为这些敏感名称提供仅由合法字符组成的数值，断言三种代码示例均不包含名称或值；固定认证头仍为 `X-API-Key: <YOUR_API_KEY>`，既有内部路径和外部 URL 防护保持不变。
+
+### 11.2 facets 上限不完整状态
+
+- 新增 `CatalogFacetResult` 完成度类型；达到 100 页上限时返回 `complete: false`、`reason: "page-limit"`，并丢弃部分 items。
+- 页面显示 `catalog-facets-incomplete` 状态，且不会把被截断的部分结果传给 `CatalogFilters`；只有按 `count` 或空页停止时才使用已收集 facet。
+- 回归夹具第 1 页返回 100 条、第 2 页返回唯一 `data`/`deprecated` 项并断言其进入筛选选项；另以 `count=10001` 覆盖请求到第 100 页后的显式不完整状态及空筛选选项。
+
+### 11.3 本次真实静态验证
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+exit 0
+Checked 3 files in 12ms. No fixes applied.
+
+git diff --check
+exit 0
+仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
+```
+
+本次没有运行 Playwright、前端 build、后端测试、路由生成、TypeScript 完整检查或线上验收；因此新增浏览器回归断言和完整类型/运行时行为仍未验证。
