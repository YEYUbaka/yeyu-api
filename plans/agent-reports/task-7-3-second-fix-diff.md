# Review package: 04fcbd4..9c901eb

## Commits
9c901eb fix: harden catalog examples and filters

## Files changed
 .../src/components/ApiCatalog/ApiDetailView.tsx    |  54 +++++++----
 .../src/components/ApiCatalog/catalog-types.ts     |  39 ++++++++
 frontend/src/routes/catalog/index.tsx              |  38 +++++++-
 frontend/tests/public-catalog.spec.ts              | 103 ++++++++++++++++++++-
 plans/agent-reports/task-7-3-report.md             |  35 +++++++
 5 files changed, 246 insertions(+), 23 deletions(-)

## Diff
diff --git a/frontend/src/components/ApiCatalog/ApiDetailView.tsx b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
index 7c7f036..a650887 100644
--- a/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+++ b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
@@ -3,95 +3,114 @@ import { Link } from "@tanstack/react-router"
 import type { ApiDetail } from "@/client"
 
 import CodeExample from "./CodeExample"
 import {
   asRecord,
   asText,
   buildPublicApiUrl,
   formatMetadata,
   formatUpdatedAt,
   normalizeInternalApiPath,
+  normalizeSafeQueryKey,
+  normalizeSafeQueryValue,
+  PUBLIC_API_AUTH_HEADER,
   PUBLIC_API_BASE_URL,
   responseProperties,
   sanitizeMetadata,
 } from "./catalog-types"
 
 type QueryExample = {
   name: string
   value: string
 }
 
 function parameterExamples(detail: ApiDetail): QueryExample[] {
   return detail.parameters.flatMap((parameter) => {
     const safeParameter = asRecord(sanitizeMetadata(parameter))
     if (!safeParameter || asText(safeParameter.in, "") !== "query") {
       return []
     }
 
-    const name = asText(safeParameter.name, "")
+    const name = normalizeSafeQueryKey(safeParameter.name)
     if (!name) return []
 
     const schema = asRecord(safeParameter.schema)
-    const examples = schema?.examples
-    const example = Array.isArray(examples) ? examples[0] : undefined
-    const value = asText(example ?? schema?.default, "value")
+    const candidates = [
+      ...(Array.isArray(schema?.examples) ? schema.examples : []),
+      schema?.default,
+    ]
+    const value = candidates
+      .map((candidate) => normalizeSafeQueryValue(candidate))
+      .find((candidate): candidate is string => candidate !== undefined)
+    if (!value) return []
+
     return [{ name, value }]
   })
 }
 
