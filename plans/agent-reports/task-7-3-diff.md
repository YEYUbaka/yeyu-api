# Review package: 53b19fc..ec82905

## Commits
ec82905 docs: record task 3 catalog implementation
a30e6e7 docs: record task 7-3 implementation report
c13adce feat: add public catalog and api detail pages

## Files changed
 .../src/components/ApiCatalog/ApiDetailView.tsx    | 327 +++++++++++
 frontend/src/components/ApiCatalog/CatalogCard.tsx |  42 ++
 .../src/components/ApiCatalog/CatalogFilters.tsx   |  72 +++
 frontend/src/components/ApiCatalog/CatalogGrid.tsx |  19 +
 .../src/components/ApiCatalog/CatalogSearch.tsx    |  53 ++
 .../src/components/ApiCatalog/CatalogStates.tsx    |  64 ++
 frontend/src/components/ApiCatalog/CodeExample.tsx |  67 +++
 .../src/components/ApiCatalog/catalog-types.ts     |  89 +++
 .../src/components/PublicSite/PublicFooter.tsx     |   4 +-
 .../src/components/PublicSite/PublicHeader.tsx     |   4 +-
 frontend/src/index.css                             | 647 ++++++++++++++++++++-
 frontend/src/routes/catalog/$slug.tsx              |  46 ++
 frontend/src/routes/catalog/index.tsx              | 156 ++++-
 frontend/src/routes/index.tsx                      |  28 +-
 frontend/tests/public-catalog.spec.ts              | 235 +++++++-
 plans/agent-reports/task-7-3-brief.md              |  58 ++
 plans/agent-reports/task-7-3-report.md             | 135 +++++
 17 files changed, 1984 insertions(+), 62 deletions(-)

