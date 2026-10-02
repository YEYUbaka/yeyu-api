# Review package: e125ac2..4c43285

## Commits
4c43285 docs: record task 7-2 implementation report
0acbfc3 feat: split public and protected web shells

## Files changed
 frontend/src/components/Common/Footer.tsx          |  44 +-
 frontend/src/components/Common/Logo.tsx            |  55 +--
 .../src/components/PublicSite/PublicFooter.tsx     |  33 ++
 .../src/components/PublicSite/PublicHeader.tsx     |  86 ++++
 .../src/components/PublicSite/PublicLayout.tsx     |  20 +
 frontend/src/components/Sidebar/AppSidebar.tsx     |   2 +-
 frontend/src/hooks/useAuth.ts                      |   2 +-
 frontend/src/index.css                             | 500 ++++++++++++++++++++-
 frontend/src/routes/_layout.tsx                    |   7 +-
 frontend/src/routes/_layout/dashboard.tsx          |  34 ++
 frontend/src/routes/_layout/index.tsx              |  31 --
 frontend/src/routes/index.tsx                      | 212 +++++++++
 frontend/src/routes/login.tsx                      |   6 +-
 frontend/tests/login.spec.ts                       |  29 +-
 frontend/tests/public-catalog.spec.ts              |  39 ++
 plans/agent-reports/task-7-2-report.md             | 106 +++++
 16 files changed, 1090 insertions(+), 116 deletions(-)

## Diff
diff --git a/frontend/src/components/Common/Footer.tsx b/frontend/src/components/Common/Footer.tsx
index 279e1e7..5687a91 100644
--- a/frontend/src/components/Common/Footer.tsx
+++ b/frontend/src/components/Common/Footer.tsx
@@ -1,44 +1,30 @@
-import { FaGithub, FaLinkedinIn } from "react-icons/fa"
-import { FaXTwitter } from "react-icons/fa6"
-
-const socialLinks = [
-  {
-    icon: FaGithub,
-    href: "https://github.com/fastapi/fastapi",
-    label: "GitHub",
-  },
-  { icon: FaXTwitter, href: "https://x.com/fastapi", label: "X" },
-  {
-    icon: FaLinkedinIn,
-    href: "https://linkedin.com/company/fastapi",
-    label: "LinkedIn",
-  },
-]
+import { Link } from "@tanstack/react-router"
 
 export function Footer() {
   const currentYear = new Date().getFullYear()
 
   return (
     <footer className="border-t py-4 px-6">
       <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
         <p className="text-muted-foreground text-sm">
-          Full Stack FastAPI Template - {currentYear}
+          Yeyu API 公益平台 - {currentYear}
         </p>
         <div className="flex items-center gap-4">
-          {socialLinks.map(({ icon: Icon, href, label }) => (
-            <a
-              key={label}
-              href={href}
-              target="_blank"
-              rel="noopener noreferrer"
-              aria-label={label}
-              className="text-muted-foreground hover:text-foreground transition-colors"
-            >
-              <Icon className="h-5 w-5" />
-            </a>
-          ))}
+          <Link
+            to="/"
+            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
+          >
+            返回公共首页
+          </Link>
+          <Link
+            to="/"
+            hash="usage"
+            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
+          >
+            使用规范
+          </Link>
         </div>
       </div>
     </footer>
   )
 }
diff --git a/frontend/src/components/Common/Logo.tsx b/frontend/src/components/Common/Logo.tsx
index 05c299f..d574f16 100644
--- a/frontend/src/components/Common/Logo.tsx
+++ b/frontend/src/components/Common/Logo.tsx
@@ -1,60 +1,61 @@
 import { Link } from "@tanstack/react-router"
 
-import { useTheme } from "@/components/theme-provider"
 import { cn } from "@/lib/utils"
-import icon from "/assets/images/fastapi-icon.svg"
-import iconLight from "/assets/images/fastapi-icon-light.svg"
-import logo from "/assets/images/fastapi-logo.svg"
-import logoLight from "/assets/images/fastapi-logo-light.svg"
 
 interface LogoProps {
   variant?: "full" | "icon" | "responsive"
   className?: string
   asLink?: boolean
 }
 
 export function Logo({
   variant = "full",
   className,
   asLink = true,
 }: LogoProps) {
-  const { resolvedTheme } = useTheme()
-  const isDark = resolvedTheme === "dark"
-
-  const fullLogo = isDark ? logoLight : logo
-  const iconLogo = isDark ? iconLight : icon
-
   const content =
     variant === "responsive" ? (
       <>
-        <img
-          src={fullLogo}
-          alt="FastAPI"
+        <span
+          aria-hidden="true"
           className={cn(
-            "h-6 w-auto group-data-[collapsible=icon]:hidden",
+            "inline-flex h-7 items-center gap-1.5 text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden",
             className,
           )}
-        />
-        <img
-          src={iconLogo}
-          alt="FastAPI"
+        >
+          <span className="logo-mark">Y</span>
+          <span>Yeyu API</span>
+        </span>
+        <span
+          aria-hidden="true"
           className={cn(
-            "size-5 hidden group-data-[collapsible=icon]:block",
+            "logo-mark hidden size-7 items-center justify-center text-sm group-data-[collapsible=icon]:inline-flex",
             className,
           )}
-        />
+        >
+          Y
+        </span>
       </>
     ) : (
-      <img
-        src={variant === "full" ? fullLogo : iconLogo}
-        alt="FastAPI"
-        className={cn(variant === "full" ? "h-6 w-auto" : "size-5", className)}
-      />
+      <span
+        aria-hidden="true"
+        className={cn(
+          "inline-flex items-center gap-2 text-lg font-semibold tracking-tight",
+          className,
+        )}
+      >
+        <span className="logo-mark">Y</span>
+        {variant === "full" ? <span>Yeyu API</span> : null}
+      </span>
     )
 
   if (!asLink) {
     return content
   }
 
-  return <Link to="/">{content}</Link>
+  return (
+    <Link to="/" aria-label="Yeyu API 首页" className="inline-flex">
+      {content}
+    </Link>
+  )
 }
