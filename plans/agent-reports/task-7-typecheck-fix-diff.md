# Review package: 303be18..bf62666

## Commits
bf62666 fix: close catalog typecheck findings

## Files changed
 .../src/components/ApiCatalog/ApiDetailView.tsx    |  8 ++---
 .../src/components/PublicSite/PublicFooter.tsx     |  6 +++-
 .../src/components/PublicSite/PublicHeader.tsx     |  7 ++++-
 frontend/src/routes/index.tsx                      |  2 +-
 plans/agent-reports/task-7-final-fix-report.md     | 34 ++++++++++++++++++++++
 5 files changed, 50 insertions(+), 7 deletions(-)

## Diff
diff --git a/frontend/src/components/ApiCatalog/ApiDetailView.tsx b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
index a650887..398ebdb 100644
--- a/frontend/src/components/ApiCatalog/ApiDetailView.tsx
+++ b/frontend/src/components/ApiCatalog/ApiDetailView.tsx
@@ -41,21 +41,21 @@ function parameterExamples(detail: ApiDetail): QueryExample[] {
     const value = candidates
       .map((candidate) => normalizeSafeQueryValue(candidate))
       .find((candidate): candidate is string => candidate !== undefined)
     if (!value) return []
 
     return [{ name, value }]
   })
 }
 
 function quoteCurlArgument(value: string): string {
-  return `'${value.replaceAll("'", "'\\''")}'`
+  return `'${value.replace(/'/g, "'\\''")}'`
 }
 
 function buildCodeExamples(detail: ApiDetail) {
   const candidateMethod = detail.method.toUpperCase()
   const method = /^[A-Z]{1,16}$/.test(candidateMethod) ? candidateMethod : "GET"
   const queryParameters = parameterExamples(detail)
   const path = normalizeInternalApiPath(detail.path)
   const absoluteUrl = buildPublicApiUrl(path)
   if (!path || !absoluteUrl) {
     const unavailable = "无法生成示例：目录路径不可用。"
@@ -117,40 +117,40 @@ function buildCodeExamples(detail: ApiDetail) {
 
   return {
     curl: curlLines.join(" \\\n"),
     javascript: javascriptLines.join("\n"),
     python: pythonLines.join("\n"),
   }
 }
 
 function readableCacheKey(key: string) {
   return key
-    .replaceAll("_", " ")
-    .replace(/\b\w/g, (character) => character.toUpperCase())
+    .replace(/_/g, " ")
+    .replace(/\b\w/g, (character: string) => character.toUpperCase())
 }
 
 interface ApiDetailViewProps {
   detail: ApiDetail
 }
 
 export function ApiDetailView({ detail }: ApiDetailViewProps) {
   const authHeader = PUBLIC_API_AUTH_HEADER
   const examples = buildCodeExamples(detail)
   const responseFields = responseProperties(detail)
   const safePath = normalizeInternalApiPath(detail.path)
   const safeCacheRules = asRecord(sanitizeMetadata(detail.cache_rules)) ?? {}
   const cacheEntries = Object.entries(safeCacheRules)
 
   return (
     <div className="api-detail-page">
       <div className="api-detail-breadcrumbs">
-        <Link to="/catalog" className="public-text-link">
+        <Link to="/catalog" search={{ page: 1 }} className="public-text-link">
           ← 返回公开目录
         </Link>
         <span aria-hidden="true">/</span>
         <span>{detail.category}</span>
       </div>
 
       <header className="api-detail-header">
         <div className="api-detail-path-row">
           <span className="catalog-method-badge">{detail.method}</span>
           <code>{safePath ?? "路径不可用"}</code>
diff --git a/frontend/src/components/PublicSite/PublicFooter.tsx b/frontend/src/components/PublicSite/PublicFooter.tsx
index 192e8b8..4da0a9d 100644
--- a/frontend/src/components/PublicSite/PublicFooter.tsx
+++ b/frontend/src/components/PublicSite/PublicFooter.tsx
@@ -8,21 +8,25 @@ export function PublicFooter() {
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
-          <Link className="public-footer-link" to="/catalog">
+          <Link
+            className="public-footer-link"
+            to="/catalog"
+            search={{ page: 1 }}
+          >
             API 目录
           </Link>
           <Link className="public-footer-link" to="/" hash="usage">
             使用规范
           </Link>
           <Link className="public-footer-link" to="/login">
             登录
           </Link>
         </nav>
       </div>
diff --git a/frontend/src/components/PublicSite/PublicHeader.tsx b/frontend/src/components/PublicSite/PublicHeader.tsx
index 4a2d6d2..372e595 100644
--- a/frontend/src/components/PublicSite/PublicHeader.tsx
+++ b/frontend/src/components/PublicSite/PublicHeader.tsx
@@ -11,21 +11,26 @@ interface NavigationLinksProps {
 
 function NavigationLinks({ onNavigate }: NavigationLinksProps) {
   const linkClassName =
     "public-nav-link rounded-md px-3 py-2 text-sm font-medium"
 
   return (
     <>
       <Link to="/" className={linkClassName} onClick={onNavigate}>
         首页
       </Link>
-      <Link to="/catalog" className={linkClassName} onClick={onNavigate}>
+      <Link
+        to="/catalog"
+        search={{ page: 1 }}
+        className={linkClassName}
+        onClick={onNavigate}
+      >
         API 目录
       </Link>
       <Link to="/" hash="usage" className={linkClassName} onClick={onNavigate}>
         使用规范
       </Link>
       {isLoggedIn() ? (
         <Link
           to="/dashboard"
           className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
           onClick={onNavigate}
diff --git a/frontend/src/routes/index.tsx b/frontend/src/routes/index.tsx
index 2067555..639fce8 100644
--- a/frontend/src/routes/index.tsx
+++ b/frontend/src/routes/index.tsx
@@ -41,21 +41,21 @@ function CatalogPreview() {
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
-        <Link className="public-text-link" to="/catalog">
+        <Link className="public-text-link" to="/catalog" search={{ page: 1 }}>
           搜索完整目录 <span aria-hidden="true">→</span>
         </Link>
       </div>
 
       {catalogQuery.isPending ? (
         <p className="public-state" role="status">
           正在读取真实目录……
         </p>
       ) : null}
 
diff --git a/plans/agent-reports/task-7-final-fix-report.md b/plans/agent-reports/task-7-final-fix-report.md
index 05b9cee..5dd79a8 100644
--- a/plans/agent-reports/task-7-final-fix-report.md
+++ b/plans/agent-reports/task-7-final-fix-report.md
@@ -197,10 +197,44 @@ git diff --check
 - TypeScript build 仍有上面列出的既有组件类型错误；解决它们需要修改本次明确禁止修改的组件/配置文件。
 - Playwright 需要独立、正确的 yeyu-api 前端进程、后端和真实测试账号；当前运行被旧 KnowTrace 进程污染，未形成有效浏览器验收证据。
 - PostgreSQL、SMTP、OAuth、DNS、Nginx 和线上服务未验证，也未被本任务修改。
 - `task-7-1-review.md` 现在明确为中止且未批准；后续若需要独立批准，必须另行完成可追溯复审，不能沿用本文件作为 Approved 证据。
 
 ## 提交
 
 提交主题：`fix: close final catalog review findings`
 
 提交 SHA 由最终 `git commit` 结果返回。
+
+## 本轮 TypeScript Findings 收口追加记录（2026-10-02）
+
+本轮严格限制在当前 tsc 暴露的 7 个错误：
+
+- `ApiDetailView.tsx` 将两个 `replaceAll` 改为 ES2020 可用的全局正则 `replace`；回调参数显式标注为 `string`，保持原有输出语义。
+- `ApiDetailView.tsx`、`PublicHeader.tsx`、`PublicFooter.tsx` 和 `routes/index.tsx` 中返回 `/catalog` 的 TanStack Link 均补充 `search={{ page: 1 }}`。
+- 未修改 `frontend/src/routeTree.gen.ts`，未修改后端、Playwright、旧项目、服务器或凭据。
+
+### 本轮修改文件
+
+- `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`
+- `E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicFooter.tsx`
+- `E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx`
+- `E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx`
+- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-final-fix-report.md`
+
+### 本轮真实验证结果
+
+1. `pnpm exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json`
+   - 退出码：`0`。
+   - 输出：无；此前复现的 7 个错误不再出现。
+2. `pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests`（工作目录：`E:\AI_projects\yeyu-api\frontend`）
+   - 退出码：`0`。
+   - 输出：`Checked 74 files in 41ms. No fixes applied.`
+3. `git diff --check`（工作目录：`E:\AI_projects\yeyu-api`）
+   - 退出码：`0`。
+   - 未报告 whitespace 错误；Git 仅输出本次源码文件及已有计划文件的 LF/CRLF 转换提示。
+
+### 本轮未验证风险
+
+- 本轮未重新执行 Vite build、Playwright、后端集成测试或真实线上验收；这些边界不属于本次 7 个 tsc 错误的最小修复。
+- 工作树中原有的其他计划/报告改动未纳入本次提交，需继续由其原任务处理。
+- 本轮没有重新生成或手工编辑 `routeTree.gen.ts`。