-function buildCodeExamples(detail: ApiDetail, authHeader: string) {
-  const method = detail.method.toUpperCase()
+function quoteCurlArgument(value: string): string {
+  return `'${value.replaceAll("'", "'\\''")}'`
+}
+
+function buildCodeExamples(detail: ApiDetail) {
+  const candidateMethod = detail.method.toUpperCase()
+  const method = /^[A-Z]{1,16}$/.test(candidateMethod) ? candidateMethod : "GET"
   const queryParameters = parameterExamples(detail)
   const path = normalizeInternalApiPath(detail.path)
   const absoluteUrl = buildPublicApiUrl(path)
   if (!path || !absoluteUrl) {
     const unavailable = "无法生成示例：目录路径不可用。"
     return {
       curl: unavailable,
       javascript: unavailable,
       python: unavailable,
     }
   }
 
   const curlStart =
     method === "GET"
-      ? `curl -G "${absoluteUrl}"`
-      : `curl -X ${method} "${absoluteUrl}"`
-  const curlLines = [curlStart, `  -H "${authHeader}: <YOUR_API_KEY>"`]
+      ? `curl -G ${quoteCurlArgument(absoluteUrl)}`
+      : `curl -X ${method} ${quoteCurlArgument(absoluteUrl)}`
+  const curlLines = [
+    curlStart,
+    `  -H ${quoteCurlArgument(`${PUBLIC_API_AUTH_HEADER}: <YOUR_API_KEY>`)}`,
+  ]
   for (const parameter of queryParameters) {
-    curlLines.push(`  --data-urlencode "${parameter.name}=${parameter.value}"`)
+    curlLines.push(
+      `  --data-urlencode ${quoteCurlArgument(`${parameter.name}=${parameter.value}`)}`,
+    )
   }
 
   const javascriptLines = [
     `const endpoint = new URL(${JSON.stringify(path)}, ${JSON.stringify(PUBLIC_API_BASE_URL)});`,
     ...queryParameters.map(
       (parameter) =>
         `endpoint.searchParams.set(${JSON.stringify(parameter.name)}, ${JSON.stringify(parameter.value)});`,
     ),
     "",
     "const response = await fetch(endpoint, {",
     `  method: ${JSON.stringify(method)},`,
     "  headers: {",
-    `    ${JSON.stringify(authHeader)}: "<YOUR_API_KEY>",`,
+    `    ${JSON.stringify(PUBLIC_API_AUTH_HEADER)}: "<YOUR_API_KEY>",`,
     "  },",
     "});",
     "const data = await response.json();",
     "console.log(data);",
   ]
 
   const pythonLines = [
     "import requests",
     "",
     "response = requests.request(",
     `    ${JSON.stringify(method)},`,
     `    ${JSON.stringify(absoluteUrl)},`,
-    `    headers={${JSON.stringify(authHeader)}: "<YOUR_API_KEY>"},`,
+    `    headers={${JSON.stringify(PUBLIC_API_AUTH_HEADER)}: "<YOUR_API_KEY>"},`,
     ...(queryParameters.length
       ? [
           `    params=${JSON.stringify(Object.fromEntries(queryParameters.map((parameter) => [parameter.name, parameter.value])))},`,
         ]
       : []),
     "    timeout=10,",
     ")",
     "response.raise_for_status()",
     "print(response.json())",
   ]
@@ -107,22 +126,22 @@ function readableCacheKey(key: string) {
   return key
     .replaceAll("_", " ")
     .replace(/\b\w/g, (character) => character.toUpperCase())
 }
 
 interface ApiDetailViewProps {
   detail: ApiDetail
 }
 
 export function ApiDetailView({ detail }: ApiDetailViewProps) {
-  const authHeader = detail.auth.header ?? "X-API-Key"
-  const examples = buildCodeExamples(detail, authHeader)
+  const authHeader = PUBLIC_API_AUTH_HEADER
+  const examples = buildCodeExamples(detail)
   const responseFields = responseProperties(detail)
   const safePath = normalizeInternalApiPath(detail.path)
   const safeCacheRules = asRecord(sanitizeMetadata(detail.cache_rules)) ?? {}
   const cacheEntries = Object.entries(safeCacheRules)
 
   return (
     <div className="api-detail-page">
       <div className="api-detail-breadcrumbs">
         <Link to="/catalog" className="public-text-link">
           ← 返回公开目录
@@ -191,24 +210,23 @@ export function ApiDetailView({ detail }: ApiDetailViewProps) {
                       <th scope="col">位置</th>
                       <th scope="col">必填</th>
                       <th scope="col">类型 / 说明</th>
                     </tr>
                   </thead>
                   <tbody>
                     {detail.parameters.map((parameter, index) => {
                       const safeParameter =
                         asRecord(sanitizeMetadata(parameter)) ?? {}
                       const schema = asRecord(safeParameter.schema)
-                      const name = asText(
-                        safeParameter.name,
-                        `参数 ${index + 1}`,
-                      )
+                      const name =
+                        normalizeSafeQueryKey(safeParameter.name) ??
+                        `参数 ${index + 1}`
                       const schemaText = asText(schema?.type, "—")
                       const description = asText(safeParameter.description, "")
                       return (
                         <tr
                           key={`${name}-${asText(safeParameter.in, "unknown")}-${index}`}
                         >
                           <th scope="row">
                             <code>{name}</code>
                           </th>
                           <td>{asText(safeParameter.in)}</td>
diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
index 248fd59..5e973cc 100644
--- a/frontend/src/components/ApiCatalog/catalog-types.ts
+++ b/frontend/src/components/ApiCatalog/catalog-types.ts
@@ -3,48 +3,87 @@ import type { ApiDetail, CatalogItem } from "@/client"
 export type CatalogSearchParams = {
   query?: string
   category?: string
   status?: string
   page: number
 }
 
 export type CatalogMetadata = Record<string, unknown>
 
 export const PUBLIC_API_BASE_URL = "https://api.yeyubaka.top"
+export const PUBLIC_API_AUTH_HEADER = "X-API-Key"
 
 const SENSITIVE_METADATA_KEY_PARTS = [
   "token",
   "secret",
   "password",
   "authorization",
   "cookie",
   "apikey",
   "credential",
   "privatekey",
   "providerref",
 ]
+const SAFE_QUERY_KEY_PATTERN = /^[A-Za-z][A-Za-z0-9_.-]{0,63}$/
+const SAFE_QUERY_VALUE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/+:-]{0,127}$/
+const QUERY_VALUE_SCHEME_PATTERN = /^[A-Za-z][A-Za-z0-9+.-]*:/
+const SENSITIVE_QUERY_VALUE_PATTERN =
+  /(token|secret|password|authorization|cookie|api[-_]?key|credential|private[-_]?key|bearer)/i
+const JWT_LIKE_PATTERN =
+  /^[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}$/
 
 function normalizedMetadataKey(key: string): string {
   return key.toLowerCase().replace(/[^a-z0-9]/g, "")
 }
 
 function isSensitiveMetadataKey(key: string): boolean {
   const normalized = normalizedMetadataKey(key)
   return SENSITIVE_METADATA_KEY_PARTS.some((part) => normalized.includes(part))
 }
 
 export function normalizeSearchValue(value: unknown): string | undefined {
   if (typeof value !== "string") return undefined
   const normalized = value.trim()
   return normalized || undefined
 }
 
+export function normalizeSafeQueryKey(value: unknown): string | undefined {
+  return typeof value === "string" && SAFE_QUERY_KEY_PATTERN.test(value)
+    ? value
+    : undefined
+}
+
+export function normalizeSafeQueryValue(value: unknown): string | undefined {
+  const text =
+    typeof value === "string"
+      ? value
+      : typeof value === "number" && Number.isFinite(value)
+        ? String(value)
+        : typeof value === "boolean"
+          ? String(value)
+          : undefined
+
+  if (
+    !text ||
+    text !== text.trim() ||
+    !SAFE_QUERY_VALUE_PATTERN.test(text) ||
+    text.includes("://") ||
+    QUERY_VALUE_SCHEME_PATTERN.test(text) ||
+    SENSITIVE_QUERY_VALUE_PATTERN.test(text) ||
+    JWT_LIKE_PATTERN.test(text)
+  ) {
+    return undefined
+  }
+
+  return text
+}
+
 export function normalizePage(value: unknown): number {
   const page =
     typeof value === "number"
       ? value
       : typeof value === "string" && value.trim()
         ? Number(value)
         : Number.NaN
 
   return Number.isSafeInteger(page) && page > 0 ? page : 1
 }
diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
index 9ad8056..ed1152a 100644
--- a/frontend/src/routes/catalog/index.tsx
+++ b/frontend/src/routes/catalog/index.tsx
@@ -1,31 +1,55 @@
 import { useQuery } from "@tanstack/react-query"
 import { createFileRoute } from "@tanstack/react-router"
 import { useEffect, useState } from "react"
 
-import { type CatalogPage, CatalogService } from "@/client"
+import { type CatalogItem, type CatalogPage, CatalogService } from "@/client"
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
   type CatalogSearchParams,
   normalizeSearchValue,
   parseCatalogSearch,
 } from "@/components/ApiCatalog/catalog-types"
 import PublicLayout from "@/components/PublicSite/PublicLayout"
 
+const FACET_PAGE_SIZE = 100
+const MAX_FACET_PAGES = 100
+
+async function fetchCatalogFacetItems(): Promise<CatalogItem[]> {
+  const items: CatalogItem[] = []
+
+  for (let page = 1; page <= MAX_FACET_PAGES; page += 1) {
+    const response = await CatalogService.searchCatalog({
+      query: {
+        page,
+        page_size: FACET_PAGE_SIZE,
+      },
+    })
+    const catalogPage = response.data
+    items.push(...catalogPage.data)
+
+    if (items.length >= catalogPage.count || catalogPage.data.length === 0) {
+      return items
+    }
+  }
+
+  return items
+}
+
 export const Route = createFileRoute("/catalog/")({
   validateSearch: (search): CatalogSearchParams => parseCatalogSearch(search),
   component: CatalogRoutePage,
   head: () => ({
     meta: [
       {
         title: "API 目录 - Yeyu API",
       },
     ],
   }),
@@ -73,21 +97,28 @@ function CatalogRoutePage() {
           category: search.category,
           status: search.status,
           page: search.page,
           page_size: 20,
         },
       })
       return response.data
     },
   })
 
+  const catalogFacetQuery = useQuery<CatalogItem[]>({
+    queryKey: ["public-catalog-facets"],
+    queryFn: fetchCatalogFacetItems,
+    staleTime: 60_000,
+  })
+
   const items = catalogQuery.data?.data ?? []
+  const filterItems = catalogFacetQuery.data ?? items
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
@@ -98,26 +129,29 @@ function CatalogRoutePage() {
         <header className="catalog-page-header">
           <p className="public-eyebrow">公开目录 / REAL DATA</p>
           <h1 className="catalog-page-title">API 目录</h1>
           <p className="catalog-page-lede">
             只展示后端公开、健康或已发布的真实接口。先搜索，再阅读完整调用契约。
           </p>
         </header>
 
         <CatalogSearch value={draftQuery} onChange={setDraftQuery} />
         <CatalogFilters
-          items={items}
+          items={filterItems}
           category={search.category}
           status={search.status}
           onCategoryChange={(value) => updateFilter("category", value)}
           onStatusChange={(value) => updateFilter("status", value)}
         />
+        {catalogFacetQuery.isError && !catalogQuery.isError ? (
+          <CatalogErrorState onRetry={() => void catalogFacetQuery.refetch()} />
+        ) : null}
 
         <section
           className="catalog-results"
           aria-labelledby="catalog-results-heading"
         >
           <div className="catalog-results-heading">
             <div>
               <p className="public-eyebrow">RESULTS</p>
               <h2
                 id="catalog-results-heading"
diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
index e190367..6f4968b 100644
--- a/frontend/tests/public-catalog.spec.ts
+++ b/frontend/tests/public-catalog.spec.ts
@@ -68,31 +68,55 @@ const timeDetail = {
       request:
         'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
     },
   ],
   source: "Yeyu API",
   cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
 }
 
 const unsafeDetail = {
   ...timeDetail,
+  auth: {
+    type: "api_key",
+    header: 'X-Evil-Header: "<NON_SECRET_TEST_VALUE>"',
+  },
   path: "https://evil.example/redirect?token=<NON_SECRET_TEST_VALUE>",
   parameters: [
     ...timeDetail.parameters,
     {
-      name: "metadata",
+      name: 'bad"name`$()',
+      in: "query",
+      required: false,
+      description: "恶意参数",
+      schema: {
+        type: "string",
+        examples: ["$(whoami)\n`id`"],
+        default: "<NON_SECRET_TEST_VALUE>",
+      },
+    },
+    {
+      name: "unsafe-value",
       in: "query",
       required: false,
-      description: "可见参数",
+      description: "恶意默认值",
       schema: {
         type: "string",
-        "client-secret": "<NON_SECRET_TEST_VALUE>",
+        examples: [
+          " https://evil.example/?next=<NON_SECRET_TEST_VALUE> ",
+          '"quoted"',
+          "percent%20",
+          "query?next=evil",
+          "hash#evil",
+          "back\\slash",
+          "Asia/Shanghai",
+        ],
+        default: "secret-token-<NON_SECRET_TEST_VALUE>",
       },
     },
   ],
   response_schema: {
     ...timeDetail.response_schema,
     token: "<NON_SECRET_TEST_VALUE>",
     properties: {
       ...timeDetail.response_schema.properties,
       api_key: {
         type: "string",
@@ -109,20 +133,25 @@ const unsafeDetail = {
       authorization: "<NON_SECRET_TEST_VALUE>",
     },
   ],
   cache_rules: {
     ...timeDetail.cache_rules,
     "provider-ref": "<NON_SECRET_TEST_VALUE>",
     safe: { nested_password: "<NON_SECRET_TEST_VALUE>" },
   },
 }
 
+const unsafeExamplesDetail = {
+  ...unsafeDetail,
+  path: "/v1/tools/time",
+}
+
 type CatalogPage = {
   data: (typeof timeItem)[]
   count: number
   page: number
   page_size: number
 }
 
 const catalogListUrl = /\/api\/v1\/catalog(?:\?.*)?$/
 const catalogTimeDetailUrl = /\/api\/v1\/catalog\/time(?:\?.*)?$/
 
@@ -226,39 +255,82 @@ test("Catalog search is debounced and filters are shareable in the URL", async (
   await expect
     .poll(() => new URL(page.url()).searchParams.get("page"))
     .toBe("1")
   await expect(page).toHaveURL(/query=uuid.*category=tools.*status=published/)
 })
 
 test("Catalog pagination preserves search filters and requests the selected page", async ({
   page,
 }) => {
   const catalogRequests: URL[] = []
+  const facetRequests: URL[] = []
   await page.route(catalogListUrl, async (route) => {
     const url = new URL(route.request().url())
+    const isFacetRequest =
+      url.searchParams.get("page_size") === "100" &&
+      !url.searchParams.has("query") &&
+      !url.searchParams.has("category") &&
+      !url.searchParams.has("status")
+    if (isFacetRequest) {
+      facetRequests.push(url)
+      const pageNumber = Number(url.searchParams.get("page") ?? "1")
+      const response: CatalogPage = {
+        data: pageNumber === 2 ? [uuidItem] : [timeItem],
+        count: 101,
+        page: pageNumber,
+        page_size: 100,
+      }
+      await route.fulfill({
+        status: 200,
+        contentType: "application/json",
+        body: JSON.stringify(response),
+      })
+      return
+    }
+
     catalogRequests.push(url)
     const pageNumber = Number(url.searchParams.get("page") ?? "1")
     const response: CatalogPage = {
       data: pageNumber === 2 ? [uuidItem] : [timeItem],
       count: 21,
       page: pageNumber,
       page_size: 20,
     }
     await route.fulfill({
       status: 200,
       contentType: "application/json",
       body: JSON.stringify(response),
     })
   })
 
   await page.goto("/catalog?query=time&category=tools&status=published")
   await expect(page.getByTestId("catalog-card-time")).toBeVisible()
+  await expect
+    .poll(() =>
+      facetRequests.some((request) => request.searchParams.get("page") === "2"),
+    )
+    .toBe(true)
+  expect(
+    facetRequests.every(
+      (request) => request.searchParams.get("query") === null,
+    ),
+  ).toBe(true)
+  expect(
+    facetRequests.every(
+      (request) => request.searchParams.get("category") === null,
+    ),
+  ).toBe(true)
+  expect(
+    facetRequests.every(
+      (request) => request.searchParams.get("status") === null,
+    ),
+  ).toBe(true)
   await expect(page.getByRole("button", { name: "下一页" })).toBeEnabled()
 
   await page.getByRole("button", { name: "下一页" }).click()
   await expect(page).toHaveURL(
     /query=time.*category=tools.*status=published.*page=2/,
   )
   await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
 
   const secondRequest = catalogRequests.at(-1)
   expect(secondRequest?.searchParams.get("page")).toBe("2")
@@ -324,20 +396,45 @@ test("Detail rejects unsafe paths and hides sensitive metadata values", async ({
   await page.goto("/catalog/time")
 
   await expect(page.getByText("路径不可用", { exact: true })).toBeVisible()
   await expect(page.locator("body")).not.toContainText("evil.example")
   await expect(page.locator("body")).not.toContainText(
     "<NON_SECRET_TEST_VALUE>",
   )
   await expect(page.getByText("可见错误描述", { exact: true })).toBeVisible()
 })
 
+test("Detail omits unsafe parameter examples from every code sample", async ({
+  page,
+}) => {
+  await mockCatalogApi(page, unsafeExamplesDetail)
+  await page.goto("/catalog/time")
+
+  const codeSamples = await page
+    .locator(".code-example-block code")
+    .allTextContents()
+  expect(codeSamples).toHaveLength(3)
+
+  const renderedExamples = codeSamples.join("\n")
+  expect(renderedExamples).toContain("Asia/Shanghai")
+  expect(renderedExamples).toContain("X-API-Key")
+  expect(renderedExamples).toContain("<YOUR_API_KEY>")
+  expect(renderedExamples).not.toContain('bad"name`$()')
+  expect(renderedExamples).not.toContain(
+    "https://evil.example/?next=<NON_SECRET_TEST_VALUE>",
+  )
+  expect(renderedExamples).not.toContain("$(whoami)")
+  expect(renderedExamples).not.toContain("`id`")
+  expect(renderedExamples).not.toContain("secret-token-<NON_SECRET_TEST_VALUE>")
+  expect(renderedExamples).not.toContain("X-Evil-Header")
+})
+
 test("Detail errors do not render stale detail data", async ({ page }) => {
   let detailRequestCount = 0
   await page.route(catalogTimeDetailUrl, async (route) => {
     detailRequestCount += 1
     if (detailRequestCount === 1) {
       await route.fulfill({
         status: 200,
         contentType: "application/json",
         body: JSON.stringify(timeDetail),
       })
diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
index 14106a5..cf690f4 100644
--- a/plans/agent-reports/task-7-3-report.md
+++ b/plans/agent-reports/task-7-3-report.md
@@ -191,10 +191,45 @@ exit 0
 仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
 ```
 
 ### 未验证项
 
 - 本次新增/强化的 Playwright 行为测试未运行，因此不能宣称浏览器测试通过。
 - build、TypeScript 完整检查、后端接口实际分页/脱敏响应、真实浏览器尺寸验收和线上验收仍未验证。
 - 原有 Playwright `auth.setup.ts` 阻塞证据仍以本报告第 5 节为准；本次没有重试，也没有触碰认证配置或真实凭据。
 
 修复提交主题：`fix: close catalog review findings`
+
+## 10. 第二轮独立复审 Important 修复（2026-10-02）
+
+本轮只处理最新复审报告中的两个 Important，不修改任务 2、`frontend/src/routeTree.gen.ts`、后端、线上服务、DNS、Nginx 或真实凭据。
+
+### 10.1 参数示例值与认证头安全边界
+
+- `frontend/src/components/ApiCatalog/catalog-types.ts` 新增纯函数 `normalizeSafeQueryKey` 与 `normalizeSafeQueryValue`。
+- 参数名只接受以 ASCII 字母开头、长度受限且仅含字母数字、点、下划线和连字符的 query key；其他名称不进入代码示例，详情参数表也使用安全占位名称。
+- 参数值只接受严格字符 allowlist；拒绝空白、引号、反引号、shell 元字符、换行、百分号、query/hash、反斜杠、scheme/外部 URL、敏感词和 JWT-like 值。非字符串只接受有限的数字/布尔值转换。
+- `schema.examples` 会按顺序寻找第一个安全值，再考虑 `default`；恶意首项不会阻断后续合法值，因此 `Asia/Shanghai` 仍可生成。
+- 认证头不再读取目录 metadata，示例与鉴权说明固定使用 `X-API-Key`；curl 的 URL、header 和 query 参数使用单引号包裹并转义单引号，同时保留 `<YOUR_API_KEY>` 占位符。
+- `public-catalog.spec.ts` 的 unsafe detail 增加恶意参数名、外部 URL、空白、引号、shell 字符、换行、百分号、query/hash、反斜杠、敏感默认值和恶意认证头；新增安全路径场景，断言三种代码示例均不包含这些值，并断言合法 `Asia/Shanghai` 和 `X-API-Key` 仍存在。
+
+### 10.2 跨页真实 facets
+
+- `frontend/src/routes/catalog/index.tsx` 增加独立且缓存的公开目录 facets 查询，固定使用 `CatalogService.searchCatalog` 的无筛选请求、`page_size=100` 和 `staleTime=60_000`。
+- 查询按每个响应的 `count` 逐页读取，最多 100 页；达到 count 或空页即停止，避免不受控资源消耗。
+- `CatalogFilters` 改用完整已获取的真实 `CatalogItem[]` 计算分类/状态，并始终保留当前 URL 选择；主目录查询仍保留原有 query/category/status/page 和分页行为，facets 请求不携带这些筛选参数。
+- facets 请求失败时回退当前页真实 items，并显示现有 `CatalogErrorState`；没有新增后端接口、任意 URL、秘密或硬编码候选项。
+- 分页 route mock 返回 count=101，断言独立 facets 请求会请求 page=2/page_size=100，且不带 query、category、status。
+
+### 10.3 本轮真实验证
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+exit 0
+Checked 4 files in 10ms. No fixes applied.
+
+git diff --check
+exit 0
+仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
+```
+
+本轮没有运行 Playwright、前端 build、后端 pytest、路由生成、真实浏览器或线上验收；因此新增浏览器断言、TypeScript 完整检查、实际后端跨页响应和线上结果仍未验证。修复提交主题：`fix: harden catalog examples and filters`。
