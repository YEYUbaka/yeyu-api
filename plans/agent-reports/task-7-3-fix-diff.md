# Review package: ec82905..04fcbd4

## Commits
04fcbd4 fix: close catalog review findings

## Files changed
 .../src/components/ApiCatalog/ApiDetailView.tsx    |  81 ++++++---
 .../components/ApiCatalog/CatalogPagination.tsx    |  45 +++++
 .../src/components/ApiCatalog/catalog-types.ts     |  91 +++++++++-
 frontend/src/index.css                             |  15 ++
 frontend/src/routes/catalog/$slug.tsx              |   8 +-
 frontend/src/routes/catalog/index.tsx              |  22 ++-
 frontend/tests/public-catalog.spec.ts              | 193 ++++++++++++++++++---
 plans/agent-reports/task-7-3-report.md             |  65 +++++++
 plans/fix-task-7-3-catalog-review-findings.md      |  67 +++++++
 9 files changed, 530 insertions(+), 57 deletions(-)

## Diff
diff --git a/frontend/src/components/ApiCatalog/ApiDetailView.tsx b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
index 83a7ef8..7c7f036 100644
--- a/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+++ b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
@@ -1,57 +1,75 @@
 import { Link } from "@tanstack/react-router"
 
 import type { ApiDetail } from "@/client"
 
 import CodeExample from "./CodeExample"
 import {
   asRecord,
   asText,
+  buildPublicApiUrl,
   formatMetadata,
   formatUpdatedAt,
+  normalizeInternalApiPath,
+  PUBLIC_API_BASE_URL,
   responseProperties,
+  sanitizeMetadata,
 } from "./catalog-types"
 
 type QueryExample = {
   name: string
   value: string
 }
 
 function parameterExamples(detail: ApiDetail): QueryExample[] {
   return detail.parameters.flatMap((parameter) => {
-    if (asText(parameter.in, "") !== "query") return []
-    const name = asText(parameter.name, "")
+    const safeParameter = asRecord(sanitizeMetadata(parameter))
+    if (!safeParameter || asText(safeParameter.in, "") !== "query") {
+      return []
+    }
+
+    const name = asText(safeParameter.name, "")
     if (!name) return []
 
-    const schema = asRecord(parameter.schema)
+    const schema = asRecord(safeParameter.schema)
     const examples = schema?.examples
     const example = Array.isArray(examples) ? examples[0] : undefined
     const value = asText(example ?? schema?.default, "value")
     return [{ name, value }]
   })
 }
 
 function buildCodeExamples(detail: ApiDetail, authHeader: string) {
   const method = detail.method.toUpperCase()
   const queryParameters = parameterExamples(detail)
-  const absoluteUrl = `https://api.yeyubaka.top${detail.path}`
+  const path = normalizeInternalApiPath(detail.path)
+  const absoluteUrl = buildPublicApiUrl(path)
+  if (!path || !absoluteUrl) {
+    const unavailable = "无法生成示例：目录路径不可用。"
+    return {
+      curl: unavailable,
+      javascript: unavailable,
+      python: unavailable,
+    }
+  }
+
   const curlStart =
     method === "GET"
       ? `curl -G "${absoluteUrl}"`
       : `curl -X ${method} "${absoluteUrl}"`
   const curlLines = [curlStart, `  -H "${authHeader}: <YOUR_API_KEY>"`]
   for (const parameter of queryParameters) {
     curlLines.push(`  --data-urlencode "${parameter.name}=${parameter.value}"`)
   }
 
   const javascriptLines = [
-    `const endpoint = new URL(${JSON.stringify(detail.path)}, window.location.origin);`,
+    `const endpoint = new URL(${JSON.stringify(path)}, ${JSON.stringify(PUBLIC_API_BASE_URL)});`,
     ...queryParameters.map(
       (parameter) =>
         `endpoint.searchParams.set(${JSON.stringify(parameter.name)}, ${JSON.stringify(parameter.value)});`,
     ),
     "",
     "const response = await fetch(endpoint, {",
     `  method: ${JSON.stringify(method)},`,
     "  headers: {",
     `    ${JSON.stringify(authHeader)}: "<YOUR_API_KEY>",`,
     "  },",
@@ -92,36 +110,38 @@ function readableCacheKey(key: string) {
 }
 
 interface ApiDetailViewProps {
   detail: ApiDetail
 }
 
 export function ApiDetailView({ detail }: ApiDetailViewProps) {
   const authHeader = detail.auth.header ?? "X-API-Key"
   const examples = buildCodeExamples(detail, authHeader)
   const responseFields = responseProperties(detail)
-  const cacheEntries = Object.entries(detail.cache_rules)
+  const safePath = normalizeInternalApiPath(detail.path)
+  const safeCacheRules = asRecord(sanitizeMetadata(detail.cache_rules)) ?? {}
+  const cacheEntries = Object.entries(safeCacheRules)
 
   return (
     <div className="api-detail-page">
       <div className="api-detail-breadcrumbs">
         <Link to="/catalog" className="public-text-link">
           ← 返回公开目录
         </Link>
         <span aria-hidden="true">/</span>
         <span>{detail.category}</span>
       </div>
 
       <header className="api-detail-header">
         <div className="api-detail-path-row">
           <span className="catalog-method-badge">{detail.method}</span>
-          <code>{detail.path}</code>
+          <code>{safePath ?? "路径不可用"}</code>
         </div>
         <h1 className="api-detail-title">{detail.name}</h1>
         <p className="api-detail-summary">{detail.summary}</p>
         <div className="api-detail-tags">
           {detail.is_free ? (
             <span className="catalog-tag catalog-tag-free">免费</span>
           ) : null}
           <span className="catalog-tag catalog-tag-status">
             {detail.status}
           </span>
@@ -168,33 +188,40 @@ export function ApiDetailView({ detail }: ApiDetailViewProps) {
                   <thead>
                     <tr>
                       <th scope="col">名称</th>
                       <th scope="col">位置</th>
                       <th scope="col">必填</th>
                       <th scope="col">类型 / 说明</th>
                     </tr>
                   </thead>
                   <tbody>
                     {detail.parameters.map((parameter, index) => {
-                      const schema = asRecord(parameter.schema)
-                      const name = asText(parameter.name, `参数 ${index + 1}`)
+                      const safeParameter =
+                        asRecord(sanitizeMetadata(parameter)) ?? {}
+                      const schema = asRecord(safeParameter.schema)
+                      const name = asText(
+                        safeParameter.name,
+                        `参数 ${index + 1}`,
+                      )
                       const schemaText = asText(schema?.type, "—")
-                      const description = asText(parameter.description, "")
+                      const description = asText(safeParameter.description, "")
                       return (
                         <tr
-                          key={`${name}-${asText(parameter.in, "unknown")}-${index}`}
+                          key={`${name}-${asText(safeParameter.in, "unknown")}-${index}`}
                         >
                           <th scope="row">
                             <code>{name}</code>
                           </th>
-                          <td>{asText(parameter.in)}</td>
-                          <td>{parameter.required === true ? "是" : "否"}</td>
+                          <td>{asText(safeParameter.in)}</td>
+                          <td>
+                            {safeParameter.required === true ? "是" : "否"}
+                          </td>
                           <td>
                             <span>{schemaText}</span>
                             {description ? (
                               <span className="api-table-note">
                                 {description}
                               </span>
                             ) : null}
                           </td>
                         </tr>
                       )
@@ -245,31 +272,37 @@ export function ApiDetailView({ detail }: ApiDetailViewProps) {
               <div className="api-table-scroll">
                 <table className="api-detail-table">
                   <thead>
                     <tr>
                       <th scope="col">HTTP</th>
                       <th scope="col">错误码</th>
                       <th scope="col">说明</th>
                     </tr>
                   </thead>
                   <tbody>
-                    {detail.errors.map((error, index) => (
-                      <tr key={`${asText(error.code, "error")}-${index}`}>
-                        <td>{asText(error.status)}</td>
-                        <th scope="row">
-                          <code>{asText(error.code)}</code>
-                        </th>
-                        <td>
-                          {asText(error.description, asText(error.message))}
-                        </td>
-                      </tr>
-                    ))}
+                    {detail.errors.map((error, index) => {
+                      const safeError = asRecord(sanitizeMetadata(error)) ?? {}
+                      return (
+                        <tr key={`${asText(safeError.code, "error")}-${index}`}>
+                          <td>{asText(safeError.status)}</td>
+                          <th scope="row">
+                            <code>{asText(safeError.code)}</code>
+                          </th>
+                          <td>
+                            {asText(
+                              safeError.description,
+                              asText(safeError.message),
+                            )}
+                          </td>
+                        </tr>
+                      )
+                    })}
                   </tbody>
                 </table>
               </div>
             ) : (
               <p className="api-detail-muted">目录暂未提供错误码说明。</p>
             )}
           </section>
 
           <section
             className="api-detail-section"
diff --git a/frontend/src/components/ApiCatalog/CatalogPagination.tsx b/frontend/src/components/ApiCatalog/CatalogPagination.tsx
new file mode 100644
index 0000000..b530923
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogPagination.tsx
@@ -0,0 +1,45 @@
+interface CatalogPaginationProps {
+  count: number
+  page: number
+  pageSize: number
+  isFetching?: boolean
+  onPageChange: (page: number) => void
+}
+
+export function CatalogPagination({
+  count,
+  page,
+  pageSize,
+  isFetching = false,
+  onPageChange,
+}: CatalogPaginationProps) {
+  const safePageSize = Math.max(1, pageSize)
+  const totalPages = Math.max(1, Math.ceil(count / safePageSize))
+  if (totalPages <= 1) return null
+
+  return (
+    <nav className="catalog-pagination" aria-label="目录分页">
+      <button
+        type="button"
+        className="public-inline-button"
+        disabled={isFetching || page <= 1}
+        onClick={() => onPageChange(page - 1)}
+      >
+        上一页
+      </button>
+      <span aria-live="polite">
+        第 {page} / {totalPages} 页
+      </span>
+      <button
+        type="button"
+        className="public-inline-button"
+        disabled={isFetching || page >= totalPages}
+        onClick={() => onPageChange(page + 1)}
+      >
+        下一页
+      </button>
+    </nav>
+  )
+}
+
+export default CatalogPagination
diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
index 16a7477..248fd59 100644
--- a/frontend/src/components/ApiCatalog/catalog-types.ts
+++ b/frontend/src/components/ApiCatalog/catalog-types.ts
@@ -1,33 +1,95 @@
 import type { ApiDetail, CatalogItem } from "@/client"
 
 export type CatalogSearchParams = {
   query?: string
   category?: string
   status?: string
+  page: number
 }
 
 export type CatalogMetadata = Record<string, unknown>
 
+export const PUBLIC_API_BASE_URL = "https://api.yeyubaka.top"
+
+const SENSITIVE_METADATA_KEY_PARTS = [
+  "token",
+  "secret",
+  "password",
+  "authorization",
+  "cookie",
+  "apikey",
+  "credential",
+  "privatekey",
+  "providerref",
+]
+
+function normalizedMetadataKey(key: string): string {
+  return key.toLowerCase().replace(/[^a-z0-9]/g, "")
+}
+
+function isSensitiveMetadataKey(key: string): boolean {
+  const normalized = normalizedMetadataKey(key)
+  return SENSITIVE_METADATA_KEY_PARTS.some((part) => normalized.includes(part))
+}
+
 export function normalizeSearchValue(value: unknown): string | undefined {
   if (typeof value !== "string") return undefined
   const normalized = value.trim()
   return normalized || undefined
 }
 
+export function normalizePage(value: unknown): number {
+  const page =
+    typeof value === "number"
+      ? value
+      : typeof value === "string" && value.trim()
+        ? Number(value)
+        : Number.NaN
+
+  return Number.isSafeInteger(page) && page > 0 ? page : 1
+}
+
+export function normalizeInternalApiPath(value: unknown): string | undefined {
+  if (typeof value !== "string") return undefined
+
+  const normalized = value.trim()
+  if (!normalized) return undefined
+
+  if (
+    !normalized.startsWith("/") ||
+    normalized.startsWith("//") ||
+    normalized.includes("//") ||
+    /https?:/i.test(normalized) ||
+    normalized.includes("\\") ||
+    /[?#%]/.test(normalized) ||
+    normalized.includes("..")
+  ) {
+    return undefined
+  }
+
+  return normalized
+}
+
+export function buildPublicApiUrl(value: unknown): string | undefined {
+  const path = normalizeInternalApiPath(value)
+  return path ? `${PUBLIC_API_BASE_URL}${path}` : undefined
+}
+
 export function parseCatalogSearch(
   search: Record<string, unknown>,
 ): CatalogSearchParams {
   return {
     query: normalizeSearchValue(search.query),
     category: normalizeSearchValue(search.category),
     status: normalizeSearchValue(search.status),
+    page: normalizePage(search.page),
   }
 }
 
 export function formatUpdatedAt(value?: string | null): string {
   if (!value) return "更新时间待补充"
 
   const timestamp = Date.parse(value)
   if (Number.isNaN(timestamp)) return value
 
   return new Intl.DateTimeFormat("zh-HK", {
@@ -43,38 +105,55 @@ export function asRecord(value: unknown): CatalogMetadata | undefined {
 }
 
 export function asText(value: unknown, fallback = "—"): string {
   if (typeof value === "string") return value
   if (typeof value === "number" || typeof value === "boolean") {
     return String(value)
   }
   return fallback
 }
 
+export function sanitizeMetadata(value: unknown): unknown {
+  if (Array.isArray(value)) {
+    return value.map((item) => sanitizeMetadata(item))
+  }
+
+  if (typeof value !== "object" || value === null) return value
+
+  const sanitized: CatalogMetadata = {}
+  for (const [key, nestedValue] of Object.entries(value)) {
+    if (isSensitiveMetadataKey(key)) continue
+    sanitized[key] = sanitizeMetadata(nestedValue)
+  }
+  return sanitized
+}
+
 export function formatMetadata(value: unknown): string {
-  if (value === null || value === undefined) return "—"
-  if (typeof value === "string") return value
-  if (typeof value === "number" || typeof value === "boolean") {
-    return String(value)
+  const sanitized = sanitizeMetadata(value)
+  if (sanitized === null || sanitized === undefined) return "—"
+  if (typeof sanitized === "string") return sanitized
+  if (typeof sanitized === "number" || typeof sanitized === "boolean") {
+    return String(sanitized)
   }
 
   try {
-    return JSON.stringify(value, null, 2) ?? "无法展示"
+    return JSON.stringify(sanitized, null, 2) ?? "无法展示"
   } catch {
     return "无法展示"
   }
 }
 
 export function responseProperties(
   detail: ApiDetail,
 ): Array<[string, CatalogMetadata]> {
-  const properties = asRecord(detail.response_schema)?.properties
+  const safeResponseSchema = asRecord(sanitizeMetadata(detail.response_schema))
+  const properties = safeResponseSchema?.properties
   if (!properties || typeof properties !== "object") return []
 
   return Object.entries(properties)
     .map(
       ([name, value]) =>
         [name, asRecord(value) ?? {}] as [string, CatalogMetadata],
     )
     .sort(([left], [right]) => left.localeCompare(right))
 }
 
diff --git a/frontend/src/index.css b/frontend/src/index.css
index 4cd1214..eff80a1 100644
--- a/frontend/src/index.css
+++ b/frontend/src/index.css
@@ -716,20 +716,35 @@
   margin-top: 1rem;
 }
 
 .catalog-grid {
   display: grid;
   grid-template-columns: repeat(2, minmax(0, 1fr));
   gap: 1rem;
   margin-top: 1.25rem;
 }
 
+.catalog-pagination {
+  display: flex;
+  align-items: center;
+  justify-content: center;
+  gap: 1rem;
+  margin-top: 1.5rem;
+  color: var(--yeyu-muted);
+  font-size: 0.85rem;
+}
+
+.catalog-pagination button:disabled {
+  cursor: not-allowed;
+  opacity: 0.45;
+}
+
 .catalog-card {
   display: grid;
   min-width: 0;
   gap: 1.1rem;
   padding: 1.25rem;
   border: 1px solid var(--yeyu-line);
   border-top: 3px solid var(--yeyu-teal);
   background: var(--yeyu-paper-strong);
   transition:
     border-color 160ms ease,
diff --git a/frontend/src/routes/catalog/$slug.tsx b/frontend/src/routes/catalog/$slug.tsx
index 5c51950..30c0fa2 100644
--- a/frontend/src/routes/catalog/$slug.tsx
+++ b/frontend/src/routes/catalog/$slug.tsx
@@ -28,19 +28,21 @@ function CatalogDetailRoute() {
       const response = await CatalogService.getCatalogDetail({
         path: { slug },
       })
       return response.data
     },
   })
 
   return (
     <PublicLayout>
       <div className="public-container catalog-detail-shell">
-        {detailQuery.isPending ? <CatalogLoadingState /> : null}
-        {detailQuery.isError ? (
+        {detailQuery.isPending ? (
+          <CatalogLoadingState />
+        ) : detailQuery.isError ? (
           <CatalogDetailErrorState onRetry={() => void detailQuery.refetch()} />
+        ) : detailQuery.data ? (
+          <ApiDetailView detail={detailQuery.data} />
         ) : null}
-        {detailQuery.data ? <ApiDetailView detail={detailQuery.data} /> : null}
       </div>
     </PublicLayout>
   )
 }
diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
index f83b403..9ad8056 100644
--- a/frontend/src/routes/catalog/index.tsx
+++ b/frontend/src/routes/catalog/index.tsx
@@ -1,17 +1,18 @@
 import { useQuery } from "@tanstack/react-query"
 import { createFileRoute } from "@tanstack/react-router"
 import { useEffect, useState } from "react"
 
 import { type CatalogPage, CatalogService } from "@/client"
 import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
 import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
+import CatalogPagination from "@/components/ApiCatalog/CatalogPagination"
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
@@ -41,55 +42,58 @@ function CatalogRoutePage() {
 
   useEffect(() => {
     const normalizedQuery = normalizeSearchValue(draftQuery)
     if (normalizedQuery === search.query) return
 
     const timeoutId = window.setTimeout(() => {
       void navigate({
         search: (previous) => ({
           ...previous,
           query: normalizedQuery,
+          page: 1,
         }),
         replace: true,
       })
     }, 400)
 
     return () => window.clearTimeout(timeoutId)
   }, [draftQuery, navigate, search.query])
 
   const catalogQuery = useQuery<CatalogPage>({
     queryKey: [
       "public-catalog",
       search.query ?? "",
       search.category ?? "",
       search.status ?? "",
+      search.page,
     ],
     queryFn: async () => {
       const response = await CatalogService.searchCatalog({
         query: {
           query: search.query,
           category: search.category,
           status: search.status,
-          page: 1,
+          page: search.page,
           page_size: 20,
         },
       })
       return response.data
     },
   })
 
   const items = catalogQuery.data?.data ?? []
   const updateFilter = (key: "category" | "status", value: string) => {
     void navigate({
       search: (previous) => ({
         ...previous,
         [key]: normalizeSearchValue(value),
+        page: 1,
       }),
       replace: true,
     })
   }
 
   return (
     <PublicLayout>
       <div className="public-container catalog-page-shell">
         <header className="catalog-page-header">
           <p className="public-eyebrow">公开目录 / REAL DATA</p>
@@ -141,15 +145,31 @@ function CatalogRoutePage() {
           {!catalogQuery.isPending &&
           !catalogQuery.isError &&
           items.length === 0 ? (
             <CatalogEmptyState />
           ) : null}
           {!catalogQuery.isPending &&
           !catalogQuery.isError &&
           items.length > 0 ? (
             <CatalogGrid items={items} />
           ) : null}
+          {!catalogQuery.isPending &&
+          !catalogQuery.isError &&
+          catalogQuery.data ? (
+            <CatalogPagination
+              count={catalogQuery.data.count}
+              page={search.page}
+              pageSize={catalogQuery.data.page_size}
+              isFetching={catalogQuery.isFetching}
+              onPageChange={(page) =>
+                void navigate({
+                  search: (previous) => ({ ...previous, page }),
+                  replace: true,
+                })
+              }
+            />
+          ) : null}
         </section>
       </div>
     </PublicLayout>
   )
 }
diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
index 39af2f7..e190367 100644
--- a/frontend/tests/public-catalog.spec.ts
+++ b/frontend/tests/public-catalog.spec.ts
@@ -66,58 +66,103 @@ const timeDetail = {
     {
       language: "curl",
       request:
         'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
     },
   ],
   source: "Yeyu API",
   cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
 }
 
+const unsafeDetail = {
+  ...timeDetail,
+  path: "https://evil.example/redirect?token=<NON_SECRET_TEST_VALUE>",
+  parameters: [
+    ...timeDetail.parameters,
+    {
+      name: "metadata",
+      in: "query",
+      required: false,
+      description: "可见参数",
+      schema: {
+        type: "string",
+        "client-secret": "<NON_SECRET_TEST_VALUE>",
+      },
+    },
+  ],
+  response_schema: {
+    ...timeDetail.response_schema,
+    token: "<NON_SECRET_TEST_VALUE>",
+    properties: {
+      ...timeDetail.response_schema.properties,
+      api_key: {
+        type: "string",
+        private_key: "<NON_SECRET_TEST_VALUE>",
+      },
+    },
+  },
+  errors: [
+    ...timeDetail.errors,
+    {
+      status: 500,
+      code: "SAFE_ERROR",
+      description: "可见错误描述",
+      authorization: "<NON_SECRET_TEST_VALUE>",
+    },
+  ],
+  cache_rules: {
+    ...timeDetail.cache_rules,
+    "provider-ref": "<NON_SECRET_TEST_VALUE>",
+    safe: { nested_password: "<NON_SECRET_TEST_VALUE>" },
+  },
+}
+
 type CatalogPage = {
   data: (typeof timeItem)[]
   count: number
   page: number
   page_size: number
 }
 
-async function mockCatalogApi(page: Page) {
-  await page.route("**/api/v1/catalog*", async (route) => {
-    const url = new URL(route.request().url())
+const catalogListUrl = /\/api\/v1\/catalog(?:\?.*)?$/
+const catalogTimeDetailUrl = /\/api\/v1\/catalog\/time(?:\?.*)?$/
 
-    if (url.pathname.endsWith("/time")) {
-      await route.fulfill({
-        status: 200,
-        contentType: "application/json",
-        body: JSON.stringify(timeDetail),
-      })
-      return
-    }
+async function mockCatalogApi(page: Page, detail = timeDetail) {
+  await page.route(catalogTimeDetailUrl, async (route) => {
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify(detail),
+    })
+  })
 
+  await page.route(catalogListUrl, async (route) => {
+    const url = new URL(route.request().url())
     const query = url.searchParams.get("query") ?? ""
     const category = url.searchParams.get("category")
     const status = url.searchParams.get("status")
+    const pageNumber = Number(url.searchParams.get("page") ?? "1")
     const data =
       query === "missing"
         ? []
         : query === "uuid"
           ? [uuidItem]
           : [timeItem, uuidItem]
     const filtered = data.filter(
       (item) =>
         (!category || item.category === category) &&
         (!status || item.status === status),
     )
     const response: CatalogPage = {
       data: filtered,
       count: filtered.length,
-      page: 1,
+      page: pageNumber,
       page_size: 20,
     }
 
     await route.fulfill({
       status: 200,
       contentType: "application/json",
       body: JSON.stringify(response),
     })
   })
 }
@@ -139,55 +184,99 @@ test("Anonymous users can browse the real public catalog", async ({ page }) => {
   await expect(page.getByRole("link", { name: /时间查询/ })).toHaveAttribute(
     "href",
     "/catalog/time",
   )
 })
 
 test("Catalog search is debounced and filters are shareable in the URL", async ({
   page,
 }) => {
   const catalogRequests: string[] = []
-  await page.route("**/api/v1/catalog*", async (route) => {
+  await page.route(catalogListUrl, async (route) => {
     const url = new URL(route.request().url())
-    if (url.pathname.endsWith("/time")) {
-      await route.fulfill({
-        status: 200,
-        contentType: "application/json",
-        body: JSON.stringify(timeDetail),
-      })
-      return
-    }
     catalogRequests.push(url.search)
     const item = url.searchParams.get("query") === "uuid" ? uuidItem : timeItem
     await route.fulfill({
       status: 200,
       contentType: "application/json",
       body: JSON.stringify({ data: [item], count: 1, page: 1, page_size: 20 }),
     })
   })
 
-  await page.goto("/catalog")
+  await page.goto("/catalog?page=2")
   const searchInput = page.getByRole("searchbox", { name: "搜索公开 API" })
   await searchInput.fill("uuid")
   await page.waitForTimeout(150)
   expect(
     catalogRequests.filter((request) => request.includes("query=uuid")),
   ).toHaveLength(0)
-  await expect(page).toHaveURL(/\/catalog\?query=uuid$/)
+  await expect
+    .poll(() => new URL(page.url()).searchParams.get("page"))
+    .toBe("1")
+  await expect
+    .poll(() => new URL(page.url()).searchParams.get("query"))
+    .toBe("uuid")
   await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
 
   await page.getByLabel("分类").selectOption("tools")
+  await expect
+    .poll(() => new URL(page.url()).searchParams.get("page"))
+    .toBe("1")
   await expect(page).toHaveURL(/query=uuid.*category=tools/)
   await page.getByLabel("状态").selectOption("published")
+  await expect
+    .poll(() => new URL(page.url()).searchParams.get("page"))
+    .toBe("1")
   await expect(page).toHaveURL(/query=uuid.*category=tools.*status=published/)
 })
 
+test("Catalog pagination preserves search filters and requests the selected page", async ({
+  page,
+}) => {
+  const catalogRequests: URL[] = []
+  await page.route(catalogListUrl, async (route) => {
+    const url = new URL(route.request().url())
+    catalogRequests.push(url)
+    const pageNumber = Number(url.searchParams.get("page") ?? "1")
+    const response: CatalogPage = {
+      data: pageNumber === 2 ? [uuidItem] : [timeItem],
+      count: 21,
+      page: pageNumber,
+      page_size: 20,
+    }
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify(response),
+    })
+  })
+
+  await page.goto("/catalog?query=time&category=tools&status=published")
+  await expect(page.getByTestId("catalog-card-time")).toBeVisible()
+  await expect(page.getByRole("button", { name: "下一页" })).toBeEnabled()
+
+  await page.getByRole("button", { name: "下一页" }).click()
+  await expect(page).toHaveURL(
+    /query=time.*category=tools.*status=published.*page=2/,
+  )
+  await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
+
+  const secondRequest = catalogRequests.at(-1)
+  expect(secondRequest?.searchParams.get("page")).toBe("2")
+  expect(secondRequest?.searchParams.get("page_size")).toBe("20")
+
+  await page.getByRole("button", { name: "上一页" }).click()
+  await expect(page).toHaveURL(
+    /query=time.*category=tools.*status=published.*page=1/,
+  )
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
@@ -221,20 +310,78 @@ test("Time detail documents the request contract and safe code examples", async
   await expect(
     page.locator("code").filter({ hasText: "api.yeyubaka.top" }).first(),
   ).toBeVisible()
 
   const copyButton = page.getByRole("button", { name: "复制 curl 示例" })
   await expect(copyButton).toBeVisible()
   await copyButton.click()
   await expect(copyButton).toContainText("已复制")
 })
 
+test("Detail rejects unsafe paths and hides sensitive metadata values", async ({
+  page,
+}) => {
+  await mockCatalogApi(page, unsafeDetail)
+  await page.goto("/catalog/time")
+
+  await expect(page.getByText("路径不可用", { exact: true })).toBeVisible()
+  await expect(page.locator("body")).not.toContainText("evil.example")
+  await expect(page.locator("body")).not.toContainText(
+    "<NON_SECRET_TEST_VALUE>",
+  )
+  await expect(page.getByText("可见错误描述", { exact: true })).toBeVisible()
+})
+
+test("Detail errors do not render stale detail data", async ({ page }) => {
+  let detailRequestCount = 0
+  await page.route(catalogTimeDetailUrl, async (route) => {
+    detailRequestCount += 1
+    if (detailRequestCount === 1) {
+      await route.fulfill({
+        status: 200,
+        contentType: "application/json",
+        body: JSON.stringify(timeDetail),
+      })
+      return
+    }
+
+    await route.fulfill({
+      status: 503,
+      contentType: "application/json",
+      body: JSON.stringify({ detail: "unavailable" }),
+    })
+  })
+  await page.route(catalogListUrl, async (route) => {
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
+  await page.goto("/catalog/time")
+  await expect(page.getByRole("heading", { name: "时间查询" })).toBeVisible()
+  await page.getByRole("link", { name: /返回公开目录/ }).click()
+  await expect(page).toHaveURL("/catalog")
+  await page.getByRole("link", { name: /时间查询/ }).click()
+
+  await expect(page.getByTestId("catalog-detail-error")).toBeVisible()
+  await expect(
+    page.getByRole("heading", { name: "时间查询" }),
+  ).not.toBeVisible()
+})
+
 test("Public navigation remains keyboard accessible on mobile", async ({
   page,
 }) => {
   await page.setViewportSize({ width: 390, height: 844 })
   await mockCatalogApi(page)
   await page.goto("/")
 
   const navigation = page.getByRole("navigation", { name: "公共导航" })
   const menuButton = navigation.getByRole("button", { name: /菜单/ })
 
diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
index aaab69a..14106a5 100644
--- a/plans/agent-reports/task-7-3-report.md
+++ b/plans/agent-reports/task-7-3-report.md
@@ -126,10 +126,75 @@ Checked 15 files in 14ms. No fixes applied.
 - [x] 复制按钮有可访问名称，成功状态有文字和图标反馈。
 - [x] 移动端表格、路径和代码块设置横向滚动边界。
 - [x] Biome 最终对本次 15 个文件通过。
 - [ ] Playwright、build、pytest 和真实浏览器验收：受用户要求/现有 setup 阻塞，未验证。
 
 ## 7. 提交
 
 实现代码提交主题：`feat: add public catalog and api detail pages`
 
 提交 SHA：`c13adce`（实现提交；报告随后单独提交）。
+
+## 8. 独立审查 Important 修复（2026-10-02）
+
+本次修复范围仅覆盖独立审查报告中的五个 Important，不修改任务 2 认证/公共壳层，不手改 `frontend/src/routeTree.gen.ts`，不扩展在线调试、API Key 管理或第三方接口。
+
+### 8.1 示例 URL/path 边界
+
+- `frontend/src/components/ApiCatalog/catalog-types.ts` 新增 `normalizeInternalApiPath` 和 `buildPublicApiUrl`。
+- 只接受经过 trim 的单斜杠内部绝对路径，拒绝 `http(s)`、`//`、反斜杠、query/hash、百分号和 `..`。
+- `ApiDetailView` 的 curl、JavaScript、Python 示例统一使用受控路径和 `https://api.yeyubaka.top`；非法路径显示“路径不可用”和不可执行的占位说明，不回显后端任意绝对 URL。
+- 保留 `<YOUR_API_KEY>`，未增加任意 URL 输入或凭据读取。
+
+### 8.2 metadata 防御性脱敏
+
+- `sanitizeMetadata` 递归删除规范化后包含 `token`、`secret`、`password`、`authorization`、`cookie`、`apikey`、`credential`、`privatekey`、`providerref` 的大小写/下划线/连字符变体。
+- `formatMetadata` 在 JSON 格式化前过滤；响应 schema、参数、错误和 cache rules 的展示均使用过滤后的对象，敏感值不替换回显。
+
+### 8.3 目录分页
+
+- `CatalogSearchParams` 新增合法正整数 `page`，缺失或非法值默认为 1。
+- 目录 query key 和 `CatalogService.searchCatalog` 请求均使用 `page` 与 `page_size: 20`。
+- 新增单一职责文件 `frontend/src/components/ApiCatalog/CatalogPagination.tsx`，提供可访问的上一页/下一页、当前页和总页数；搜索、分类、状态变化会重置 `page=1`，分页导航保留其他 search params。
+- 增加分页 URL、请求 query 和上一页行为的 route-mock 回归断言。
+
+### 8.4 详情错误状态互斥
+
+- `frontend/src/routes/catalog/$slug.tsx` 改为 loading/error/success 三选一分支；`isError` 时不再渲染 React Query 保留的旧 detail。
+- 增加“先成功、导航返回后详情请求失败”的 stale detail 回归断言。
+
+### 8.5 Playwright mock 匹配可靠性
+
+- `frontend/tests/public-catalog.spec.ts` 将宽泛 `**/api/v1/catalog*` 改为分别匹配列表 URL 和 `/api/v1/catalog/time` 详情 URL 的正则，并允许 query string。
+- 列表和详情 route mock 不会再把详情请求误判为列表请求，也不会意外访问真实后端。
+
+## 9. 本次真实验证结果
+
+按用户要求没有运行长时间 Playwright、前端 build、后端 pytest、路由生成或线上验收。
+
+先写测试后的短静态检查：
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+exit 1
+原因：Biome 仅报告新增 expect.poll 的格式问题，未修改文件。
+```
+
+修复格式并完成实现后的静态检查：
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx E:\AI_projects\yeyu-api\frontend\src\index.css E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+exit 0
+Checked 7 files in 12ms. No fixes applied.
+
+git diff --check
+exit 0
+仅有 Windows 工作树 LF/CRLF 转换提示，无空白错误。
+```
+
+### 未验证项
+
+- 本次新增/强化的 Playwright 行为测试未运行，因此不能宣称浏览器测试通过。
+- build、TypeScript 完整检查、后端接口实际分页/脱敏响应、真实浏览器尺寸验收和线上验收仍未验证。
+- 原有 Playwright `auth.setup.ts` 阻塞证据仍以本报告第 5 节为准；本次没有重试，也没有触碰认证配置或真实凭据。
+
+修复提交主题：`fix: close catalog review findings`
diff --git a/plans/fix-task-7-3-catalog-review-findings.md b/plans/fix-task-7-3-catalog-review-findings.md
new file mode 100644
index 0000000..9d91c89
--- /dev/null
+++ b/plans/fix-task-7-3-catalog-review-findings.md
@@ -0,0 +1,67 @@
+# Task 7-3 Catalog Review Findings Fix Plan
+
+> **For agentic workers:** Execute this plan in the current `E:\AI_projects\yeyu-api` worktree. Keep the existing public shell and generated route tree unchanged.
+
+**Goal:** Close the five Important findings from the Task 7-3 read-only review with the smallest safe frontend changes and focused regression coverage.
+
+**Architecture:** Keep catalog state in TanStack Router search params. Add pure path and metadata guards in `catalog-types.ts`, use those guards at every detail rendering boundary, and keep pagination as a focused `CatalogPagination` component. Make the detail route render exactly one loading, error, or success state.
+
+**Tech Stack:** React, TypeScript, TanStack Router, TanStack Query, generated `CatalogService`, Playwright route mocks, Biome.
+
+## Global Constraints
+
+- Modify only the Task 7-3 frontend catalog files, focused catalog tests, this plan, and the Task 7-3 report.
+- Do not edit `frontend\src\routeTree.gen.ts`, Task 2 authentication/public shell behavior, backend, online services, DNS, Nginx, or credentials.
+- Use `https://api.yeyubaka.top` only as the controlled public API base in generated examples.
+- Retain `<YOUR_API_KEY>` and use `<NON_SECRET_TEST_VALUE>` for any sensitive-looking test value.
+- Write or update regression tests before implementation; do not run long Playwright or build commands.
+
+### Task 1: Add failing regression coverage
+
+**Files:**
+- Modify: `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`
+
+- [ ] Replace the broad catalog glob with separate regular expressions for `/api/v1/catalog` list URLs with optional query strings and `/api/v1/catalog/time` detail URLs.
+- [ ] Add route-mocked assertions for page 2 and page 1 navigation while retaining `query`, `category`, and `status`.
+- [ ] Add route-mocked detail data containing an unsafe absolute path and sensitive nested keys, then assert the unsafe host and `<NON_SECRET_TEST_VALUE>` are absent from rendered examples/metadata.
+- [ ] Add a stale-detail failure flow that asserts the detail error state does not render the previous detail heading.
+- [ ] Run only the permitted short static check on the updated test file; do not run Playwright.
+
+### Task 2: Harden detail path and metadata boundaries
+
+**Files:**
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`
+
+**Interfaces:**
+- `normalizeInternalApiPath(value: unknown): string | undefined` trims and accepts only a single-slash internal path without `http(s)`, `//`, backslash, query/hash, percent encoding, or `..`.
+- `sanitizeMetadata(value: unknown): unknown` recursively removes object keys whose normalized lowercase form contains `token`, `secret`, `password`, `authorization`, `cookie`, `apikey`, `credential`, `privatekey`, or `providerref`.
+- `formatMetadata` sanitizes before JSON formatting; `responseProperties`, parameter display/examples, error display, and cache display consume sanitized values.
+
+- [ ] Implement the two pure guards in `catalog-types.ts` without changing generated client types.
+- [ ] Build curl, JavaScript, and Python snippets from the controlled base plus the normalized path; render `路径不可用` and a non-URL message when the backend path is rejected.
+- [ ] Keep `<YOUR_API_KEY>` unchanged and do not add arbitrary URL input or credential reads.
+
+### Task 3: Add legal page state and mutually exclusive detail states
+
+**Files:**
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
+- Create: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx`
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`
+- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx`
+
+- [ ] Add `page: number` to parsed search state, normalize only positive safe integers, and default invalid/missing input to 1.
+- [ ] Include `page` in the query key and send `page` plus `page_size: 20` to `CatalogService.searchCatalog`.
+- [ ] Reset `page` to 1 on debounced query changes and category/status changes while preserving the other search params.
+- [ ] Render accessible previous/next controls using `count` and `page_size`; disable controls at boundaries and while fetching.
+- [ ] Render detail loading, error, and success as an exclusive branch so stale detail data is hidden when `isError` is true.
+
+### Task 4: Verify and record evidence
+
+**Files:**
+- Modify: `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-report.md`
+
+- [ ] Run targeted Biome on every changed frontend source/test file and record the real exit code/output.
+- [ ] Run `git diff --check` and record the real result, including any non-failure line-ending warning.
+- [ ] Do not claim Playwright, build, backend tests, route generation, or browser acceptance unless actually run; record them as unverified.
+- [ ] Inspect the final diff and status, append the five fixes and evidence to the report, then commit with `fix: close catalog review findings`.
