# Review package: 4c43285..e9efb91

## Commits
e9efb91 docs: record task 7-2 repair report
673d806 fix: close public shell review findings

## Files changed
 frontend/package.json                  |  2 +-
 frontend/src/routes/catalog/index.tsx  | 45 +++++++++++++++++++++++
 frontend/tests/login.spec.ts           |  4 +--
 frontend/tests/public-catalog.spec.ts  | 29 +++++++++++----
 plans/agent-reports/task-7-2-report.md | 66 ++++++++++++++++++++++++++++++++++
 5 files changed, 136 insertions(+), 10 deletions(-)

## Diff
diff --git a/frontend/package.json b/frontend/package.json
index 3a63aca..568862d 100644
--- a/frontend/package.json
+++ b/frontend/package.json
@@ -1,19 +1,19 @@
 {
   "name": "frontend",
   "private": true,
   "packageManager": "pnpm@10.28.2",
   "version": "0.0.0",
   "type": "module",
   "scripts": {
     "dev": "vite",
-    "build": "tsc -p tsconfig.build.json && vite build",
+    "build": "vite build && tsc -p tsconfig.build.json",
     "lint": "biome check --write --unsafe --no-errors-on-unmatched --files-ignore-unknown=true ./",
     "preview": "vite preview",
     "generate-client": "openapi-ts",
     "test": "pnpm exec playwright test",
     "test:ui": "pnpm exec playwright test --ui"
   },
   "dependencies": {
     "@hookform/resolvers": "^5.7.1",
     "@radix-ui/react-avatar": "^1.2.6",
     "@radix-ui/react-checkbox": "^1.3.11",
diff --git a/frontend/src/routes/catalog/index.tsx b/frontend/src/routes/catalog/index.tsx
new file mode 100644
index 0000000..a0084bb
--- /dev/null
+++ b/frontend/src/routes/catalog/index.tsx
@@ -0,0 +1,45 @@
+import { createFileRoute, Link } from "@tanstack/react-router"
+
+import PublicLayout from "@/components/PublicSite/PublicLayout"
+
+export const Route = createFileRoute("/catalog/")({
+  component: CatalogPlaceholder,
+  head: () => ({
+    meta: [
+      {
+        title: "API 目录 - Yeyu API",
+      },
+    ],
+  }),
+})
+
+function CatalogPlaceholder() {
+  return (
+    <PublicLayout>
+      <div className="public-container py-16 sm:py-24">
+        <section
+          className="public-state mx-auto max-w-2xl text-center"
+          aria-labelledby="catalog-placeholder-heading"
+          data-testid="catalog-placeholder"
+        >
+          <p className="public-eyebrow">公开目录</p>
+          <h1
+            id="catalog-placeholder-heading"
+            className="public-section-title mt-3"
+          >
+            API 目录建设中
+          </h1>
+          <p className="public-section-copy mx-auto mt-4 max-w-xl">
+            由公开目录驱动的真实接口条目将在下一阶段开放，当前先保留清晰的公共入口。
+          </p>
+          <p className="mt-3 text-sm text-[var(--yeyu-muted)]">
+            目录建设中，请稍后再来查看。
+          </p>
+          <Link to="/" className="public-primary-button mt-8 inline-flex">
+            返回首页
+          </Link>
+        </section>
+      </div>
+    </PublicLayout>
+  )
+}
diff --git a/frontend/tests/login.spec.ts b/frontend/tests/login.spec.ts
index b399e9d..05ef6ea 100644
--- a/frontend/tests/login.spec.ts
+++ b/frontend/tests/login.spec.ts
@@ -85,24 +85,24 @@ test("Successful log out", async ({ page }) => {
   await page.getByRole("menuitem", { name: "Log out" }).click()
   await page.waitForURL("/login")
 })
 
 test("Logged-out user cannot access protected routes", async ({ page }) => {
   await page.goto("/login")
 
   await fillForm(page, firstSuperuser, firstSuperuserPassword)
   await page.getByRole("button", { name: "Log In" }).click()
 
-  await page.waitForURL("/")
+  await page.waitForURL("/dashboard")
 
   await expect(
-    page.getByText("Welcome back, nice to see you again!"),
+    page.getByRole("heading", { name: "Yeyu API 控制台" }),
   ).toBeVisible()
 
   await page.getByTestId("user-menu").click()
   await page.getByRole("menuitem", { name: "Log out" }).click()
   await page.waitForURL("/login")
 
   await page.goto("/settings")
   await page.waitForURL("/login")
 })
 
diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
index 1c5789d..ac5f343 100644
--- a/frontend/tests/public-catalog.spec.ts
+++ b/frontend/tests/public-catalog.spec.ts
@@ -9,31 +9,46 @@ test("Anonymous users can open the public home without login redirect", async ({
 
   await expect(page).toHaveURL(/\/$/)
   await expect(
     page.getByRole("heading", {
       name: "给学生和个人开发者的免费 API 工具箱",
     }),
   ).toBeVisible()
   await expect(page).not.toHaveURL(/\/login/)
 })
 
-test("Anonymous users can open the catalog entry without login redirect", async ({
+test("Anonymous users can open the public catalog placeholder", async ({
   page,
 }) => {
   await page.goto("/catalog")
 
-  await expect(page).not.toHaveURL(/\/login/)
+  await expect(page).toHaveURL("/catalog")
+  await expect(
+    page.getByRole("heading", { name: "API 目录建设中" }),
+  ).toBeVisible()
+  await expect(page.getByText("由公开目录驱动")).toBeVisible()
+  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
 })
 
 test("Public navigation exposes keyboard-accessible catalog and login links", async ({
   page,
 }) => {
   await page.setViewportSize({ width: 390, height: 844 })
   await page.goto("/")
 
-  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
-  await expect(page.getByRole("link", { name: "API 目录" })).toBeVisible()
-  await expect(page.getByRole("link", { name: "登录" })).toBeVisible()
+  const navigation = page.getByRole("navigation", { name: "公共导航" })
+  const menuButton = navigation.getByRole("button", { name: /菜单/ })
+
+  await expect(navigation).toBeVisible()
+  await expect(menuButton).toHaveAttribute("aria-expanded", "true")
+
+  await menuButton.press("Enter")
+  await expect(menuButton).toHaveAttribute("aria-expanded", "false")
+
+  await menuButton.press("Space")
+  await expect(menuButton).toHaveAttribute("aria-expanded", "true")
+  await expect(navigation.getByRole("link", { name: "API 目录" })).toBeVisible()
+  await expect(navigation.getByRole("link", { name: "登录" })).toBeVisible()
 
-  await page.getByRole("link", { name: "登录" }).focus()
-  await expect(page.getByRole("link", { name: "登录" })).toBeFocused()
+  await navigation.getByRole("link", { name: "登录" }).focus()
+  await expect(navigation.getByRole("link", { name: "登录" })).toBeFocused()
 })
diff --git a/plans/agent-reports/task-7-2-report.md b/plans/agent-reports/task-7-2-report.md
index c795cbd..35c5158 100644
--- a/plans/agent-reports/task-7-2-report.md
+++ b/plans/agent-reports/task-7-2-report.md
@@ -97,10 +97,76 @@ Playwright GREEN：未运行。由于 Chromium 可执行文件缺失，且用户
 - 实现提交主题：`feat: split public and protected web shells`
 - 提交 SHA：`0acbfc3`。
 - 报告状态：本文件随实现提交写入；本次回填 SHA 后产生一个仅文档的收尾提交。
 
 ## 未验证项
 
 - 真实 Chromium 浏览器中的匿名 `/`、`/catalog`、登录成功 `/dashboard`、登出和 `/items` 认证跳转。
 - TanStack Router 生成 `routeTree.gen.ts` 后的最终 TypeScript/build 结果。
 - 真实后端目录 API 返回项在浏览器中的展示。
 - 生产环境、Docker Compose、数据库、SMTP、GitHub OAuth、DNS、TLS、Nginx 和线上回归。
+
+## Task 7-2 修复报告：关闭公共壳层审查问题
+
+### 修复文件
+
+- `frontend/package.json`：将 `build` 调整为 `vite build && tsc -p tsconfig.build.json`，先让 Vite/TanStack Router 官方插件生成路由树，再执行类型检查。
+- `frontend/tests/login.spec.ts`：将“Logged-out user cannot access protected routes”中的登录后断言改为 `/dashboard` 和 `Yeyu API 控制台`，保留退出后 `/settings` 跳转 `/login` 的断言。
+- `frontend/src/routes/catalog/index.tsx`：新增任务 2 范围内的最小公共目录占位路由，复用 `PublicLayout`，提供语义 `h1`、`API 目录建设中`、`由公开目录驱动` 文案和返回首页入口；没有接口卡片、统计或 API 请求。
+- `frontend/tests/public-catalog.spec.ts`：要求 `/catalog` 最终 URL、占位标题和公共导航可见；移动菜单使用键盘 `Enter`、`Space` 实际操作，并断言 `aria-expanded` 为 `true → false → true` 以及展开后的目录/登录链接可见。
+- 未修改 `frontend/src/routeTree.gen.ts`；未触碰旧项目、线上服务、服务器、DNS、Nginx 或真实凭据。
+
+### 审查问题对应改动
+
+1. Critical 构建阻塞：根因是原 `build` 在 Vite 路由生成前运行 `tsc`。已改为 Vite 官方生成链先执行，再运行 `tsc`；本机生成链仍受 SWC 原生绑定环境阻塞，未手写生成树。
+2. Important 登录测试：已等待 `/dashboard`，断言 `Yeyu API 控制台`，并保留登出后访问 `/settings` 必须回到 `/login`。
+3. Important 公共目录：已新增 `/catalog` 最小占位页，并将测试强化为最终 URL、占位标题和公共导航断言；任务 3 可继续扩展该文件。
+4. Important 移动菜单：已从仅 `focus()` 改为对 menu button 使用 `press("Enter")`、`press("Space")`，验证收起/展开状态和展开后的链接。
+
+### 验证命令与真实结果
+
+```text
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true E:\AI_projects\yeyu-api\frontend\package.json E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
+退出码：0
+输出：Checked 4 files in 6ms. No fixes applied.
+```
+
+```text
+git diff --check
+退出码：0；无空白错误（Git 仅提示 LF 将在后续写入时转换为 CRLF）。
+```
+
+```text
+pnpm build
+退出码：1
+输出关键原文：
+> frontend@0.0.0 build E:\AI_projects\YEYU-API\frontend
+> vite build && tsc -p tsconfig.build.json
+failed to load config from E:\AI_projects\YEYU-API\frontend\vite.config.ts
+Error: Failed to load native binding
+Error: Cannot find module './swc.win32-x64-msvc.node'
+Error: SWC native addon: validate cache root C:\Users\21239\AppData\Local\swc: ... DACL grants replacement rights ...
+code: 'ERR_SWC_NATIVE_CACHE'
+```
+
+```text
+pnpm rebuild @swc/core
+退出码：0，但 postinstall 真实输出仍为：
+@swc/core was not able to resolve native bindings installation. It'll try to use @swc/wasm as fallback instead.
+Error: ENOENT: no such file or directory, rename ...\@swc\core\npm-install\node_modules\@swc\wasm -> ...\node_modules\@swc\wasm
+Failed to install fallback @swc/wasm@1.16.12. @swc/core will not properly.
+```
+
+```text
+pnpm exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json
+退出码：1
+输出：旧 routeTree.gen.ts 类型集合中缺少 /dashboard、/catalog/ 和新的 /，对应 PublicHeader.tsx、useAuth.ts、_layout/dashboard.tsx、catalog/index.tsx、routes/index.tsx、login.tsx 报 TS2322/TS2345。
+```
+
+Playwright 未在本次修复中运行，遵循本次指令不运行长时间浏览器或全套测试；此前报告中的 Chromium 可执行文件缺失阻塞仍适用。
+
+### 阻塞结论与提交
+
+- 修复后的构建入口顺序已落地，但本机仍有阻塞：Vite/TanStack 官方生成链在加载配置时被 `@swc/core` 原生绑定缺失、`ERR_SWC_NATIVE_CACHE` 和 fallback `ENOENT` 阻断，因此本地未能生成新 `routeTree.gen.ts`，最终 `tsc` 不能通过。
+- 该阻塞已用真实命令和原始错误记录；没有手工编辑 `routeTree.gen.ts`，也没有把未运行的 Playwright 断言标记为通过。
+- 提交主题：`fix: close public shell review findings`
+- 提交 SHA：`673d806f955c54deb2284198babc33116b78d959`。