## Diff
diff --git a/frontend/src/components/ApiCatalog/ApiDetailView.tsx b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
new file mode 100644
index 0000000..83a7ef8
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
@@ -0,0 +1,327 @@
+import { Link } from "@tanstack/react-router"
+
+import type { ApiDetail } from "@/client"
+
+import CodeExample from "./CodeExample"
+import {
+  asRecord,
+  asText,
+  formatMetadata,
+  formatUpdatedAt,
+  responseProperties,
+} from "./catalog-types"
+
+type QueryExample = {
+  name: string
+  value: string
+}
+
+function parameterExamples(detail: ApiDetail): QueryExample[] {
+  return detail.parameters.flatMap((parameter) => {
+    if (asText(parameter.in, "") !== "query") return []
+    const name = asText(parameter.name, "")
+    if (!name) return []
+
+    const schema = asRecord(parameter.schema)
+    const examples = schema?.examples
+    const example = Array.isArray(examples) ? examples[0] : undefined
+    const value = asText(example ?? schema?.default, "value")
+    return [{ name, value }]
+  })
+}
+
+function buildCodeExamples(detail: ApiDetail, authHeader: string) {
+  const method = detail.method.toUpperCase()
+  const queryParameters = parameterExamples(detail)
+  const absoluteUrl = `https://api.yeyubaka.top${detail.path}`
+  const curlStart =
+    method === "GET"
+      ? `curl -G "${absoluteUrl}"`
+      : `curl -X ${method} "${absoluteUrl}"`
+  const curlLines = [curlStart, `  -H "${authHeader}: <YOUR_API_KEY>"`]
+  for (const parameter of queryParameters) {
+    curlLines.push(`  --data-urlencode "${parameter.name}=${parameter.value}"`)
+  }
+
+  const javascriptLines = [
+    `const endpoint = new URL(${JSON.stringify(detail.path)}, window.location.origin);`,
+    ...queryParameters.map(
+      (parameter) =>
+        `endpoint.searchParams.set(${JSON.stringify(parameter.name)}, ${JSON.stringify(parameter.value)});`,
+    ),
+    "",
+    "const response = await fetch(endpoint, {",
+    `  method: ${JSON.stringify(method)},`,
+    "  headers: {",
+    `    ${JSON.stringify(authHeader)}: "<YOUR_API_KEY>",`,
+    "  },",
+    "});",
+    "const data = await response.json();",
+    "console.log(data);",
+  ]
+
+  const pythonLines = [
+    "import requests",
+    "",
+    "response = requests.request(",
+    `    ${JSON.stringify(method)},`,
+    `    ${JSON.stringify(absoluteUrl)},`,
+    `    headers={${JSON.stringify(authHeader)}: "<YOUR_API_KEY>"},`,
+    ...(queryParameters.length
+      ? [
+          `    params=${JSON.stringify(Object.fromEntries(queryParameters.map((parameter) => [parameter.name, parameter.value])))},`,
+        ]
+      : []),
+    "    timeout=10,",
+    ")",
+    "response.raise_for_status()",
+    "print(response.json())",
+  ]
+
+  return {
+    curl: curlLines.join(" \\\n"),
+    javascript: javascriptLines.join("\n"),
+    python: pythonLines.join("\n"),
+  }
+}
+
+function readableCacheKey(key: string) {
+  return key
+    .replaceAll("_", " ")
+    .replace(/\b\w/g, (character) => character.toUpperCase())
+}
+
+interface ApiDetailViewProps {
+  detail: ApiDetail
+}
+
+export function ApiDetailView({ detail }: ApiDetailViewProps) {
+  const authHeader = detail.auth.header ?? "X-API-Key"
+  const examples = buildCodeExamples(detail, authHeader)
+  const responseFields = responseProperties(detail)
+  const cacheEntries = Object.entries(detail.cache_rules)
+
+  return (
+    <div className="api-detail-page">
+      <div className="api-detail-breadcrumbs">
+        <Link to="/catalog" className="public-text-link">
+          ← 返回公开目录
+        </Link>
+        <span aria-hidden="true">/</span>
+        <span>{detail.category}</span>
+      </div>
+
+      <header className="api-detail-header">
+        <div className="api-detail-path-row">
+          <span className="catalog-method-badge">{detail.method}</span>
+          <code>{detail.path}</code>
+        </div>
+        <h1 className="api-detail-title">{detail.name}</h1>
+        <p className="api-detail-summary">{detail.summary}</p>
+        <div className="api-detail-tags">
+          {detail.is_free ? (
+            <span className="catalog-tag catalog-tag-free">免费</span>
+          ) : null}
+          <span className="catalog-tag catalog-tag-status">
+            {detail.status}
+          </span>
+          <time dateTime={detail.updated_at ?? undefined}>
+            更新于 {formatUpdatedAt(detail.updated_at)}
+          </time>
+        </div>
+      </header>
+
+      <div className="api-detail-layout">
+        <main className="api-detail-main">
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-auth-heading"
+          >
+            <p className="public-eyebrow">AUTHENTICATION</p>
+            <h2 id="api-auth-heading" className="api-detail-section-title">
+              API Key 鉴权
+            </h2>
+            <p className="api-detail-copy">
+              调用该接口时，请在 <code>{authHeader}</code> 请求头中提供你的 API
+              Key。浏览器登录 Cookie 不会替代 API Key。
+            </p>
+            <div className="api-auth-callout">
+              <span>请求头</span>
+              <code>{authHeader}: &lt;YOUR_API_KEY&gt;</code>
+            </div>
+          </section>
+
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-parameters-heading"
+          >
+            <p className="public-eyebrow">REQUEST</p>
+            <h2
+              id="api-parameters-heading"
+              className="api-detail-section-title"
+            >
+              参数
+            </h2>
+            {detail.parameters.length ? (
+              <div className="api-table-scroll">
+                <table className="api-detail-table">
+                  <thead>
+                    <tr>
+                      <th scope="col">名称</th>
+                      <th scope="col">位置</th>
+                      <th scope="col">必填</th>
+                      <th scope="col">类型 / 说明</th>
+                    </tr>
+                  </thead>
+                  <tbody>
+                    {detail.parameters.map((parameter, index) => {
+                      const schema = asRecord(parameter.schema)
+                      const name = asText(parameter.name, `参数 ${index + 1}`)
+                      const schemaText = asText(schema?.type, "—")
+                      const description = asText(parameter.description, "")
+                      return (
+                        <tr
+                          key={`${name}-${asText(parameter.in, "unknown")}-${index}`}
+                        >
+                          <th scope="row">
+                            <code>{name}</code>
+                          </th>
+                          <td>{asText(parameter.in)}</td>
+                          <td>{parameter.required === true ? "是" : "否"}</td>
+                          <td>
+                            <span>{schemaText}</span>
+                            {description ? (
+                              <span className="api-table-note">
+                                {description}
+                              </span>
+                            ) : null}
+                          </td>
+                        </tr>
+                      )
+                    })}
+                  </tbody>
+                </table>
+              </div>
+            ) : (
+              <p className="api-detail-muted">该接口不接受参数。</p>
+            )}
+          </section>
+
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-response-heading"
+          >
+            <p className="public-eyebrow">RESPONSE</p>
+            <h2 id="api-response-heading" className="api-detail-section-title">
+              响应结构
+            </h2>
+            {responseFields.length ? (
+              <div className="api-response-fields">
+                {responseFields.map(([name, schema]) => (
+                  <div key={name} className="api-response-field">
+                    <code>{name}</code>
+                    <span>{asText(schema.type, "object")}</span>
+                    {schema.format ? (
+                      <span>{asText(schema.format)}</span>
+                    ) : null}
+                  </div>
+                ))}
+              </div>
+            ) : null}
+            <pre className="api-json-block">
+              <code>{formatMetadata(detail.response_schema)}</code>
+            </pre>
+          </section>
+
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-errors-heading"
+          >
+            <p className="public-eyebrow">ERRORS</p>
+            <h2 id="api-errors-heading" className="api-detail-section-title">
+              错误码
+            </h2>
+            {detail.errors.length ? (
+              <div className="api-table-scroll">
+                <table className="api-detail-table">
+                  <thead>
+                    <tr>
+                      <th scope="col">HTTP</th>
+                      <th scope="col">错误码</th>
+                      <th scope="col">说明</th>
+                    </tr>
+                  </thead>
+                  <tbody>
+                    {detail.errors.map((error, index) => (
+                      <tr key={`${asText(error.code, "error")}-${index}`}>
+                        <td>{asText(error.status)}</td>
+                        <th scope="row">
+                          <code>{asText(error.code)}</code>
+                        </th>
+                        <td>
+                          {asText(error.description, asText(error.message))}
+                        </td>
+                      </tr>
+                    ))}
+                  </tbody>
+                </table>
+              </div>
+            ) : (
+              <p className="api-detail-muted">目录暂未提供错误码说明。</p>
+            )}
+          </section>
+
+          <section
+            className="api-detail-section"
+            aria-labelledby="api-examples-heading"
+          >
+            <p className="public-eyebrow">EXAMPLES</p>
+            <h2 id="api-examples-heading" className="api-detail-section-title">
+              安全调用示例
+            </h2>
+            <p className="api-detail-copy">
+              示例只使用占位密钥，不会读取或保存浏览器中的真实凭据。
+            </p>
+            <div className="api-code-grid">
+              <CodeExample language="curl" code={examples.curl} />
+              <CodeExample language="JavaScript" code={examples.javascript} />
+              <CodeExample language="Python" code={examples.python} />
+            </div>
+          </section>
+        </main>
+
+        <aside className="api-detail-aside" aria-label="接口补充信息">
+          <section
+            className="api-aside-card"
+            aria-labelledby="api-source-heading"
+          >
+            <p className="public-eyebrow">SOURCE</p>
+            <h2 id="api-source-heading" className="api-aside-title">
+              来源
+            </h2>
+            <p className="api-aside-value">{detail.source}</p>
+          </section>
+          <section
+            className="api-aside-card"
+            aria-labelledby="api-cache-heading"
+          >
+            <p className="public-eyebrow">CACHE</p>
+            <h2 id="api-cache-heading" className="api-aside-title">
+              缓存规则
+            </h2>
+            <dl className="api-cache-list">
+              {cacheEntries.map(([key, value]) => (
+                <div key={key}>
+                  <dt>{readableCacheKey(key)}</dt>
+                  <dd>{formatMetadata(value)}</dd>
+                </div>
+              ))}
+            </dl>
+          </section>
+        </aside>
+      </div>
+    </div>
+  )
+}
+
+export default ApiDetailView
diff --git a/frontend/src/components/ApiCatalog/CatalogCard.tsx b/frontend/src/components/ApiCatalog/CatalogCard.tsx
new file mode 100644
index 0000000..5b3c94e
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogCard.tsx
@@ -0,0 +1,42 @@
+import { Link } from "@tanstack/react-router"
+
+import type { CatalogItem } from "@/client"
+
+import { formatUpdatedAt } from "./catalog-types"
+
+interface CatalogCardProps {
+  item: CatalogItem
+}
+
+export function CatalogCard({ item }: CatalogCardProps) {
+  return (
+    <article className="catalog-card" data-testid={`catalog-card-${item.slug}`}>
+      <div className="catalog-card-path">
+        <span className="catalog-method-badge">{item.method}</span>
+        <code>{item.path}</code>
+      </div>
+      <div className="catalog-card-content">
+        <Link
+          to="/catalog/$slug"
+          params={{ slug: item.slug }}
+          className="catalog-card-title"
+        >
+          {item.name}
+        </Link>
+        <p className="catalog-card-summary">{item.summary}</p>
+      </div>
+      <div className="catalog-card-meta">
+        <span className="catalog-tag">{item.category}</span>
+        {item.is_free ? (
+          <span className="catalog-tag catalog-tag-free">免费</span>
+        ) : null}
+        <span className="catalog-tag catalog-tag-status">{item.status}</span>
+        <time dateTime={item.updated_at ?? undefined}>
+          更新于 {formatUpdatedAt(item.updated_at)}
+        </time>
+      </div>
+    </article>
+  )
+}
+
+export default CatalogCard
diff --git a/frontend/src/components/ApiCatalog/CatalogFilters.tsx b/frontend/src/components/ApiCatalog/CatalogFilters.tsx
new file mode 100644
index 0000000..2df3a59
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogFilters.tsx
@@ -0,0 +1,72 @@
+import type { CatalogItem } from "@/client"
+
+import { uniqueCatalogValues } from "./catalog-types"
+
+interface CatalogFiltersProps {
+  items: CatalogItem[]
+  category?: string
+  status?: string
+  onCategoryChange: (value: string) => void
+  onStatusChange: (value: string) => void
+}
+
+export function CatalogFilters({
+  items,
+  category,
+  status,
+  onCategoryChange,
+  onStatusChange,
+}: CatalogFiltersProps) {
+  const categories = uniqueCatalogValues(items, "category", category)
+  const statuses = uniqueCatalogValues(items, "status", status)
+
+  return (
+    <section
+      className="catalog-filters"
+      aria-labelledby="catalog-filter-heading"
+    >
+      <div>
+        <p className="public-eyebrow">筛选</p>
+        <h2 id="catalog-filter-heading" className="catalog-filter-title">
+          缩小公开接口范围
+        </h2>
+      </div>
+      <div className="catalog-filter-controls">
+        <div className="catalog-filter-field">
+          <label htmlFor="catalog-category">分类</label>
+          <select
+            id="catalog-category"
+            aria-label="分类"
+            value={category ?? ""}
+            onChange={(event) => onCategoryChange(event.target.value)}
+          >
+            <option value="">全部分类</option>
+            {categories.map((value) => (
+              <option key={value} value={value}>
+                {value}
+              </option>
+            ))}
+          </select>
+        </div>
+        <div className="catalog-filter-field">
+          <label htmlFor="catalog-status">状态</label>
+          <select
+            id="catalog-status"
+            aria-label="状态"
+            value={status ?? ""}
+            onChange={(event) => onStatusChange(event.target.value)}
+          >
+            <option value="">全部状态</option>
+            {statuses.map((value) => (
+              <option key={value} value={value}>
+                {value}
+              </option>
+            ))}
+          </select>
+        </div>
+      </div>
+    </section>
+  )
+}
+
+export default CatalogFilters
diff --git a/frontend/src/components/ApiCatalog/CatalogGrid.tsx b/frontend/src/components/ApiCatalog/CatalogGrid.tsx
new file mode 100644
index 0000000..86425a4
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogGrid.tsx
@@ -0,0 +1,19 @@
+import type { CatalogItem } from "@/client"
+
+import CatalogCard from "./CatalogCard"
+
+interface CatalogGridProps {
+  items: CatalogItem[]
+}
+
+export function CatalogGrid({ items }: CatalogGridProps) {
+  return (
+    <div className="catalog-grid" data-testid="catalog-grid">
+      {items.map((item) => (
+        <CatalogCard key={item.slug} item={item} />
+      ))}
+    </div>
+  )
+}
+
+export default CatalogGrid
diff --git a/frontend/src/components/ApiCatalog/CatalogSearch.tsx b/frontend/src/components/ApiCatalog/CatalogSearch.tsx
new file mode 100644
index 0000000..a625b17
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogSearch.tsx
@@ -0,0 +1,53 @@
+import { Search, X } from "lucide-react"
+
+interface CatalogSearchProps {
+  value: string
+  onChange: (value: string) => void
+}
+
+export function CatalogSearch({ value, onChange }: CatalogSearchProps) {
+  return (
+    <section
+      className="catalog-search-panel"
+      aria-labelledby="catalog-search-heading"
+    >
+      <div className="catalog-search-heading">
+        <div>
+          <p className="public-eyebrow">搜索优先</p>
+          <h2 id="catalog-search-heading" className="catalog-search-title">
+            先按接口名、简介或路径查找
+          </h2>
+        </div>
+        <p className="catalog-search-hint">输入停止后约 400ms 更新目录</p>
+      </div>
+      <div className="catalog-search-control">
+        <Search aria-hidden="true" className="catalog-search-icon" />
+        <label className="sr-only" htmlFor="catalog-search-input">
+          搜索公开 API
+        </label>
+        <input
+          id="catalog-search-input"
+          data-testid="catalog-search-input"
+          className="catalog-search-input"
+          type="search"
+          value={value}
+          onChange={(event) => onChange(event.target.value)}
+          placeholder="例如：时间、UUID、工具"
+          autoComplete="off"
+        />
+        {value ? (
+          <button
+            type="button"
+            className="catalog-search-clear"
+            aria-label="清除搜索"
+            onClick={() => onChange("")}
+          >
+            <X aria-hidden="true" />
+          </button>
+        ) : null}
+      </div>
+    </section>
+  )
+}
+
+export default CatalogSearch
diff --git a/frontend/src/components/ApiCatalog/CatalogStates.tsx b/frontend/src/components/ApiCatalog/CatalogStates.tsx
new file mode 100644
index 0000000..760889d
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CatalogStates.tsx
@@ -0,0 +1,64 @@
+interface CatalogErrorStateProps {
+  onRetry: () => void
+}
+
+export function CatalogLoadingState() {
+  return (
+    <div
+      className="catalog-state catalog-skeleton-list"
+      data-testid="catalog-loading"
+      role="status"
+      aria-label="正在加载公开目录"
+    >
+      <span className="catalog-skeleton-line catalog-skeleton-line-wide" />
+      <span className="catalog-skeleton-line" />
+      <span className="catalog-skeleton-line catalog-skeleton-line-short" />
+      <span className="sr-only">正在读取真实目录……</span>
+    </div>
+  )
+}
+
+export function CatalogErrorState({ onRetry }: CatalogErrorStateProps) {
+  return (
+    <div
+      className="catalog-state catalog-state-error"
+      data-testid="catalog-error"
+      role="alert"
+    >
+      <div>
+        <p className="catalog-state-kicker">目录读取失败</p>
+        <p>公开目录暂时无法读取，请稍后重试。</p>
+      </div>
+      <button type="button" className="public-inline-button" onClick={onRetry}>
+        重试
+      </button>
+    </div>
+  )
+}
+
+export function CatalogEmptyState() {
+  return (
+    <div className="catalog-state" data-testid="catalog-empty" role="status">
+      <p className="catalog-state-kicker">没有匹配结果</p>
+      <p>没有找到匹配的公开接口，请换一个关键词或清除筛选。</p>
+    </div>
+  )
+}
+
+export function CatalogDetailErrorState({ onRetry }: CatalogErrorStateProps) {
+  return (
+    <div
+      className="catalog-state catalog-state-error"
+      data-testid="catalog-detail-error"
+      role="alert"
+    >
+      <div>
+        <p className="catalog-state-kicker">详情读取失败</p>
+        <p>该接口可能已下线，或目录服务暂时不可用。</p>
+      </div>
+      <button type="button" className="public-inline-button" onClick={onRetry}>
+        重试
+      </button>
+    </div>
+  )
+}
diff --git a/frontend/src/components/ApiCatalog/CodeExample.tsx b/frontend/src/components/ApiCatalog/CodeExample.tsx
new file mode 100644
index 0000000..bcec275
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/CodeExample.tsx
@@ -0,0 +1,67 @@
+import { Check, Copy } from "lucide-react"
+import { useState } from "react"
+
+interface CodeExampleProps {
+  language: string
+  code: string
+}
+
+function codeId(language: string) {
+  return language.toLowerCase().replace(/[^a-z0-9]+/g, "-")
+}
+
+export function CodeExample({ language, code }: CodeExampleProps) {
+  const [copyState, setCopyState] = useState<"idle" | "success" | "error">(
+    "idle",
+  )
+  const headingId = `code-example-${codeId(language)}`
+
+  const copyCode = async () => {
+    if (!navigator.clipboard) {
+      setCopyState("error")
+      return
+    }
+
+    try {
+      await navigator.clipboard.writeText(code)
+      setCopyState("success")
+    } catch {
+      setCopyState("error")
+    }
+  }
+
+  const buttonLabel = copyState === "success" ? "已复制" : "复制"
+
+  return (
+    <section className="code-example" aria-labelledby={headingId}>
+      <div className="code-example-header">
+        <h3 id={headingId}>{language}</h3>
+        <button
+          type="button"
+          className="code-copy-button"
+          aria-label={`复制 ${language} 示例`}
+          onClick={() => void copyCode()}
+        >
+          {copyState === "success" ? (
+            <Check aria-hidden="true" />
+          ) : (
+            <Copy aria-hidden="true" />
+          )}
+          <span>{buttonLabel}</span>
+        </button>
+      </div>
+      <pre className="code-example-block">
+        <code>{code}</code>
+      </pre>
+      <p className="code-example-feedback" aria-live="polite">
+        {copyState === "success"
+          ? `${language} 示例已复制到剪贴板。`
+          : copyState === "error"
+            ? "复制失败，请手动选择代码。"
+            : ""}
+      </p>
+    </section>
+  )
+}
+
+export default CodeExample
diff --git a/frontend/src/components/ApiCatalog/catalog-types.ts b/frontend/src/components/ApiCatalog/catalog-types.ts
new file mode 100644
index 0000000..16a7477
--- /dev/null
+++ b/frontend/src/components/ApiCatalog/catalog-types.ts
@@ -0,0 +1,89 @@
+import type { ApiDetail, CatalogItem } from "@/client"
+
+export type CatalogSearchParams = {
+  query?: string
+  category?: string
+  status?: string
+}
+
+export type CatalogMetadata = Record<string, unknown>
+
+export function normalizeSearchValue(value: unknown): string | undefined {
+  if (typeof value !== "string") return undefined
+  const normalized = value.trim()
+  return normalized || undefined
+}
+
+export function parseCatalogSearch(
+  search: Record<string, unknown>,
+): CatalogSearchParams {
+  return {
+    query: normalizeSearchValue(search.query),
+    category: normalizeSearchValue(search.category),
+    status: normalizeSearchValue(search.status),
+  }
+}
+
+export function formatUpdatedAt(value?: string | null): string {
+  if (!value) return "更新时间待补充"
+
+  const timestamp = Date.parse(value)
+  if (Number.isNaN(timestamp)) return value
+
+  return new Intl.DateTimeFormat("zh-HK", {
+    dateStyle: "medium",
+  }).format(new Date(timestamp))
+}
+
+export function asRecord(value: unknown): CatalogMetadata | undefined {
+  if (typeof value !== "object" || value === null || Array.isArray(value)) {
+    return undefined
+  }
+  return value as CatalogMetadata
+}
+
+export function asText(value: unknown, fallback = "—"): string {
+  if (typeof value === "string") return value
+  if (typeof value === "number" || typeof value === "boolean") {
+    return String(value)
+  }
+  return fallback
+}
+
+export function formatMetadata(value: unknown): string {
+  if (value === null || value === undefined) return "—"
+  if (typeof value === "string") return value
+  if (typeof value === "number" || typeof value === "boolean") {
+    return String(value)
+  }
+
+  try {
+    return JSON.stringify(value, null, 2) ?? "无法展示"
+  } catch {
+    return "无法展示"
+  }
+}
+
+export function responseProperties(
+  detail: ApiDetail,
+): Array<[string, CatalogMetadata]> {
+  const properties = asRecord(detail.response_schema)?.properties
+  if (!properties || typeof properties !== "object") return []
+
+  return Object.entries(properties)
+    .map(
+      ([name, value]) =>
+        [name, asRecord(value) ?? {}] as [string, CatalogMetadata],
+    )
+    .sort(([left], [right]) => left.localeCompare(right))
+}
+
+export function uniqueCatalogValues(
+  items: CatalogItem[],
+  field: "category" | "status",
+  currentValue?: string,
+): string[] {
+  const values = new Set(items.map((item) => item[field]).filter(Boolean))
+  if (currentValue) values.add(currentValue)
+  return Array.from(values).sort((left, right) => left.localeCompare(right))
+}
diff --git a/frontend/src/components/PublicSite/PublicFooter.tsx b/frontend/src/components/PublicSite/PublicFooter.tsx
index 15a05ca..192e8b8 100644
--- a/frontend/src/components/PublicSite/PublicFooter.tsx
+++ b/frontend/src/components/PublicSite/PublicFooter.tsx
@@ -8,23 +8,23 @@ export function PublicFooter() {
       <div className="public-container flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
         <div>
           <p className="font-semibold text-[var(--yeyu-ink)]">
             Yeyu API 公益平台
           </p>
           <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
             面向学生与个人开发者的公开工具目录 · {currentYear}
           </p>
         </div>
         <nav aria-label="页脚导航" className="flex flex-wrap gap-4 text-sm">
-          <a className="public-footer-link" href="/catalog">
+          <Link className="public-footer-link" to="/catalog">
             API 目录
-          </a>
+          </Link>
           <Link className="public-footer-link" to="/" hash="usage">
             使用规范
           </Link>
           <Link className="public-footer-link" to="/login">
             登录
           </Link>
         </nav>
       </div>
     </footer>
   )