diff --git a/frontend/src/components/PublicSite/PublicFooter.tsx b/frontend/src/components/PublicSite/PublicFooter.tsx
new file mode 100644
index 0000000..15a05ca
--- /dev/null
+++ b/frontend/src/components/PublicSite/PublicFooter.tsx
@@ -0,0 +1,33 @@
+import { Link } from "@tanstack/react-router"
+
+export function PublicFooter() {
+  const currentYear = new Date().getFullYear()
+
+  return (
+    <footer className="public-footer">
+      <div className="public-container flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
+        <div>
+          <p className="font-semibold text-[var(--yeyu-ink)]">
+            Yeyu API 公益平台
+          </p>
+          <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
+            面向学生与个人开发者的公开工具目录 · {currentYear}
+          </p>
+        </div>
+        <nav aria-label="页脚导航" className="flex flex-wrap gap-4 text-sm">
+          <a className="public-footer-link" href="/catalog">
+            API 目录
+          </a>
+          <Link className="public-footer-link" to="/" hash="usage">
+            使用规范
+          </Link>
+          <Link className="public-footer-link" to="/login">
+            登录
+          </Link>
+        </nav>
+      </div>
+    </footer>
+  )
+}
+
+export default PublicFooter
diff --git a/frontend/src/components/PublicSite/PublicHeader.tsx b/frontend/src/components/PublicSite/PublicHeader.tsx
new file mode 100644
index 0000000..e6daf45
--- /dev/null
+++ b/frontend/src/components/PublicSite/PublicHeader.tsx
@@ -0,0 +1,86 @@
+import { Link } from "@tanstack/react-router"
+import { Menu, X } from "lucide-react"
+import { useState } from "react"
+
+import { Logo } from "@/components/Common/Logo"
+import { isLoggedIn } from "@/hooks/useAuth"
+
+interface NavigationLinksProps {
+  onNavigate?: () => void
+}
+
+function NavigationLinks({ onNavigate }: NavigationLinksProps) {
+  const linkClassName =
+    "public-nav-link rounded-md px-3 py-2 text-sm font-medium"
+
+  return (
+    <>
+      <Link to="/" className={linkClassName} onClick={onNavigate}>
+        首页
+      </Link>
+      <a href="/catalog" className={linkClassName} onClick={onNavigate}>
+        API 目录
+      </a>
+      <Link to="/" hash="usage" className={linkClassName} onClick={onNavigate}>
+        使用规范
+      </Link>
+      {isLoggedIn() ? (
+        <Link
+          to="/dashboard"
+          className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
+          onClick={onNavigate}
+        >
+          控制台
+        </Link>
+      ) : (
+        <Link
+          to="/login"
+          className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
+          onClick={onNavigate}
+        >
+          登录
+        </Link>
+      )}
+    </>
+  )
+}
+
+export function PublicHeader() {
+  const [menuOpen, setMenuOpen] = useState(true)
+  const toggleMenu = () => setMenuOpen((open) => !open)
+  const closeMenu = () => setMenuOpen(false)
+
+  return (
+    <header className="public-header">
+      <div className="public-container public-header-inner">
+        <Logo variant="full" className="h-8" />
+
+        <nav aria-label="公共导航" className="public-nav">
+          <div className="hidden items-center gap-1 md:flex">
+            <NavigationLinks />
+          </div>
+          <button
+            type="button"
+            className="public-menu-button md:hidden"
+            aria-controls="public-mobile-navigation"
+            aria-expanded={menuOpen}
+            aria-label={menuOpen ? "收起菜单" : "打开菜单"}
+            onClick={toggleMenu}
+          >
+            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
+          </button>
+          {menuOpen ? (
+            <div
+              id="public-mobile-navigation"
+              className="public-mobile-navigation md:hidden"
+            >
+              <NavigationLinks onNavigate={closeMenu} />
+            </div>
+          ) : null}
+        </nav>
+      </div>
+    </header>
+  )
+}
+
+export default PublicHeader
diff --git a/frontend/src/components/PublicSite/PublicLayout.tsx b/frontend/src/components/PublicSite/PublicLayout.tsx
new file mode 100644
index 0000000..7bb6666
--- /dev/null
+++ b/frontend/src/components/PublicSite/PublicLayout.tsx
@@ -0,0 +1,20 @@
+import type { ReactNode } from "react"
+
+import PublicFooter from "./PublicFooter"
+import PublicHeader from "./PublicHeader"
+
+interface PublicLayoutProps {
+  children: ReactNode
+}
+
+export function PublicLayout({ children }: PublicLayoutProps) {
+  return (
+    <div className="public-site flex min-h-svh flex-col">
+      <PublicHeader />
+      <main className="min-w-0 flex-1">{children}</main>
+      <PublicFooter />
+    </div>
+  )
+}
+
+export default PublicLayout
diff --git a/frontend/src/components/Sidebar/AppSidebar.tsx b/frontend/src/components/Sidebar/AppSidebar.tsx
index 8502bcb..0442aa0 100644
--- a/frontend/src/components/Sidebar/AppSidebar.tsx
+++ b/frontend/src/components/Sidebar/AppSidebar.tsx
@@ -6,21 +6,21 @@ import {
   Sidebar,
   SidebarContent,
   SidebarFooter,
   SidebarHeader,
 } from "@/components/ui/sidebar"
 import useAuth from "@/hooks/useAuth"
 import { type Item, Main } from "./Main"
 import { User } from "./User"
 
 const baseItems: Item[] = [
-  { icon: Home, title: "Dashboard", path: "/" },
+  { icon: Home, title: "Dashboard", path: "/dashboard" },
   { icon: Briefcase, title: "Items", path: "/items" },
 ]
 
 export function AppSidebar() {
   const { user: currentUser } = useAuth()
 
   const items = currentUser?.is_superuser
     ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
     : baseItems
 
diff --git a/frontend/src/hooks/useAuth.ts b/frontend/src/hooks/useAuth.ts
index 9c6cfc7..ba37f06 100644
--- a/frontend/src/hooks/useAuth.ts
+++ b/frontend/src/hooks/useAuth.ts
@@ -45,21 +45,21 @@ const useAuth = () => {
   const login = async (data: AccessToken) => {
     const response = await LoginService.loginAccessToken({
       body: data,
     })
     localStorage.setItem("access_token", response.data.access_token)
   }
 
   const loginMutation = useMutation({
     mutationFn: login,
     onSuccess: () => {
-      navigate({ to: "/" })
+      navigate({ to: "/dashboard" })
     },
     onError: handleError.bind(showErrorToast),
   })
 
   const logout = () => {
     void client
       .post({ url: "/api/v1/auth/logout", throwOnError: true })
       .finally(() => {
         localStorage.removeItem("access_token")
         localStorage.removeItem("session_authenticated")
diff --git a/frontend/src/index.css b/frontend/src/index.css
index 47e5696..a042441 100644
--- a/frontend/src/index.css
+++ b/frontend/src/index.css
@@ -36,38 +36,46 @@
   --color-sidebar-primary: var(--sidebar-primary);
   --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
   --color-sidebar-accent: var(--sidebar-accent);
   --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
   --color-sidebar-border: var(--sidebar-border);
   --color-sidebar-ring: var(--sidebar-ring);
 }
 
 :root {
   --radius: 0.625rem;
-  --background: oklch(1 0 0);
-  --foreground: oklch(0.145 0 0);
-  --card: oklch(1 0 0);
-  --card-foreground: oklch(0.145 0 0);
-  --popover: oklch(1 0 0);
-  --popover-foreground: oklch(0.145 0 0);
-  --primary: oklch(0.5982 0.10687 182.4689);
-  --primary-foreground: oklch(0.985 0 0);
-  --secondary: oklch(0.97 0 0);
-  --secondary-foreground: oklch(0.205 0 0);
-  --muted: oklch(0.97 0 0);
-  --muted-foreground: oklch(0.556 0 0);
-  --accent: oklch(0.97 0 0);
-  --accent-foreground: oklch(0.205 0 0);
-  --destructive: oklch(0.577 0.245 27.325);
-  --border: oklch(0.922 0 0);
-  --input: oklch(0.922 0 0);
-  --ring: oklch(0.708 0 0);
+  --yeyu-paper: #f4f3ee;
+  --yeyu-paper-strong: #fffdf8;
+  --yeyu-ink: #17211f;
+  --yeyu-muted: #53635f;
+  --yeyu-teal: #197c72;
+  --yeyu-mint: #ddede7;
+  --yeyu-amber: #b45309;
+  --yeyu-line: #cbd8d3;
+  --background: var(--yeyu-paper);
+  --foreground: var(--yeyu-ink);
+  --card: var(--yeyu-paper-strong);
+  --card-foreground: var(--yeyu-ink);
+  --popover: var(--yeyu-paper-strong);
+  --popover-foreground: var(--yeyu-ink);
+  --primary: var(--yeyu-teal);
+  --primary-foreground: #ffffff;
+  --secondary: var(--yeyu-mint);
+  --secondary-foreground: var(--yeyu-ink);
+  --muted: #e8eee9;
+  --muted-foreground: var(--yeyu-muted);
+  --accent: #e6f0ec;
+  --accent-foreground: var(--yeyu-ink);
+  --destructive: #b42318;
+  --border: var(--yeyu-line);
+  --input: var(--yeyu-line);
+  --ring: var(--yeyu-teal);
   --chart-1: oklch(0.646 0.222 41.116);
   --chart-2: oklch(0.6 0.118 184.704);
   --chart-3: oklch(0.398 0.07 227.392);
   --chart-4: oklch(0.828 0.189 84.429);
   --chart-5: oklch(0.769 0.188 70.08);
   --sidebar: oklch(0.985 0 0);
   --sidebar-foreground: oklch(0.145 0 0);
   --sidebar-primary: oklch(0.5982 0.10687 182.4689);
   --sidebar-primary-foreground: oklch(0.985 0 0);
   --sidebar-accent: oklch(0.97 0 0);
@@ -107,18 +115,474 @@
   --sidebar-accent: oklch(0.269 0 0);
   --sidebar-accent-foreground: oklch(0.985 0 0);
   --sidebar-border: oklch(1 0 0 / 10%);
   --sidebar-ring: oklch(0.556 0 0);
 }
 
 @layer base {
   * {
     @apply border-border outline-ring/50;
   }
+
   body {
     @apply bg-background text-foreground;
+    min-width: 320px;
+    overflow-x: hidden;
+    font-family:
+      ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
+      "Microsoft YaHei", sans-serif;
   }
+
   button,
   [role="button"] {
     cursor: pointer;
   }
+
+  :where(a, button, input, select, textarea):focus-visible {
+    outline: 3px solid var(--yeyu-teal);
+    outline-offset: 3px;
+  }
+}
+
+.public-site {
+  --background: var(--yeyu-paper);
+  --foreground: var(--yeyu-ink);
+  --card: var(--yeyu-paper-strong);
+  --card-foreground: var(--yeyu-ink);
+  --popover: var(--yeyu-paper-strong);
+  --popover-foreground: var(--yeyu-ink);
+  --primary: var(--yeyu-teal);
+  --primary-foreground: #ffffff;
+  --secondary: var(--yeyu-mint);
+  --secondary-foreground: var(--yeyu-ink);
+  --muted: #e8eee9;
+  --muted-foreground: var(--yeyu-muted);
+  --accent: #e6f0ec;
+  --accent-foreground: var(--yeyu-ink);
+  --border: var(--yeyu-line);
+  --input: var(--yeyu-line);
+  --ring: var(--yeyu-teal);
+  background: var(--yeyu-paper);
+  color: var(--yeyu-ink);
+  color-scheme: light;
+}
+
+.public-container {
+  width: min(calc(100% - 2rem), 72rem);
+  margin-inline: auto;
+}
+
+.public-header {
+  position: relative;
+  z-index: 20;
+  border-bottom: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper);
+}
+
+.public-header-inner {
+  display: flex;
+  min-height: 4.5rem;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+}
+
+.public-nav {
+  position: relative;
+  margin-left: auto;
+}
+
+.public-nav-link {
+  color: var(--yeyu-muted);
+  text-decoration: none;
+  transition:
+    background-color 160ms ease,
+    color 160ms ease;
+}
+
+.public-nav-link:hover {
+  background: var(--yeyu-mint);
+  color: var(--yeyu-ink);
+}
+
+.public-nav-link-primary {
+  background: var(--yeyu-teal);
+  color: #ffffff;
+}
+
+.public-nav-link-primary:hover {
+  background: #12665e;
+  color: #ffffff;
+}
+
+.public-menu-button {
+  display: inline-flex;
+  height: 2.5rem;
+  width: 2.5rem;
+  align-items: center;
+  justify-content: center;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.375rem;
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-ink);
+}
+
+.public-mobile-navigation {
+  position: absolute;
+  top: calc(100% + 0.75rem);
+  right: 0;
+  z-index: 30;
+  min-width: 14rem;
+  gap: 0.25rem;
+  padding: 0.5rem;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.5rem;
+  background: var(--yeyu-paper-strong);
+  box-shadow: 0 12px 30px rgb(23 33 31 / 12%);
+}
+
+.public-mobile-navigation > * {
+  display: block;
+  width: 100%;
+}
+
+.public-hero {
+  display: grid;
+  gap: 2rem;
+  padding-block: clamp(3.5rem, 9vw, 7rem);
+}
+
+.public-hero-copy {
+  max-width: 48rem;
+}
+
+.public-eyebrow {
+  margin: 0;
+  color: var(--yeyu-teal);
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  font-size: 0.75rem;
+  font-weight: 700;
+  letter-spacing: 0.16em;
+  line-height: 1.5;
+  text-transform: uppercase;
+}
+
+.public-hero-title {
+  max-width: 13ch;
+  margin-top: 1rem;
+  color: var(--yeyu-ink);
+  font-size: clamp(2.5rem, 7vw, 5.5rem);
+  font-weight: 700;
+  letter-spacing: -0.055em;
+  line-height: 0.98;
+}
+
+.public-hero-lede {
+  max-width: 42rem;
+  margin-top: 1.5rem;
+  color: var(--yeyu-muted);
+  font-size: clamp(1rem, 2vw, 1.2rem);
+  line-height: 1.8;
+}
+
+.public-search-form {
+  display: flex;
+  max-width: 44rem;
+  flex-wrap: wrap;
+  gap: 0.75rem;
+  margin-top: 2rem;
+}
+
+.public-search-input {
+  min-width: 0;
+  flex: 1 1 16rem;
+  height: 3rem;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.375rem;
+  background: var(--yeyu-paper-strong);
+  padding-inline: 1rem;
+  color: var(--yeyu-ink);
+}
+
+.public-search-input::placeholder {
+  color: var(--yeyu-muted);
+  opacity: 0.8;
+}
+
+.public-primary-button {
+  display: inline-flex;
+  min-height: 3rem;
+  align-items: center;
+  justify-content: center;
+  gap: 0.5rem;
+  border: 0;
+  border-radius: 0.375rem;
+  background: var(--yeyu-teal);
+  padding: 0.75rem 1.1rem;
+  color: #ffffff;
+  font-size: 0.9rem;
+  font-weight: 700;
+  text-decoration: none;
+  transition:
+    background-color 160ms ease,
+    transform 160ms ease;
+}
+
+.public-primary-button:hover {
+  background: #12665e;
+  transform: translateY(-1px);
+}
+
+.public-hero-links {
+  display: flex;
+  flex-wrap: wrap;
+  gap: 1.25rem;
+  margin-top: 1.25rem;
+}
+
+.public-text-link,
+.public-footer-link {
+  color: var(--yeyu-teal);
+  font-size: 0.9rem;
+  font-weight: 700;
+  text-underline-offset: 0.25rem;
+}
+
+.public-text-link:hover,
+.public-footer-link:hover {
+  text-decoration: underline;
+}
+
+.public-boundary-note {
+  align-self: end;
+  max-width: 28rem;
+  padding: 1.5rem;
+  border-left: 4px solid var(--yeyu-amber);
+  background: var(--yeyu-mint);
+}
+
+.public-note-title {
+  margin-top: 0.75rem;
+  color: var(--yeyu-ink);
+  font-size: 1.5rem;
+  font-weight: 700;
+  letter-spacing: -0.02em;
+}
+
+.public-note-copy,
+.public-section-copy {
+  margin-top: 0.75rem;
+  color: var(--yeyu-muted);
+  line-height: 1.75;
+}
+
+.public-note-rule {
+  height: 1px;
+  margin-block: 1.25rem;
+  background: var(--yeyu-line);
+}
+
+.public-note-label {
+  color: var(--yeyu-muted);
+  font-size: 0.75rem;
+  font-weight: 700;
+  letter-spacing: 0.12em;
+  text-transform: uppercase;
+}
+
+.public-code-chip,
+.public-path-line,
+.public-path-line code {
+  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+}
+
+.public-code-chip {
+  display: inline-block;
+  margin-top: 0.5rem;
+  padding: 0.35rem 0.5rem;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.25rem;
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-ink);
+  font-size: 0.85rem;
+}
+
+.public-section {
+  padding-block: clamp(3rem, 7vw, 5.5rem);
+  border-top: 1px solid var(--yeyu-line);
+}
+
+.public-section-heading {
+  display: flex;
+  align-items: end;
+  justify-content: space-between;
+  gap: 1.5rem;
+}
+
+.public-section-title {
+  margin-top: 0.75rem;
+  color: var(--yeyu-ink);
+  font-size: clamp(1.75rem, 4vw, 3rem);
+  font-weight: 700;
+  letter-spacing: -0.04em;
+  line-height: 1.05;
+}
+
+.public-catalog-list {
+  display: grid;
+  gap: 0.75rem;
+  margin-top: 2rem;
+  padding: 0;
+  list-style: none;
+}
+
+.public-catalog-row {
+  display: grid;
+  grid-template-columns: minmax(12rem, 0.8fr) minmax(0, 1.6fr) auto;
+  gap: 1rem;
+  align-items: center;
+  padding: 1rem;
+  border: 1px solid var(--yeyu-line);
+  border-radius: 0.375rem;
+  background: var(--yeyu-paper-strong);
+}
+
+.public-path-line {
+  display: flex;
+  min-width: 0;
+  align-items: center;
+  gap: 0.65rem;
+  color: var(--yeyu-ink);
+  font-size: 0.85rem;
+  overflow-x: auto;
+  white-space: nowrap;
+}
+
+.public-method-badge {
+  flex: 0 0 auto;
+  color: var(--yeyu-teal);
+  font-size: 0.72rem;
+  font-weight: 800;
+  letter-spacing: 0.08em;
+}
+
+.public-catalog-meta {
+  display: flex;
+  flex-wrap: wrap;
+  justify-content: flex-end;
+  gap: 0.5rem 0.75rem;
+  color: var(--yeyu-muted);
+  font-size: 0.78rem;
+  text-align: right;
+}
+
+.public-state {
+  margin-top: 2rem;
+  padding: 1.25rem;
+  border: 1px dashed var(--yeyu-line);
+  border-radius: 0.375rem;
+  background: var(--yeyu-paper-strong);
+  color: var(--yeyu-muted);
+  line-height: 1.7;
+}
+
+.public-state-error {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+  border-color: var(--yeyu-amber);
+}
+
+.public-inline-button {
+  flex: 0 0 auto;
+  color: var(--yeyu-teal);
+  font-weight: 700;
+  text-decoration: underline;
+  text-underline-offset: 0.25rem;
+}
+
+.public-usage-section {
+  display: grid;
+  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
+  gap: 2rem;
+}
+
+.public-usage-grid {
+  display: grid;
+  gap: 1rem;
+  color: var(--yeyu-muted);
+  line-height: 1.75;
+}
+
+.public-usage-grid p {
+  padding-left: 1rem;
+  border-left: 2px solid var(--yeyu-teal);
+}
+
+.public-bottom-cta {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 1rem;
+  padding-block: 2rem 4rem;
+  color: var(--yeyu-ink);
+  font-weight: 700;
+}
+
+.public-footer {
+  border-top: 1px solid var(--yeyu-line);
+  background: var(--yeyu-paper-strong);
+}
+
+.public-footer-link {
+  color: var(--yeyu-muted);
+  font-weight: 600;
+}
+
+.logo-mark {
+  display: inline-flex;
+  height: 1.75rem;
+  width: 1.75rem;
+  align-items: center;
+  justify-content: center;
+  border-radius: 0.25rem;
+  background: var(--yeyu-teal);
+  color: #ffffff;
+  font-size: 0.85em;
+  font-weight: 800;
+}
+
+@media (min-width: 768px) {
+  .public-hero {
+    grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.65fr);
+    align-items: end;
+  }
+}
+
+@media (max-width: 767px) {
+  .public-section-heading,
+  .public-bottom-cta {
+    align-items: flex-start;
+    flex-direction: column;
+  }
+
+  .public-catalog-row,
+  .public-usage-section {
+    grid-template-columns: 1fr;
+  }
+
+  .public-catalog-meta {
+    justify-content: flex-start;
+    text-align: left;
+  }
+}
+
+@media (prefers-reduced-motion: reduce) {
+  *,
+  *::before,
+  *::after {
+    scroll-behavior: auto;
+    transition: none;
+    animation: none;
+  }
 }
diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
index 7bafdf7..9d9f7c3 100644
--- a/frontend/src/routes/_layout.tsx
+++ b/frontend/src/routes/_layout.tsx
@@ -19,22 +19,25 @@ export const Route = createFileRoute("/_layout")({
     }
   },
 })
 
 function Layout() {
   return (
     <SidebarProvider>
       <AppSidebar />
       <SidebarInset>
         <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
-          <SidebarTrigger className="-ml-1 text-muted-foreground" />
+          <SidebarTrigger
+            className="-ml-1 text-muted-foreground"
+            aria-label="切换侧边栏"
+          />
         </header>
-        <main className="flex-1 p-6 md:p-8">
+        <main id="main-content" className="flex-1 p-6 md:p-8">
           <div className="mx-auto max-w-7xl">
             <Outlet />
           </div>
         </main>
         <Footer />
       </SidebarInset>
     </SidebarProvider>
   )
 }
diff --git a/frontend/src/routes/_layout/dashboard.tsx b/frontend/src/routes/_layout/dashboard.tsx
new file mode 100644
index 0000000..436dd2b
--- /dev/null
+++ b/frontend/src/routes/_layout/dashboard.tsx
@@ -0,0 +1,34 @@
+import { createFileRoute } from "@tanstack/react-router"
+
+import useAuth from "@/hooks/useAuth"
+
+export const Route = createFileRoute("/_layout/dashboard")({
+  component: Dashboard,
+  head: () => ({
+    meta: [
+      {
+        title: "Yeyu API 控制台",
+      },
+    ],
+  }),
+})
+
+function Dashboard() {
+  const { user: currentUser } = useAuth()
+  const displayName = currentUser?.full_name || currentUser?.email || "开发者"
+
+  return (
+    <section className="flex flex-col gap-3" data-testid="dashboard-page">
+      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
+        Yeyu API / 控制台
+      </p>
+      <h1 className="max-w-2xl truncate text-3xl font-semibold tracking-tight">
+        Yeyu API 控制台
+      </h1>
+      <p className="text-lg text-muted-foreground">你好，{displayName}。</p>
+      <p className="max-w-2xl text-muted-foreground">
+        在这里管理你的账户、API Key 和调用设置。公共目录仍然可以从站点首页查看。
+      </p>
+    </section>
+  )
+}
diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
deleted file mode 100644
index 3e640cb..0000000
--- a/frontend/src/routes/_layout/index.tsx
+++ /dev/null
@@ -1,31 +0,0 @@
-import { createFileRoute } from "@tanstack/react-router"
-
-import useAuth from "@/hooks/useAuth"
-
-export const Route = createFileRoute("/_layout/")({
-  component: Dashboard,
-  head: () => ({
-    meta: [
-      {
-        title: "Dashboard - FastAPI Template",
-      },
-    ],
-  }),
-})
-
-function Dashboard() {
-  const { user: currentUser } = useAuth()
-
-  return (
-    <div>
-      <div>
-        <h1 className="text-2xl truncate max-w-sm">
-          Hi, {currentUser?.full_name || currentUser?.email} 👋
-        </h1>
-        <p className="text-muted-foreground">
-          Welcome back, nice to see you again!!!
-        </p>
-      </div>
-    </div>
-  )
-}
diff --git a/frontend/src/routes/index.tsx b/frontend/src/routes/index.tsx
new file mode 100644
index 0000000..ae23cfe
--- /dev/null
+++ b/frontend/src/routes/index.tsx
@@ -0,0 +1,212 @@
+import { useQuery } from "@tanstack/react-query"
+import { createFileRoute, Link } from "@tanstack/react-router"
+
+import { CatalogService } from "@/client"
+import PublicLayout from "@/components/PublicSite/PublicLayout"
+
+export const Route = createFileRoute("/")({
+  component: PublicHome,
+  head: () => ({
+    meta: [
+      {
+        title: "Yeyu API 公益工具箱",
+      },
+    ],
+  }),
+})
+
+function formatUpdatedAt(value?: string | null) {
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
+function CatalogPreview() {
+  const catalogQuery = useQuery({
+    queryKey: ["public-catalog-preview"],
+    queryFn: async () => {
+      const response = await CatalogService.searchCatalog({
+        query: {
+          page: 1,
+          page_size: 4,
+        },
+      })
+      return response.data
+    },
+  })
+
+  const items = catalogQuery.data?.data ?? []
+
+  return (
+    <section
+      id="catalog"
+      className="public-section public-catalog-section"
+      aria-labelledby="catalog-heading"
+    >
+      <div className="public-section-heading">
+        <div>
+          <p className="public-eyebrow">目录入口</p>
+          <h2 id="catalog-heading" className="public-section-title">
+            从真实目录开始
+          </h2>
+          <p className="public-section-copy">
+            这里展示后端公开目录中的接口，不展示虚构卡片或调用统计。
+          </p>
+        </div>
+        <a className="public-text-link" href="/catalog">
+          搜索完整目录 <span aria-hidden="true">→</span>
+        </a>
+      </div>
+
+      {catalogQuery.isPending ? (
+        <p className="public-state" role="status">
+          正在读取真实目录……
+        </p>
+      ) : null}
+
+      {catalogQuery.isError ? (
+        <div className="public-state public-state-error" role="alert">
+          <p>目录暂时无法读取，请稍后重试。</p>
+          <button
+            type="button"
+            className="public-inline-button"
+            onClick={() => void catalogQuery.refetch()}
+          >
+            重试
+          </button>
+        </div>
+      ) : null}
+
+      {!catalogQuery.isPending &&
+      !catalogQuery.isError &&
+      items.length === 0 ? (
+        <p className="public-state">当前没有可公开的接口，请稍后再来查看。</p>
+      ) : null}
+
+      {!catalogQuery.isPending && !catalogQuery.isError && items.length > 0 ? (
+        <ul className="public-catalog-list" data-testid="catalog-preview-list">
+          {items.map((item) => (
+            <li key={item.slug} className="public-catalog-row">
+              <div className="public-path-line">
+                <span className="public-method-badge">{item.method}</span>
+                <code>{item.path}</code>
+              </div>
+              <div className="min-w-0">
+                <h3 className="truncate text-base font-semibold text-[var(--yeyu-ink)]">
+                  {item.name}
+                </h3>
+                <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
+                  {item.summary}
+                </p>
+              </div>
+              <div className="public-catalog-meta">
+                <span>{item.category}</span>
+                <time dateTime={item.updated_at ?? undefined}>
+                  {formatUpdatedAt(item.updated_at)}
+                </time>
+              </div>
+            </li>
+          ))}
+        </ul>
+      ) : null}
+    </section>
+  )
+}
+
+function PublicHome() {
+  return (
+    <PublicLayout>
+      <div className="public-container">
+        <section className="public-hero" aria-labelledby="home-heading">
+          <div className="public-hero-copy">
+            <p className="public-eyebrow">YEYU API / 公益工具箱</p>
+            <h1 id="home-heading" className="public-hero-title">
+              给学生和个人开发者的免费 API 工具箱
+            </h1>
+            <p className="public-hero-lede">
+              从清楚的接口文档开始，按公开规范调用稳定、可核验的自营工具。
+            </p>
+            <form className="public-search-form" action="/catalog" method="get">
+              <label className="sr-only" htmlFor="catalog-query">
+                搜索 API 目录
+              </label>
+              <input
+                id="catalog-query"
+                name="query"
+                className="public-search-input"
+                placeholder="搜索时间戳、UUID、天气……"
+                type="search"
+              />
+              <button className="public-primary-button" type="submit">
+                搜索 API 目录
+              </button>
+            </form>
+            <nav className="public-hero-links" aria-label="快速入口">
+              <a className="public-text-link" href="/catalog">
+                浏览公开目录 <span aria-hidden="true">↗</span>
+              </a>
+              <a className="public-text-link" href="#usage">
+                阅读使用规范 <span aria-hidden="true">↓</span>
+              </a>
+            </nav>
+          </div>
+
+          <aside
+            className="public-boundary-note"
+            aria-labelledby="boundary-heading"
+          >
+            <p className="public-eyebrow">调用边界</p>
+            <h2 id="boundary-heading" className="public-note-title">
+              先看清楚，再开始调用
+            </h2>
+            <p className="public-note-copy">
+              公共页面只负责发现和阅读目录。真正的工具调用需要独立 API
+              Key，浏览器登录状态不会替代它。
+            </p>
+            <div className="public-note-rule" aria-hidden="true" />
+            <p className="public-note-label">示例凭据</p>
+            <code className="public-code-chip">&lt;YOUR_API_KEY&gt;</code>
+          </aside>
+        </section>
+
+        <CatalogPreview />
+
+        <section
+          id="usage"
+          className="public-section public-usage-section"
+          aria-labelledby="usage-heading"
+        >
+          <div>
+            <p className="public-eyebrow">使用规范</p>
+            <h2 id="usage-heading" className="public-section-title">
+              公益服务也需要清楚的边界
+            </h2>
+          </div>
+          <div className="public-usage-grid">
+            <p>
+              只调用目录中公开、已发布的接口；参数、缓存和来源以对应文档为准。
+            </p>
+            <p>
+              请保管好自己的 API Key，不要把密钥提交到代码仓库或分享给他人。
+            </p>
+            <p>
+              发现异常或文档问题时，请停止重试并通过项目渠道反馈，给公共资源留下余量。
+            </p>
+          </div>
+        </section>
+
+        <div className="public-bottom-cta">
+          <p>准备好查找一个清楚、可用的接口了吗？</p>
+          <Link className="public-primary-button" to="/login">
+            登录并进入控制台
+          </Link>
+        </div>
+      </div>
+    </PublicLayout>
+  )
+}
diff --git a/frontend/src/routes/login.tsx b/frontend/src/routes/login.tsx
index 3f075c5..c2c02e2 100644
--- a/frontend/src/routes/login.tsx
+++ b/frontend/src/routes/login.tsx
@@ -39,45 +39,45 @@ type FormData = z.infer<typeof formSchema>
 const searchSchema = z.object({
   oauth: z.enum(["github"]).optional(),
 })
 
 export const Route = createFileRoute("/login")({
   component: Login,
   validateSearch: searchSchema,
   beforeLoad: async ({ search }) => {
     if (isLoggedIn() && search.oauth !== "github") {
       throw redirect({
-        to: "/",
+        to: "/dashboard",
       })
     }
   },
   head: () => ({
     meta: [
       {
-        title: "Log In - FastAPI Template",
+        title: "登录 - Yeyu API",
       },
     ],
   }),
 })
 
 function Login() {
   const { loginMutation } = useAuth()
   const navigate = Route.useNavigate()
   const search = Route.useSearch()
   const [oauthError, setOauthError] = useState<string | null>(null)
 
   useEffect(() => {
     if (search.oauth !== "github") return
     UsersService.readUserMe()
       .then(() => {
         localStorage.setItem("session_authenticated", "1")
-        void navigate({ to: "/" })
+        void navigate({ to: "/dashboard" })
       })
       .catch(() => {
         localStorage.removeItem("session_authenticated")
         setOauthError("GitHub 登录未完成，请先验证邮箱后再绑定 GitHub。")
       })
   }, [navigate, search.oauth])
   const form = useForm<FormData>({
     resolver: zodResolver(formSchema),
     mode: "onBlur",
     criteriaMode: "all",
diff --git a/frontend/tests/login.spec.ts b/frontend/tests/login.spec.ts
index 8072ddc..b399e9d 100644
--- a/frontend/tests/login.spec.ts
+++ b/frontend/tests/login.spec.ts
@@ -36,24 +36,24 @@ test("Forgot Password link is visible", async ({ page }) => {
     page.getByRole("link", { name: "Forgot your password?" }),
   ).toBeVisible()
 })
 
 test("Log in with valid email and password ", async ({ page }) => {
   await page.goto("/login")
 
   await fillForm(page, firstSuperuser, firstSuperuserPassword)
   await page.getByRole("button", { name: "Log In" }).click()
 
-  await page.waitForURL("/")
+  await page.waitForURL("/dashboard")
 
   await expect(
-    page.getByText("Welcome back, nice to see you again!"),
+    page.getByRole("heading", { name: "Yeyu API 控制台" }),
   ).toBeVisible()
 })
 
 test("Log in with invalid email", async ({ page }) => {
   await page.goto("/login")
 
   await fillForm(page, "invalidemail", firstSuperuserPassword)
   await page.getByRole("button", { name: "Log In" }).click()
 
   await expect(page.getByText("Invalid email address")).toBeVisible()
@@ -68,24 +68,24 @@ test("Log in with invalid password", async ({ page }) => {
 
   await expect(page.getByText("Incorrect email or password")).toBeVisible()
 })
 
 test("Successful log out", async ({ page }) => {
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
 })
 
 test("Logged-out user cannot access protected routes", async ({ page }) => {
   await page.goto("/login")
 
@@ -99,19 +99,40 @@ test("Logged-out user cannot access protected routes", async ({ page }) => {
   ).toBeVisible()
 
   await page.getByTestId("user-menu").click()
   await page.getByRole("menuitem", { name: "Log out" }).click()
   await page.waitForURL("/login")
 
   await page.goto("/settings")
   await page.waitForURL("/login")
 })
 
+test("Anonymous users are redirected to login from items", async ({ page }) => {
+  await page.goto("/items")
+
+  await page.waitForURL("/login")
+  await expect(page).toHaveURL("/login")
+})
+
+test("Logged-in users are redirected from login to dashboard", async ({
+  page,
+}) => {
+  await page.goto("/login")
+
+  await fillForm(page, firstSuperuser, firstSuperuserPassword)
+  await page.getByRole("button", { name: "Log In" }).click()
+  await page.waitForURL("/dashboard")
+
+  await page.goto("/login")
+  await page.waitForURL("/dashboard")
+  await expect(page).toHaveURL("/dashboard")
+})
+
 test("Redirects to /login when token is wrong", async ({ page }) => {
   await page.goto("/settings")
   await page.evaluate(() => {
     localStorage.setItem("access_token", "invalid_token")
   })
   await page.goto("/settings")
   await page.waitForURL("/login")
   await expect(page).toHaveURL("/login")
 })
diff --git a/frontend/tests/public-catalog.spec.ts b/frontend/tests/public-catalog.spec.ts
new file mode 100644
index 0000000..1c5789d
--- /dev/null
+++ b/frontend/tests/public-catalog.spec.ts
@@ -0,0 +1,39 @@
+import { expect, test } from "@playwright/test"
+
+test.use({ storageState: { cookies: [], origins: [] } })
+
+test("Anonymous users can open the public home without login redirect", async ({
+  page,
+}) => {
+  await page.goto("/")
+
+  await expect(page).toHaveURL(/\/$/)
+  await expect(
+    page.getByRole("heading", {
+      name: "给学生和个人开发者的免费 API 工具箱",
+    }),
+  ).toBeVisible()
+  await expect(page).not.toHaveURL(/\/login/)
+})
+
+test("Anonymous users can open the catalog entry without login redirect", async ({
+  page,
+}) => {
+  await page.goto("/catalog")
+
+  await expect(page).not.toHaveURL(/\/login/)
+})
+
+test("Public navigation exposes keyboard-accessible catalog and login links", async ({
+  page,
+}) => {
+  await page.setViewportSize({ width: 390, height: 844 })
+  await page.goto("/")
+
+  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
+  await expect(page.getByRole("link", { name: "API 目录" })).toBeVisible()
+  await expect(page.getByRole("link", { name: "登录" })).toBeVisible()
+
+  await page.getByRole("link", { name: "登录" }).focus()
+  await expect(page.getByRole("link", { name: "登录" })).toBeFocused()
+})
diff --git a/plans/agent-reports/task-7-2-report.md b/plans/agent-reports/task-7-2-report.md
new file mode 100644
index 0000000..c795cbd
--- /dev/null
+++ b/plans/agent-reports/task-7-2-report.md
@@ -0,0 +1,106 @@
+# Task 7-2 实现报告：拆分公共和受保护的前端路由壳层
+
+## 范围与结果
+
+- 基线：`e125ac2`（任务 1 的 `feb0136` 已在历史中）。
+- 已实现公共首页 `/`，使用生成的 `CatalogService.searchCatalog` 读取真实目录；加载、错误、空结果和搜索入口均有明确状态，不硬编码接口卡片或统计。
+- 已实现 `PublicLayout`、`PublicHeader`、`PublicFooter`，包含首页、API 目录、使用规范、登录/控制台入口，以及移动端可折叠且可键盘访问的导航。
+- 已将受保护首页迁移为 `/dashboard`，保留 `_layout.tsx` 的认证 `beforeLoad`，并保留当前用户欢迎信息。
+- 已统一密码登录成功、GitHub callback 成功和已登录访问 `/login` 的目标为 `/dashboard`；登出仍跳转 `/login`。
+- 已更新侧边栏 Dashboard、Logo、Footer 和本地 CSS 变量，移除已使用组件中的 FastAPI Template 品牌链接与文案。
+- 未手改 `frontend/src/routeTree.gen.ts`；该文件仍需要 TanStack Router/Vite 生成。
+- 未实现任务 3 的完整 `/catalog` 目录页、筛选、详情页或代码示例页。
+
+## 修改文件
+
+实现文件：
+
+- `frontend/src/routes/index.tsx`
+- `frontend/src/routes/_layout/dashboard.tsx`
+- `frontend/src/routes/_layout.tsx`
+- 删除 `frontend/src/routes/_layout/index.tsx`
+- `frontend/src/components/PublicSite/PublicLayout.tsx`
+- `frontend/src/components/PublicSite/PublicHeader.tsx`
+- `frontend/src/components/PublicSite/PublicFooter.tsx`
+- `frontend/src/hooks/useAuth.ts`
+- `frontend/src/routes/login.tsx`
+- `frontend/src/components/Sidebar/AppSidebar.tsx`
+- `frontend/src/components/Common/Logo.tsx`
+- `frontend/src/components/Common/Footer.tsx`
+- `frontend/src/index.css`
+
+测试文件：
+
+- `frontend/tests/login.spec.ts`
+- `frontend/tests/public-catalog.spec.ts`
+
+未修改：
+
+- `frontend/src/routeTree.gen.ts`（按任务要求不手改）
+- `E:\AI_projects\yeyubakahome_Web`、线上服务、DNS、Nginx、服务器和凭据。
+
+## TDD RED/GREEN 证据
+
+### RED
+
+命令：
+
+```powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec playwright test tests/public-catalog.spec.ts tests/login.spec.ts
+```
+
+真实结果：退出码 `1`。测试收集阶段报错：`Environment variable FIRST_SUPERUSER is undefined`，未进入浏览器测试。
+
+为排除测试账号收集阻塞，仅使用进程级非真实占位值重试公共边界：
+
+```powershell
+$env:FIRST_SUPERUSER='red@example.com'
+$env:FIRST_SUPERUSER_PASSWORD='not-a-real-password'
+pnpm exec playwright test tests/public-catalog.spec.ts
+```
+
+真实结果：退出码 `1`。Playwright setup 阶段报错：
+`Executable doesn't exist at C:\Users\21239\AppData\Local\ms-playwright\chromium_headless_shell-1234\chrome-headless-shell-win64\chrome-headless-shell.exe`。
+该测试进程随后已停止；未将未执行的浏览器断言标记为通过。
+
+### GREEN / 静态检查
+
+Biome 修复格式和静态问题后执行：
+
+```powershell
+Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
+pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
+```
+
+真实结果：退出码 `0`，`Checked 63 files in 31ms. No fixes applied.`
+
+Playwright GREEN：未运行。由于 Chromium 可执行文件缺失，且用户要求本次不再运行浏览器或长时间命令，保持为未验证。
+
+## 其他验证与阻塞
+
+1. `pnpm build` 已执行，退出码 `2`。TypeScript 报告 `/dashboard` 和新的公共 `/` 不在旧 `routeTree.gen.ts` 类型中；构建脚本先执行 `tsc`、后执行 Vite 路由生成，因此未进入 Vite 阶段。
+2. 为使用官方 Vite/TanStack 生成链刷新路由树，执行 `pnpm exec vite build`，退出码 `1`。Vite 配置加载失败：`Failed to load native binding`；缺少 `./swc.win32-x64-msvc.node`，并报告 `ERR_SWC_NATIVE_CACHE` 及 SWC 缓存目录 DACL 权限问题。未手工写入生成路由树。
+3. Docker、数据库、SMTP、GitHub OAuth、DNS、Nginx 和线上服务验收本任务未运行，均未验证。
+
+## Self-review
+
+- 路由边界：公共 `/` 不挂载受保护 `_layout`；`/items`、`/settings`、`/admin` 仍挂载认证 layout；`/dashboard` 使用同一认证门禁。
+- 跳转边界：密码登录、GitHub callback、已登录访问 `/login` 和侧栏 Dashboard 均指向 `/dashboard`；登出仍清理本地认证标记并前往 `/login`。
+- 数据边界：首页只调用公开 `CatalogService.searchCatalog`，不伪造数据、统计、上游 URL 或 API Key；示例凭据仅为 `<YOUR_API_KEY>`。
+- 可访问性：公共页面使用 `header`、`nav`、`main`、`footer`、表单标签、`role=status`、`role=alert` 和可见 `:focus-visible` 焦点环；移动菜单使用 `aria-expanded`、`aria-controls` 和键盘可聚焦按钮。
+- 品牌边界：改动的 Logo/Footer/登录标题不再引用 FastAPI；未扩展修改任务简报之外的旧路由文件。
+- 独立只读子代理：当前会话未提供可调用的子代理工具，因此没有伪造独立审查结果；本报告仅记录主代理的只读 self-review。
+
+## 提交
+
+- 实现提交主题：`feat: split public and protected web shells`
+- 提交 SHA：`0acbfc3`。
+- 报告状态：本文件随实现提交写入；本次回填 SHA 后产生一个仅文档的收尾提交。
+
+## 未验证项
+
+- 真实 Chromium 浏览器中的匿名 `/`、`/catalog`、登录成功 `/dashboard`、登出和 `/items` 认证跳转。
+- TanStack Router 生成 `routeTree.gen.ts` 后的最终 TypeScript/build 结果。
+- 真实后端目录 API 返回项在浏览器中的展示。
+- 生产环境、Docker Compose、数据库、SMTP、GitHub OAuth、DNS、TLS、Nginx 和线上回归。