diff --git a/frontend/src/components/PublicSite/PublicHeader.tsx b/frontend/src/components/PublicSite/PublicHeader.tsx
index e6daf45..4a2d6d2 100644
--- a/frontend/src/components/PublicSite/PublicHeader.tsx
+++ b/frontend/src/components/PublicSite/PublicHeader.tsx
@@ -11,23 +11,23 @@ interface NavigationLinksProps {
 
 function NavigationLinks({ onNavigate }: NavigationLinksProps) {
   const linkClassName =
     "public-nav-link rounded-md px-3 py-2 text-sm font-medium"
 
   return (
     <>
       <Link to="/" className={linkClassName} onClick={onNavigate}>
         首页
       </Link>
-      <a href="/catalog" className={linkClassName} onClick={onNavigate}>
+      <Link to="/catalog" className={linkClassName} onClick={onNavigate}>
         API 目录
-      </a>
+      </Link>
       <Link to="/" hash="usage" className={linkClassName} onClick={onNavigate}>
         使用规范
       </Link>
       {isLoggedIn() ? (
         <Link
           to="/dashboard"
           className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
           onClick={onNavigate}
         >
           控制台
diff --git a/frontend/src/index.css b/frontend/src/index.css
index a042441..4cd1214 100644
--- a/frontend/src/index.css
+++ b/frontend/src/index.css
@@ -545,43 +545,688 @@
   width: 1.75rem;
   align-items: center;
   justify-content: center;
   border-radius: 0.25rem;
   background: var(--yeyu-teal);
   color: #ffffff;
   font-size: 0.85em;
   font-weight: 800;
 }
 
+.public-catalog-title-link {
+  color: inherit;
+  text-decoration: none;
+  text-underline-offset: 0.2rem;
+}
+
+.public-catalog-title-link:hover {
+  color: var(--yeyu-teal);
+  text-decoration: underline;
+}
+
+.catalog-page-shell,
+.catalog-detail-shell {
+  padding-block: clamp(3rem, 7vw, 6rem);
+}
+
+.catalog-page-header {
+  max-width: 48rem;
+  padding-bottom: 2.5rem;
+}
+
+.catalog-page-title {
+  margin-top: 0.85rem;
+  color: var(--yeyu-ink);
+  font-size: clamp(2.75rem, 7vw, 5.25rem);
+  font-weight: 700;
+  letter-spacing: -0.06em;
+  line-height: 0.98;
+}
+
+.catalog-page-lede {
+  max-width: 42rem;
+  margin-top: 1.25rem;
+  color: var(--yeyu-muted);
+  font-size: 1.05rem;
+  line-height: 1.8;
+}
+
+.catalog-search-panel,
+.catalog-filters {
+  display: grid;
+  gap: 1.25rem;
+  padding: 1.25rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+}
+
+.catalog-search-panel {
+  margin-top: 0.5rem;
+}
+
+.catalog-search-heading,
+.catalog-results-heading {
+  display: flex;
+  align-items: end;
+  justify-content: space-between;
+  gap: 1rem;
+}
+
+.catalog-search-title,
+.catalog-filter-title,
+.catalog-results-title {
+  margin-top: 0.45rem;
+  color: var(--yeyu-ink);
+  font-size: 1.25rem;
+  font-weight: 700;
+  letter-spacing: -0.025em;
+}
+
+.catalog-search-hint,
+.catalog-results-count,
+.catalog-refreshing {
+  color: var(--yeyu-muted);
+  font-size: 0.8rem;
+}
+
+.catalog-search-control {
+  display: flex;
+  min-width: 0;
+  align-items: center;
+  gap: 0.7rem;
+  min-height: 3.25rem;
+  padding-inline: 1rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper);
+}
+
+.catalog-search-icon {
+  flex: 0 0 auto;
+  color: var(--yeyu-teal);
+}
+
+.catalog-search-input {
+  min-width: 0;
+  flex: 1;
+  border: 0;
+  outline: 0;
+  background: transparent;
+  color: var(--yeyu-ink);
+}
+
+.catalog-search-input::placeholder {
+  color: var(--yeyu-muted);
+}
+
+.catalog-search-clear {
+  display: inline-flex;
+  height: 2rem;
+  width: 2rem;
+  flex: 0 0 auto;
+  align-items: center;
+  justify-content: center;
+  border: 1px solid var(--yeyu-line);
+  color: var(--yeyu-muted);
+}
+
+.catalog-search-clear svg {
+  height: 1rem;
+  width: 1rem;
+}
+
+.catalog-filters {
+  grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr);
+  margin-top: 1rem;
+  background: var(--yeyu-mint);
+}
+
+.catalog-filter-controls {
+  display: grid;
+  grid-template-columns: repeat(2, minmax(0, 1fr));
+  gap: 0.75rem;
+}
+
+.catalog-filter-field {
+  display: grid;
+  gap: 0.35rem;
+}
+
+.catalog-filter-field label {
+  color: var(--yeyu-muted);
+  font-size: 0.78rem;
+  font-weight: 700;
+}
+
+.catalog-filter-field select {
+  min-height: 2.75rem;
+  min-width: 0;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.25rem;
+  background: var(--yeyu-paper-strong);
+  padding-inline: 0.75rem;
+  color: var(--yeyu-ink);
+}
+
+.catalog-results {
+  margin-top: clamp(3rem, 6vw, 5rem);
+  padding-top: 2rem;
+  border-top: 1px solid var(--yeyu-line);
+}
+
+.catalog-refreshing {
+  margin-top: 1rem;
+}
+
+.catalog-grid {
+  display: grid;
+  grid-template-columns: repeat(2, minmax(0, 1fr));
+  gap: 1rem;
+  margin-top: 1.25rem;
+}
+
+.catalog-card {
+  display: grid;
+  min-width: 0;
+  gap: 1.1rem;
+  padding: 1.25rem;
+  border: 1px solid var(--yeyu-line);
+  border-top: 3px solid var(--yeyu-teal);
+  background: var(--yeyu-paper-strong);
+  transition:
+    border-color 160ms ease,
+    box-shadow 160ms ease,
+    transform 160ms ease;
+}
+
+.catalog-card:hover {
+  border-color: var(--yeyu-teal);
+  box-shadow: 0 10px 24px rgb(23 33 31 / 8%);
+  transform: translateY(-2px);
+}
+
+.catalog-card-path,
+.api-detail-path-row {
+  display: flex;
+  min-width: 0;
+  align-items: center;
+  gap: 0.65rem;
+  overflow-x: auto;
+  color: var(--yeyu-ink);
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  font-size: 0.85rem;
+  white-space: nowrap;
+}
+
+.catalog-card-path code,
+.api-detail-path-row code {
+  overflow: visible;
+}
+
+.catalog-method-badge {
+  flex: 0 0 auto;
+  color: var(--yeyu-teal);
+  font-size: 0.72rem;
+  font-weight: 800;
+  letter-spacing: 0.08em;
+}
+
+.catalog-card-content {
+  min-width: 0;
+}
+
+.catalog-card-title {
+  display: inline-block;
+  max-width: 100%;
+  overflow: hidden;
+  color: var(--yeyu-ink);
+  font-size: 1.2rem;
+  font-weight: 700;
+  text-overflow: ellipsis;
+  text-decoration: none;
+  white-space: nowrap;
+}
+
+.catalog-card-title:hover {
+  color: var(--yeyu-teal);
+  text-decoration: underline;
+  text-underline-offset: 0.2rem;
+}
+
+.catalog-card-summary {
+  margin-top: 0.5rem;
+  color: var(--yeyu-muted);
+  line-height: 1.65;
+}
+
+.catalog-card-meta,
+.api-detail-tags {
+  display: flex;
+  flex-wrap: wrap;
+  align-items: center;
+  gap: 0.45rem 0.6rem;
+  color: var(--yeyu-muted);
+  font-size: 0.76rem;
+}
+
+.catalog-tag {
+  display: inline-flex;
+  align-items: center;
+  min-height: 1.65rem;
+  padding-inline: 0.5rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper);
+  color: var(--yeyu-muted);
+  font-size: 0.72rem;
+  font-weight: 700;
+}
+
+.catalog-tag-free {
+  border-color: var(--yeyu-teal);
+  color: var(--yeyu-teal);
+}
+
+.catalog-tag-status {
+  border-color: rgb(180 83 9 / 38%);
+  color: var(--yeyu-amber);
+}
+
+.catalog-state {
+  display: grid;
+  gap: 0.35rem;
+  margin-top: 1.25rem;
+  padding: 1.25rem;
+  border: 1px dashed var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-muted);
+  line-height: 1.65;
+}
+
+.catalog-state-error {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+  border-color: var(--yeyu-amber);
+}
+
+.catalog-state-kicker {
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.catalog-skeleton-list {
+  min-height: 12rem;
+  align-content: center;
+}
+
+.catalog-skeleton-line {
+  display: block;
+  width: 68%;
+  height: 0.8rem;
+  background: var(--yeyu-mint);
+}
+
+.catalog-skeleton-line-wide {
+  width: 92%;
+  height: 1.4rem;
+}
+
+.catalog-skeleton-line-short {
+  width: 42%;
+}
+
+.catalog-detail-shell {
+  max-width: 86rem;
+}
+
+.api-detail-page {
+  min-width: 0;
+}
+
+.api-detail-breadcrumbs {
+  display: flex;
+  flex-wrap: wrap;
+  align-items: center;
+  gap: 0.65rem;
+  color: var(--yeyu-muted);
+  font-size: 0.82rem;
+}
+
+.api-detail-header {
+  max-width: 58rem;
+  padding-block: 2.25rem 3rem;
+}
+
+.api-detail-title {
+  margin-top: 1rem;
+  color: var(--yeyu-ink);
+  font-size: clamp(2.35rem, 6vw, 4.75rem);
+  font-weight: 700;
+  letter-spacing: -0.055em;
+  line-height: 1;
+}
+
+.api-detail-summary {
+  max-width: 48rem;
+  margin-top: 1rem;
+  color: var(--yeyu-muted);
+  font-size: 1.05rem;
+  line-height: 1.8;
+}
+
+.api-detail-tags {
+  margin-top: 1.25rem;
+}
+
+.api-detail-layout {
+  display: grid;
+  grid-template-columns: minmax(0, 1fr) minmax(15rem, 20rem);
+  gap: clamp(2rem, 6vw, 5rem);
+  align-items: start;
+}
+
+.api-detail-main {
+  min-width: 0;
+}
+
+.api-detail-section {
+  min-width: 0;
+  padding-block: 2.25rem;
+  border-top: 1px solid var(--yeyu-line);
+}
+
+.api-detail-section-title {
+  margin-top: 0.55rem;
+  color: var(--yeyu-ink);
+  font-size: 1.5rem;
+  font-weight: 700;
+  letter-spacing: -0.03em;
+}
+
+.api-detail-copy {
+  max-width: 52rem;
+  margin-top: 0.85rem;
+  color: var(--yeyu-muted);
+  line-height: 1.75;
+}
+
+.api-auth-callout {
+  display: flex;
+  flex-wrap: wrap;
+  align-items: center;
+  justify-content: space-between;
+  gap: 0.75rem;
+  margin-top: 1.25rem;
+  padding: 0.85rem 1rem;
+  border-left: 3px solid var(--yeyu-amber);
+  background: var(--yeyu-mint);
+  color: var(--yeyu-muted);
+  font-size: 0.82rem;
+}
+
+.api-auth-callout code {
+  overflow-x: auto;
+  color: var(--yeyu-ink);
+  white-space: nowrap;
+}
+
+.api-table-scroll {
+  max-width: 100%;
+  margin-top: 1.25rem;
+  overflow-x: auto;
+  border: 1px solid var(--yeyu-line);
+}
+
+.api-detail-table {
+  width: 100%;
+  min-width: 38rem;
+  border-collapse: collapse;
+  color: var(--yeyu-muted);
+  font-size: 0.86rem;
+  text-align: left;
+}
+
+.api-detail-table th,
+.api-detail-table td {
+  padding: 0.85rem 1rem;
+  border-bottom: 1px solid var(--yeyu-line);
+  vertical-align: top;
+}
+
+.api-detail-table thead th {
+  background: var(--yeyu-mint);
+  color: var(--yeyu-ink);
+  font-size: 0.75rem;
+  font-weight: 800;
+  letter-spacing: 0.05em;
+}
+
+.api-detail-table tbody th {
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.api-detail-table tr:last-child th,
+.api-detail-table tr:last-child td {
+  border-bottom: 0;
+}
+
+.api-table-note {
+  display: block;
+  max-width: 28rem;
+  margin-top: 0.35rem;
+  line-height: 1.55;
+}
+
+.api-detail-muted {
+  margin-top: 1rem;
+  color: var(--yeyu-muted);
+}
+
+.api-response-fields {
+  display: grid;
+  grid-template-columns: repeat(2, minmax(0, 1fr));
+  gap: 0.5rem;
+  margin-top: 1.25rem;
+}
+
+.api-response-field {
+  display: flex;
+  min-width: 0;
+  flex-wrap: wrap;
+  gap: 0.5rem;
+  align-items: center;
+  justify-content: space-between;
+  padding: 0.7rem 0.8rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-muted);
+  font-size: 0.8rem;
+}
+
+.api-response-field code {
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.api-json-block,
+.code-example-block {
+  max-width: 100%;
+  margin-top: 1rem;
+  overflow-x: auto;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-ink);
+  padding: 1rem;
+  color: #eaf5f0;
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  font-size: 0.78rem;
+  line-height: 1.7;
+  white-space: pre;
+}
+
+.api-detail-aside {
+  display: grid;
+  gap: 1rem;
+  position: sticky;
+  top: 1.5rem;
+}
+
+.api-aside-card {
+  padding: 1.25rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+}
+
+.api-aside-title {
+  margin-top: 0.55rem;
+  color: var(--yeyu-ink);
+  font-size: 1.1rem;
+  font-weight: 700;
+}
+
+.api-aside-value {
+  margin-top: 0.85rem;
+  color: var(--yeyu-teal);
+  font-weight: 700;
+}
+
+.api-cache-list {
+  display: grid;
+  gap: 0.75rem;
+  margin-top: 1rem;
+}
+
+.api-cache-list > div {
+  display: flex;
+  justify-content: space-between;
+  gap: 0.75rem;
+  padding-top: 0.75rem;
+  border-top: 1px solid var(--yeyu-line);
+  color: var(--yeyu-muted);
+  font-size: 0.8rem;
+}
+
+.api-cache-list dt {
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.api-cache-list dd {
+  max-width: 9rem;
+  overflow-wrap: anywhere;
+  text-align: right;
+}
+
+.api-code-grid {
+  display: grid;
+  gap: 1rem;
+  margin-top: 1.25rem;
+}
+
+.code-example {
+  min-width: 0;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+}
+
+.code-example-header {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+  padding: 0.75rem 1rem;
+  border-bottom: 1px solid var(--yeyu-line);
+}
+
+.code-example-header h3 {
+  color: var(--yeyu-ink);
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  font-size: 0.82rem;
+  font-weight: 800;
+}
+
+.code-copy-button {
+  display: inline-flex;
+  min-height: 2.25rem;
+  align-items: center;
+  gap: 0.4rem;
+  border: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper);
+  padding: 0.4rem 0.65rem;
+  color: var(--yeyu-teal);
+  font-size: 0.78rem;
+  font-weight: 700;
+}
+
+.code-copy-button svg {
+  height: 0.9rem;
+  width: 0.9rem;
+}
+
+.code-example-block {
+  margin-top: 0;
+  border: 0;
+}
+
+.code-example-feedback {
+  min-height: 1.5rem;
+  padding: 0 1rem 0.65rem;
+  color: var(--yeyu-teal);
+  font-size: 0.75rem;
+}
+
 @media (min-width: 768px) {
   .public-hero {
     grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.65fr);
     align-items: end;
   }
 }
 
 @media (max-width: 767px) {
   .public-section-heading,
+  .catalog-search-heading,
+  .catalog-results-heading,
   .public-bottom-cta {
     align-items: flex-start;
     flex-direction: column;
   }
 
   .public-catalog-row,
-  .public-usage-section {
+  .public-usage-section,
+  .catalog-filters,
+  .catalog-filter-controls,
+  .api-detail-layout {
     grid-template-columns: 1fr;
   }
 
+  .catalog-grid,
+  .api-response-fields {
+    grid-template-columns: 1fr;
+  }
+
+  .catalog-search-hint {
+    margin-top: -0.5rem;
+  }
+
   .public-catalog-meta {
     justify-content: flex-start;
     text-align: left;
   }
+
+  .api-detail-aside {
+    position: static;
+  }
+
+  .api-auth-callout {
+    align-items: flex-start;
+    flex-direction: column;
+  }
 }
 
 @media (prefers-reduced-motion: reduce) {
   *,
   *::before,
   *::after {
     scroll-behavior: auto;
     transition: none;
     animation: none;
   }
diff --git a/frontend/src/routes/catalog/$slug.tsx b/frontend/src/routes/catalog/$slug.tsx
new file mode 100644
index 0000000..5c51950
--- /dev/null
+++ b/frontend/src/routes/catalog/$slug.tsx
@@ -0,0 +1,46 @@
+import { useQuery } from "@tanstack/react-query"
+import { createFileRoute } from "@tanstack/react-router"
+
+import { CatalogService } from "@/client"
+import ApiDetailView from "@/components/ApiCatalog/ApiDetailView"
+import {
+  CatalogDetailErrorState,
+  CatalogLoadingState,
+} from "@/components/ApiCatalog/CatalogStates"
+import PublicLayout from "@/components/PublicSite/PublicLayout"
+
+export const Route = createFileRoute("/catalog/$slug")({
+  component: CatalogDetailRoute,
+  head: () => ({
+    meta: [
+      {
+        title: "API 详情 - Yeyu API",
+      },
+    ],
+  }),
+})
+
+function CatalogDetailRoute() {
+  const { slug } = Route.useParams()
+  const detailQuery = useQuery({
+    queryKey: ["public-catalog-detail", slug],
+    queryFn: async () => {
+      const response = await CatalogService.getCatalogDetail({
+        path: { slug },
+      })
+      return response.data
+    },
+  })
+
+  return (
+    <PublicLayout>
+      <div className="public-container catalog-detail-shell">
+        {detailQuery.isPending ? <CatalogLoadingState /> : null}
+        {detailQuery.isError ? (
+          <CatalogDetailErrorState onRetry={() => void detailQuery.refetch()} />
+        ) : null}
+        {detailQuery.data ? <ApiDetailView detail={detailQuery.data} /> : null}
+      </div>
+    </PublicLayout>
+  )
+}
diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
index a0084bb..f83b403 100644
--- a/frontend/src/routes/catalog/index.tsx
+++ b/frontend/src/routes/catalog/index.tsx
@@ -1,45 +1,155 @@
-import { createFileRoute, Link } from "@tanstack/react-router"
+import { useQuery } from "@tanstack/react-query"
+import { createFileRoute } from "@tanstack/react-router"
+import { useEffect, useState } from "react"
 
+import { type CatalogPage, CatalogService } from "@/client"
+import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
+import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
+import CatalogSearch from "@/components/ApiCatalog/CatalogSearch"
+import {
+  CatalogEmptyState,
+  CatalogErrorState,
+  CatalogLoadingState,
+} from "@/components/ApiCatalog/CatalogStates"
+import {
+  type CatalogSearchParams,
+  normalizeSearchValue,
+  parseCatalogSearch,
+} from "@/components/ApiCatalog/catalog-types"
 import PublicLayout from "@/components/PublicSite/PublicLayout"
 
 export const Route = createFileRoute("/catalog/")({
-  component: CatalogPlaceholder,
+  validateSearch: (search): CatalogSearchParams => parseCatalogSearch(search),
+  component: CatalogRoutePage,
   head: () => ({
     meta: [
       {
         title: "API 目录 - Yeyu API",
       },
     ],
   }),
 })
 
-function CatalogPlaceholder() {
+function CatalogRoutePage() {
+  const search = Route.useSearch()
+  const navigate = Route.useNavigate()
+  const [draftQuery, setDraftQuery] = useState(search.query ?? "")
+
+  useEffect(() => {
+    setDraftQuery(search.query ?? "")
+  }, [search.query])
+
+  useEffect(() => {
+    const normalizedQuery = normalizeSearchValue(draftQuery)
+    if (normalizedQuery === search.query) return
+
+    const timeoutId = window.setTimeout(() => {
+      void navigate({
+        search: (previous) => ({
+          ...previous,
+          query: normalizedQuery,
+        }),
+        replace: true,
+      })
+    }, 400)
+
+    return () => window.clearTimeout(timeoutId)
+  }, [draftQuery, navigate, search.query])
+
+  const catalogQuery = useQuery<CatalogPage>({
+    queryKey: [
+      "public-catalog",
+      search.query ?? "",
+      search.category ?? "",
+      search.status ?? "",
+    ],
+    queryFn: async () => {
+      const response = await CatalogService.searchCatalog({
+        query: {
+          query: search.query,
+          category: search.category,
+          status: search.status,
+          page: 1,
+          page_size: 20,
+        },
+      })
+      return response.data
+    },
+  })
+
+  const items = catalogQuery.data?.data ?? []
+  const updateFilter = (key: "category" | "status", value: string) => {
+    void navigate({
+      search: (previous) => ({
+        ...previous,
+        [key]: normalizeSearchValue(value),
+      }),
+      replace: true,
+    })
+  }
+
   return (
     <PublicLayout>
-      <div className="public-container py-16 sm:py-24">
+      <div className="public-container catalog-page-shell">
+        <header className="catalog-page-header">
+          <p className="public-eyebrow">公开目录 / REAL DATA</p>
+          <h1 className="catalog-page-title">API 目录</h1>
+          <p className="catalog-page-lede">
+            只展示后端公开、健康或已发布的真实接口。先搜索，再阅读完整调用契约。
+          </p>
+        </header>
+
+        <CatalogSearch value={draftQuery} onChange={setDraftQuery} />
+        <CatalogFilters
+          items={items}
+          category={search.category}
+          status={search.status}
+          onCategoryChange={(value) => updateFilter("category", value)}
+          onStatusChange={(value) => updateFilter("status", value)}
+        />
+
         <section
-          className="public-state mx-auto max-w-2xl text-center"
-          aria-labelledby="catalog-placeholder-heading"
-          data-testid="catalog-placeholder"
+          className="catalog-results"
+          aria-labelledby="catalog-results-heading"
         >
-          <p className="public-eyebrow">公开目录</p>
-          <h1
-            id="catalog-placeholder-heading"
-            className="public-section-title mt-3"
-          >
-            API 目录建设中
-          </h1>
-          <p className="public-section-copy mx-auto mt-4 max-w-xl">
-            由公开目录驱动的真实接口条目将在下一阶段开放，当前先保留清晰的公共入口。
-          </p>
-          <p className="mt-3 text-sm text-[var(--yeyu-muted)]">
-            目录建设中，请稍后再来查看。
-          </p>
-          <Link to="/" className="public-primary-button mt-8 inline-flex">
-            返回首页
-          </Link>
+          <div className="catalog-results-heading">
+            <div>
+              <p className="public-eyebrow">RESULTS</p>
+              <h2
+                id="catalog-results-heading"
+                className="catalog-results-title"
+              >
+                可用接口
+              </h2>
+            </div>
+            {catalogQuery.data ? (
+              <p className="catalog-results-count">
+                共 {catalogQuery.data.count} 条
+              </p>
+            ) : null}
+          </div>
+
+          {catalogQuery.isFetching && !catalogQuery.isPending ? (
+            <p className="catalog-refreshing" role="status">
+              正在更新目录……
+            </p>
+          ) : null}
+          {catalogQuery.isPending ? <CatalogLoadingState /> : null}
+          {catalogQuery.isError ? (
+            <CatalogErrorState onRetry={() => void catalogQuery.refetch()} />
+          ) : null}
+          {!catalogQuery.isPending &&
+          !catalogQuery.isError &&
+          items.length === 0 ? (
+            <CatalogEmptyState />
+          ) : null}
+          {!catalogQuery.isPending &&
+          !catalogQuery.isError &&
+          items.length > 0 ? (
+            <CatalogGrid items={items} />
+          ) : null}
         </section>
       </div>
     </PublicLayout>
   )
 }
diff --git a/frontend/src/routes/index.tsx b/frontend/src/routes/index.tsx
index ae23cfe..2067555 100644
--- a/frontend/src/routes/index.tsx
+++ b/frontend/src/routes/index.tsx
@@ -1,38 +1,28 @@
 import { useQuery } from "@tanstack/react-query"
 import { createFileRoute, Link } from "@tanstack/react-router"
 
 import { CatalogService } from "@/client"
+import { formatUpdatedAt } from "@/components/ApiCatalog/catalog-types"
 import PublicLayout from "@/components/PublicSite/PublicLayout"
 
 export const Route = createFileRoute("/")({
   component: PublicHome,
   head: () => ({
     meta: [
       {
         title: "Yeyu API 公益工具箱",
       },
     ],
   }),
 })
 
-function formatUpdatedAt(value?: string | null) {
-  if (!value) return "更新时间待补充"
-
-  const timestamp = Date.parse(value)
-  if (Number.isNaN(timestamp)) return value
-
-  return new Intl.DateTimeFormat("zh-HK", {
-    dateStyle: "medium",
-  }).format(new Date(timestamp))
-}
-
 function CatalogPreview() {
   const catalogQuery = useQuery({
     queryKey: ["public-catalog-preview"],
     queryFn: async () => {
       const response = await CatalogService.searchCatalog({
         query: {
           page: 1,
           page_size: 4,
         },
       })
@@ -51,23 +41,23 @@ function CatalogPreview() {
       <div className="public-section-heading">
         <div>
           <p className="public-eyebrow">目录入口</p>
           <h2 id="catalog-heading" className="public-section-title">
             从真实目录开始
           </h2>
           <p className="public-section-copy">
             这里展示后端公开目录中的接口，不展示虚构卡片或调用统计。
           </p>
         </div>
-        <a className="public-text-link" href="/catalog">
+        <Link className="public-text-link" to="/catalog">
           搜索完整目录 <span aria-hidden="true">→</span>
-        </a>
+        </Link>
       </div>
 
       {catalogQuery.isPending ? (
         <p className="public-state" role="status">
           正在读取真实目录……
         </p>
       ) : null}
 
       {catalogQuery.isError ? (
         <div className="public-state public-state-error" role="alert">
@@ -91,28 +81,36 @@ function CatalogPreview() {
       {!catalogQuery.isPending && !catalogQuery.isError && items.length > 0 ? (
         <ul className="public-catalog-list" data-testid="catalog-preview-list">
           {items.map((item) => (
             <li key={item.slug} className="public-catalog-row">
               <div className="public-path-line">
                 <span className="public-method-badge">{item.method}</span>
                 <code>{item.path}</code>
               </div>
               <div className="min-w-0">
                 <h3 className="truncate text-base font-semibold text-[var(--yeyu-ink)]">
-                  {item.name}
+                  <Link
+                    to="/catalog/$slug"
+                    params={{ slug: item.slug }}
+                    className="public-catalog-title-link"
+                  >
+                    {item.name}
+                  </Link>
                 </h3>
                 <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
                   {item.summary}
                 </p>
               </div>
               <div className="public-catalog-meta">
                 <span>{item.category}</span>
+                {item.is_free ? <span>免费</span> : null}
+                <span>{item.status}</span>
                 <time dateTime={item.updated_at ?? undefined}>
                   {formatUpdatedAt(item.updated_at)}
                 </time>
               </div>
             </li>
           ))}
         </ul>
       ) : null}
     </section>
   )
@@ -132,21 +130,21 @@ function PublicHome() {
               从清楚的接口文档开始，按公开规范调用稳定、可核验的自营工具。
             </p>
             <form className="public-search-form" action="/catalog" method="get">
               <label className="sr-only" htmlFor="catalog-query">
                 搜索 API 目录
               </label>
               <input
                 id="catalog-query"
                 name="query"
                 className="public-search-input"
-                placeholder="搜索时间戳、UUID、天气……"
+                placeholder="搜索时间、UUID 等公开接口……"
                 type="search"
               />
               <button className="public-primary-button" type="submit">
                 搜索 API 目录
               </button>
             </form>
             <nav className="public-hero-links" aria-label="快速入口">
               <a className="public-text-link" href="/catalog">
                 浏览公开目录 <span aria-hidden="true">↗</span>
               </a>
diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
index ac5f343..39af2f7 100644
--- a/frontend/tests/public-catalog.spec.ts
+++ b/frontend/tests/public-catalog.spec.ts
@@ -1,54 +1,251 @@
-import { expect, test } from "@playwright/test"
+import { expect, type Page, test } from "@playwright/test"
 
 test.use({ storageState: { cookies: [], origins: [] } })
 
-test("Anonymous users can open the public home without login redirect", async ({
-  page,
-}) => {
-  await page.goto("/")
+const timeItem = {
+  slug: "time",
+  name: "时间查询",
+  summary: "按可选 IANA 时区返回当前 UTC、Unix 时间戳和本地时间。",
+  category: "tools",
+  method: "GET",
+  path: "/v1/tools/time",
+  auth_type: "api_key",
+  is_free: true,
+  status: "published",
+  updated_at: "2026-10-02T00:00:00Z",
+}
+
+const uuidItem = {
+  slug: "uuid",
+  name: "UUID v4 生成器",
+  summary: "生成一个随机 UUID v4，不接受任何查询参数。",
+  category: "tools",
+  method: "GET",
+  path: "/v1/tools/uuid",
+  auth_type: "api_key",
+  is_free: true,
+  status: "published",
+  updated_at: "2026-10-02T00:00:00Z",
+}
+
+const timeDetail = {
+  ...timeItem,
+  auth: { type: "api_key", header: "X-API-Key" },
+  parameters: [
+    {
+      name: "timezone",
+      in: "query",
+      required: false,
+      description: "可选的 IANA 时区名称，省略时使用 UTC。",
+      schema: {
+        type: "string",
+        default: "UTC",
+        examples: ["UTC", "Asia/Shanghai"],
+      },
+    },
+  ],
+  response_schema: {
+    type: "object",
+    properties: {
+      utc: { type: "string", format: "date-time" },
+      unix_timestamp: { type: "number" },
+      timezone: { type: "string" },
+      local: { type: "string", format: "date-time" },
+    },
+    required: ["utc", "unix_timestamp", "timezone", "local"],
+  },
+  errors: [
+    {
+      status: 401,
+      code: "API_KEY_REQUIRED",
+      description: "请求必须提供 X-API-Key。",
+    },
+    { status: 404, code: "API_NOT_FOUND", description: "接口不存在或未公开。" },
+  ],
+  examples: [
+    {
+      language: "curl",
+      request:
+        'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
+    },
+  ],
+  source: "Yeyu API",
+  cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
+}
+
+type CatalogPage = {
+  data: (typeof timeItem)[]
+  count: number
+  page: number
+  page_size: number
+}
+
+async function mockCatalogApi(page: Page) {
+  await page.route("**/api/v1/catalog*", async (route) => {
+    const url = new URL(route.request().url())
+
+    if (url.pathname.endsWith("/time")) {
+      await route.fulfill({
+        status: 200,
+        contentType: "application/json",
+        body: JSON.stringify(timeDetail),
+      })
+      return
+    }
+
+    const query = url.searchParams.get("query") ?? ""
+    const category = url.searchParams.get("category")
+    const status = url.searchParams.get("status")
+    const data =
+      query === "missing"
+        ? []
+        : query === "uuid"
+          ? [uuidItem]
+          : [timeItem, uuidItem]
+    const filtered = data.filter(
+      (item) =>
+        (!category || item.category === category) &&
+        (!status || item.status === status),
+    )
+    const response: CatalogPage = {
+      data: filtered,
+      count: filtered.length,
+      page: 1,
+      page_size: 20,
+    }
 
-  await expect(page).toHaveURL(/\/$/)
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify(response),
+    })
+  })
+}
+
+test("Anonymous users can browse the real public catalog", async ({ page }) => {
+  await mockCatalogApi(page)
+  await page.goto("/catalog")
+
+  await expect(page).toHaveURL("/catalog")
+  await expect(page.getByRole("heading", { name: "API 目录" })).toBeVisible()
+  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
+  await expect(page.getByTestId("catalog-card-time")).toContainText(
+    "/v1/tools/time",
+  )
+  await expect(page.getByText("免费", { exact: true }).first()).toBeVisible()
   await expect(
-    page.getByRole("heading", {
-      name: "给学生和个人开发者的免费 API 工具箱",
-    }),
+    page.getByText("published", { exact: true }).first(),
   ).toBeVisible()
-  await expect(page).not.toHaveURL(/\/login/)
+  await expect(page.getByRole("link", { name: /时间查询/ })).toHaveAttribute(
+    "href",
+    "/catalog/time",
+  )
 })
 
-test("Anonymous users can open the public catalog placeholder", async ({
+test("Catalog search is debounced and filters are shareable in the URL", async ({
   page,
 }) => {
+  const catalogRequests: string[] = []
+  await page.route("**/api/v1/catalog*", async (route) => {
+    const url = new URL(route.request().url())
+    if (url.pathname.endsWith("/time")) {
+      await route.fulfill({
+        status: 200,
+        contentType: "application/json",
+        body: JSON.stringify(timeDetail),
+      })
+      return
+    }
+    catalogRequests.push(url.search)
+    const item = url.searchParams.get("query") === "uuid" ? uuidItem : timeItem
+    await route.fulfill({
+      status: 200,
+      contentType: "application/json",
+      body: JSON.stringify({ data: [item], count: 1, page: 1, page_size: 20 }),
+    })
+  })
+
   await page.goto("/catalog")
+  const searchInput = page.getByRole("searchbox", { name: "搜索公开 API" })
+  await searchInput.fill("uuid")
+  await page.waitForTimeout(150)
+  expect(
+    catalogRequests.filter((request) => request.includes("query=uuid")),
+  ).toHaveLength(0)
+  await expect(page).toHaveURL(/\/catalog\?query=uuid$/)
+  await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()
 
-  await expect(page).toHaveURL("/catalog")
+  await page.getByLabel("分类").selectOption("tools")
+  await expect(page).toHaveURL(/query=uuid.*category=tools/)
+  await page.getByLabel("状态").selectOption("published")
+  await expect(page).toHaveURL(/query=uuid.*category=tools.*status=published/)
+})
+
+test("Catalog displays an explicit empty state for an empty result", async ({
+  page,
+}) => {
+  await mockCatalogApi(page)
+  await page.goto("/catalog?query=missing")
+
+  await expect(page.getByTestId("catalog-empty")).toBeVisible()
+  await expect(page.getByText("没有找到匹配的公开接口")).toBeVisible()
+  await expect(page.getByTestId("catalog-grid")).not.toBeVisible()
+})
+
+test("Time detail documents the request contract and safe code examples", async ({
+  page,
+}) => {
+  await mockCatalogApi(page)
+  await page.goto("/catalog/time")
+
+  await expect(page).toHaveURL("/catalog/time")
+  await expect(page.getByRole("heading", { name: "时间查询" })).toBeVisible()
+  await expect(page.getByText("/v1/tools/time", { exact: true })).toBeVisible()
+  await expect(page.getByText("GET", { exact: true }).first()).toBeVisible()
   await expect(
-    page.getByRole("heading", { name: "API 目录建设中" }),
+    page.getByText("API Key", { exact: false }).first(),
   ).toBeVisible()
-  await expect(page.getByText("由公开目录驱动")).toBeVisible()
-  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
+  await expect(page.getByText("timezone", { exact: true })).toBeVisible()
+  await expect(page.getByText("utc", { exact: true })).toBeVisible()
+  await expect(page.getByText("unix_timestamp", { exact: true })).toBeVisible()
+  await expect(
+    page.getByText("API_KEY_REQUIRED", { exact: true }),
+  ).toBeVisible()
+  await expect(page.getByText("Yeyu API", { exact: true })).toBeVisible()
+  await expect(page.getByRole("heading", { name: "curl" })).toBeVisible()
+  await expect(page.getByRole("heading", { name: "JavaScript" })).toBeVisible()
+  await expect(page.getByRole("heading", { name: "Python" })).toBeVisible()
+  await expect(
+    page.locator("code").filter({ hasText: "<YOUR_API_KEY>" }).first(),
+  ).toBeVisible()
+  await expect(
+    page.locator("code").filter({ hasText: "api.yeyubaka.top" }).first(),
+  ).toBeVisible()
+
+  const copyButton = page.getByRole("button", { name: "复制 curl 示例" })
+  await expect(copyButton).toBeVisible()
+  await copyButton.click()
+  await expect(copyButton).toContainText("已复制")
 })
 
-test("Public navigation exposes keyboard-accessible catalog and login links", async ({
+test("Public navigation remains keyboard accessible on mobile", async ({
   page,
 }) => {
   await page.setViewportSize({ width: 390, height: 844 })
+  await mockCatalogApi(page)
   await page.goto("/")
 
   const navigation = page.getByRole("navigation", { name: "公共导航" })
   const menuButton = navigation.getByRole("button", { name: /菜单/ })
 
   await expect(navigation).toBeVisible()
   await expect(menuButton).toHaveAttribute("aria-expanded", "true")
 
   await menuButton.press("Enter")
   await expect(menuButton).toHaveAttribute("aria-expanded", "false")
 
   await menuButton.press("Space")
   await expect(menuButton).toHaveAttribute("aria-expanded", "true")
   await expect(navigation.getByRole("link", { name: "API 目录" })).toBeVisible()
   await expect(navigation.getByRole("link", { name: "登录" })).toBeVisible()
-
-  await navigation.getByRole("link", { name: "登录" }).focus()
-  await expect(navigation.getByRole("link", { name: "登录" })).toBeFocused()
 })
diff --git a/plans/agent-reports/task-7-3-brief.md b/plans/agent-reports/task-7-3-brief.md
new file mode 100644
index 0000000..67f06a2
--- /dev/null
+++ b/plans/agent-reports/task-7-3-brief.md
@@ -0,0 +1,58 @@
+## Task 3: Build Search-First Catalog and Detail Pages
+
+**Files:**
+
+- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogSearch.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogFilters.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogCard.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogGrid.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogStates.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx
+- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CodeExample.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
+- Modify E:\AI_projects\yeyu-api\frontend\src\index.css
+- Modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+
+### Implementation
+
+- [ ] 在测试中覆盖目录页匿名可访问、搜索参数能反映到 URL、分类筛选能反映到 URL、空结果有明确状态、详情页展示 /v1/tools/time、GET、API Key 鉴权、参数、响应字段和错误码。
+- [ ] 目录页通过生成的 CatalogService.getCatalog 和 React Query 获取分页数据，query、category、status 使用 TanStack Router search params 作为唯一可分享状态；输入搜索设置 300 至 500 毫秒防抖并避免逐键请求。
+- [ ] 目录页首屏顺序固定为页面标题与搜索框、分类/状态筛选、真实目录卡片；卡片包含名称、中文简介、请求方法、路径、免费标记、健康/发布状态和更新时间，点击后进入 /catalog/:slug。
+- [ ] 目录页只展示后端返回数据，不在前端硬编码候选接口；API 返回空、错误和加载状态分别使用可读的 Empty、Error、Skeleton 组件。
+- [ ] 详情页通过生成的 CatalogService.getCatalogDetail({ path: { slug } }) 获取数据；展示鉴权说明、参数表、响应结构、错误码、缓存规则、来源标签和 curl、JavaScript、Python 示例。
+- [ ] 代码示例只显示 <YOUR_API_KEY>，统一从当前域名拼接请求 URL，不保存或读取真实 API Key，不提供任意 URL 输入；复制按钮使用可访问名称并在成功后有非颜色反馈。
+- [ ] 首页保持索引台视觉：上方以一句清晰定位和主搜索入口为主，下面展示由真实目录 API 返回的精选工具卡片、一个可直接跳转的 Quick Start 区块和公益/使用边界说明；不展示假统计。
+- [ ] 公共导航在首页、目录页和详情页保持一致；目录页搜索框支持从首页带 query 参数跳转后继续搜索。
+- [ ] 移动端将详情页的参数表、代码块和路径行处理为可横向滚动而不撑破页面；桌面端使用窄内容列、明显分隔线和稳定状态色。
+
+### Verification
+
+- [ ] 执行前端构建与静态检查：
+
+~~~powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
+pnpm build
+~~~
+
+- [ ] 在项目 Docker Compose 测试环境可用时执行：
+
+~~~powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec playwright test tests/public-catalog.spec.ts
+~~~
+
+- [ ] 通过 API 测试确认种子后端实际提供目录数据：
+
+~~~powershell
+conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py -q
+~~~
+
+- [ ] 使用真实浏览器尺寸至少检查 1280 像素桌面视口和 390 像素移动视口；记录页面 URL、公开/受保护结果、控制台错误和截图路径。截图若用于审查，只放在项目外部临时目录。
+- [ ] 独立只读子代理检查 API client 使用、URL 状态同步、错误/空状态、示例密钥脱敏、移动端溢出、可访问性和视觉方案偏离，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-review.md。
+- [ ] 处理审查问题后重跑构建、API 测试和浏览器测试，创建提交 feat: add public catalog and api detail pages 并推送 origin/main。
+
diff --git a/plans/agent-reports/task-7-3-report.md b/plans/agent-reports/task-7-3-report.md
new file mode 100644
index 0000000..aaab69a
--- /dev/null
+++ b/plans/agent-reports/task-7-3-report.md
@@ -0,0 +1,135 @@
+# Task 3：公共目录与 API 详情页实现报告
+
+日期：2026-10-02
+项目：`E:\AI_projects\yeyu-api`
+实现提交：`c13adce`
+
+## 1. 实现范围
+
+本次完成公共目录从占位页到真实搜索优先目录，以及公开 API 详情页：
+
+- 目录页通过生成的 `CatalogService.searchCatalog` 和 React Query 请求后端公开目录；只渲染 API 返回的 `CatalogItem`。
+- `query` 使用 400ms 防抖同步到 TanStack Router search params；`category`、`status` 立即同步 URL，并作为 React Query key 的一部分。
+- 卡片展示名称、简介、方法、路径、免费标记、后端状态和更新时间，并链接到 `/catalog/:slug`。
+- 分别实现加载、错误、空结果状态；空结果不创建前端候选卡片。
+- 新增 `/catalog/$slug` 详情路由，使用 `CatalogService.getCatalogDetail({ path: { slug } })`。
+- 详情展示 API Key 鉴权、参数表、响应字段和 schema、错误码、缓存规则、来源，以及 curl、JavaScript、Python 示例。
+- 所有示例只使用 `<YOUR_API_KEY>`；JavaScript 使用当前页面 origin，curl/Python 使用正式 API 域名；未读取 localStorage、Cookie 或真实 API Key。
+- 首页预览继续使用真实目录 API，并补充详情链接、真实状态/更新时间和搜索跳转入口。
+- 公共导航改为 TanStack Router 链接；详情路径、表格和代码块在窄视口使用滚动/换行边界。
+- 未修改 `frontend/src/routeTree.gen.ts`，未修改 dashboard 保护或认证逻辑，未实现在线调试和 API Key 管理 UI。
+
+## 2. 修改文件
+
+- `frontend/src/components/ApiCatalog/catalog-types.ts`
+- `frontend/src/components/ApiCatalog/CatalogSearch.tsx`
+- `frontend/src/components/ApiCatalog/CatalogFilters.tsx`
+- `frontend/src/components/ApiCatalog/CatalogCard.tsx`
+- `frontend/src/components/ApiCatalog/CatalogGrid.tsx`
+- `frontend/src/components/ApiCatalog/CatalogStates.tsx`
+- `frontend/src/components/ApiCatalog/ApiDetailView.tsx`
+- `frontend/src/components/ApiCatalog/CodeExample.tsx`
+- `frontend/src/routes/catalog/index.tsx`
+- `frontend/src/routes/catalog/$slug.tsx`
+- `frontend/src/routes/index.tsx`
+- `frontend/src/components/PublicSite/PublicHeader.tsx`
+- `frontend/src/components/PublicSite/PublicFooter.tsx`
+- `frontend/src/index.css`
+- `frontend/tests/public-catalog.spec.ts`
+
+任务简报 `plans/agent-reports/task-7-3-brief.md` 是用户提供的未跟踪文件，本次未修改、未提交。
+
+## 3. TDD RED/GREEN 证据
+
+### RED
+
+先更新了 `frontend/tests/public-catalog.spec.ts`，覆盖：匿名目录、搜索参数 URL 同步、防抖、分类/状态筛选 URL、空结果、`/catalog/time`、`/v1/tools/time`、GET、API Key、`timezone`、响应字段、错误码、三种代码示例和复制反馈。
+
+真实命令与结果：
+
+```text
+pnpm exec playwright test tests/public-catalog.spec.ts
+exit 1
+Error: Environment variable FIRST_SUPERUSER is undefined
+```
+
+仅在进程内注入非真实测试值后重试：
+
+```text
+$env:FIRST_SUPERUSER='<NON_SECRET_TEST_EMAIL>'; $env:FIRST_SUPERUSER_PASSWORD='<NON_SECRET_TEST_VALUE>'; pnpm exec playwright test tests/public-catalog.spec.ts
+exit 1
+browserType.launch: Executable doesn't exist ... chrome-headless-shell.exe
+1 failed [setup] auth.setup.ts; 5 did not run
+```
+
+随后执行了依赖安装：
+
+```text
+pnpm exec playwright install chromium
+exit 0
+Chrome for Testing and Chrome Headless Shell downloaded to the Playwright user cache
+```
+
+安装后再次以同样的非真实进程值运行：
+
+```text
+exit 1
+Test timeout of 30000ms exceeded
+at tests/auth.setup.ts:8:41, waiting for getByTestId('email-input')
+1 failed [setup] auth.setup.ts; 5 did not run
+```
+
+因此 RED 阶段有测试收集/环境阻塞证据，但目标目录断言没有进入浏览器执行。
+
+### GREEN
+
+已完成对应静态实现，并执行 Biome 作为快速静态门禁；没有运行 Playwright/build，故不能宣称浏览器 GREEN、类型检查 GREEN 或产品验收 GREEN。
+
+## 4. 静态验证
+
+首次对 `src tests` 执行 Biome 的真实结果：
+
+```text
+exit 1
+Checked 73 files in 46ms. No fixes applied.
+Found 14 errors.
+Found 2 warnings.
+```
+
+错误集中在新增 JSX 格式、无效 div `aria-label`、搜索容器 role，以及 CSS 特异性顺序。修正后只对本次改动的 15 个文件执行：
+
+```text
+pnpm exec biome check --write --no-errors-on-unmatched --files-ignore-unknown=true <15 absolute paths>
+exit 0
+Checked 15 files in 18ms. Fixed 9 files.
+
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true <15 absolute paths>
+exit 0
+Checked 15 files in 14ms. No fixes applied.
+```
+
+另执行 `git diff --check`，未发现空白错误；Git 仅提示 Windows 工作树的 LF/CRLF 转换警告。
+
+## 5. 未验证阻塞与边界
+
+- Playwright 被既有 `auth.setup.ts` 的认证 setup 阻塞；缺少浏览器已安装，但 setup 后续仍在登录页 `email-input` 等待超时。未把 setup 失败算作目录测试通过。
+- 按用户本次要求未运行 `pnpm build`，未运行后端 pytest，也未做真实浏览器桌面/移动截图验收。
+- 未运行 Vite 官方路由生成链，因此 `routeTree.gen.ts` 仍保持未手改状态；新增路由是否被生成链和 TypeScript 完整接纳需要后续 build/开发服务器验证。
+- 未执行线上验收、DNS/Nginx/SMTP/GitHub OAuth 或生产部署；没有触碰旧项目、线上服务和凭据。
+
+## 6. Self-review
+
+- [x] 目录卡片由 `CatalogService` 返回数据驱动，无硬编码接口卡片。
+- [x] 目录搜索和筛选状态可分享，搜索防抖为 400ms。
+- [x] 详情页使用生成 client 的 path slug 形态，展示真实 schema/参数/错误/缓存/来源字段。
+- [x] 示例只包含 `<YOUR_API_KEY>`，没有新增浏览器凭据读取或在线调用控件。
+- [x] 复制按钮有可访问名称，成功状态有文字和图标反馈。
+- [x] 移动端表格、路径和代码块设置横向滚动边界。
+- [x] Biome 最终对本次 15 个文件通过。
+- [ ] Playwright、build、pytest 和真实浏览器验收：受用户要求/现有 setup 阻塞，未验证。
+
+## 7. 提交
+
+实现代码提交主题：`feat: add public catalog and api detail pages`
+
+提交 SHA：`c13adce`（实现提交；报告随后单独提交）。
