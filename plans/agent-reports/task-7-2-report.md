# Task 7-2 实现报告：拆分公共和受保护的前端路由壳层

## 范围与结果

- 基线：`e125ac2`（任务 1 的 `feb0136` 已在历史中）。
- 已实现公共首页 `/`，使用生成的 `CatalogService.searchCatalog` 读取真实目录；加载、错误、空结果和搜索入口均有明确状态，不硬编码接口卡片或统计。
- 已实现 `PublicLayout`、`PublicHeader`、`PublicFooter`，包含首页、API 目录、使用规范、登录/控制台入口，以及移动端可折叠且可键盘访问的导航。
- 已将受保护首页迁移为 `/dashboard`，保留 `_layout.tsx` 的认证 `beforeLoad`，并保留当前用户欢迎信息。
- 已统一密码登录成功、GitHub callback 成功和已登录访问 `/login` 的目标为 `/dashboard`；登出仍跳转 `/login`。
- 已更新侧边栏 Dashboard、Logo、Footer 和本地 CSS 变量，移除已使用组件中的 FastAPI Template 品牌链接与文案。
- 未手改 `frontend/src/routeTree.gen.ts`；该文件仍需要 TanStack Router/Vite 生成。
- 未实现任务 3 的完整 `/catalog` 目录页、筛选、详情页或代码示例页。

## 修改文件

实现文件：

- `frontend/src/routes/index.tsx`
- `frontend/src/routes/_layout/dashboard.tsx`
- `frontend/src/routes/_layout.tsx`
- 删除 `frontend/src/routes/_layout/index.tsx`
- `frontend/src/components/PublicSite/PublicLayout.tsx`
- `frontend/src/components/PublicSite/PublicHeader.tsx`
- `frontend/src/components/PublicSite/PublicFooter.tsx`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/routes/login.tsx`
- `frontend/src/components/Sidebar/AppSidebar.tsx`
- `frontend/src/components/Common/Logo.tsx`
- `frontend/src/components/Common/Footer.tsx`
- `frontend/src/index.css`

测试文件：

- `frontend/tests/login.spec.ts`
- `frontend/tests/public-catalog.spec.ts`

未修改：

- `frontend/src/routeTree.gen.ts`（按任务要求不手改）
- `E:\AI_projects\yeyubakahome_Web`、线上服务、DNS、Nginx、服务器和凭据。

## TDD RED/GREEN 证据

### RED

命令：

```powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec playwright test tests/public-catalog.spec.ts tests/login.spec.ts
```

真实结果：退出码 `1`。测试收集阶段报错：`Environment variable FIRST_SUPERUSER is undefined`，未进入浏览器测试。

为排除测试账号收集阻塞，仅使用进程级非真实占位值重试公共边界：

```powershell
$env:FIRST_SUPERUSER='red@example.com'
$env:FIRST_SUPERUSER_PASSWORD='not-a-real-password'
pnpm exec playwright test tests/public-catalog.spec.ts
```

真实结果：退出码 `1`。Playwright setup 阶段报错：
`Executable doesn't exist at C:\Users\21239\AppData\Local\ms-playwright\chromium_headless_shell-1234\chrome-headless-shell-win64\chrome-headless-shell.exe`。
该测试进程随后已停止；未将未执行的浏览器断言标记为通过。

### GREEN / 静态检查

Biome 修复格式和静态问题后执行：

```powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
```

真实结果：退出码 `0`，`Checked 63 files in 31ms. No fixes applied.`

Playwright GREEN：未运行。由于 Chromium 可执行文件缺失，且用户要求本次不再运行浏览器或长时间命令，保持为未验证。

## 其他验证与阻塞

1. `pnpm build` 已执行，退出码 `2`。TypeScript 报告 `/dashboard` 和新的公共 `/` 不在旧 `routeTree.gen.ts` 类型中；构建脚本先执行 `tsc`、后执行 Vite 路由生成，因此未进入 Vite 阶段。
2. 为使用官方 Vite/TanStack 生成链刷新路由树，执行 `pnpm exec vite build`，退出码 `1`。Vite 配置加载失败：`Failed to load native binding`；缺少 `./swc.win32-x64-msvc.node`，并报告 `ERR_SWC_NATIVE_CACHE` 及 SWC 缓存目录 DACL 权限问题。未手工写入生成路由树。
3. Docker、数据库、SMTP、GitHub OAuth、DNS、Nginx 和线上服务验收本任务未运行，均未验证。

## Self-review

- 路由边界：公共 `/` 不挂载受保护 `_layout`；`/items`、`/settings`、`/admin` 仍挂载认证 layout；`/dashboard` 使用同一认证门禁。
- 跳转边界：密码登录、GitHub callback、已登录访问 `/login` 和侧栏 Dashboard 均指向 `/dashboard`；登出仍清理本地认证标记并前往 `/login`。
- 数据边界：首页只调用公开 `CatalogService.searchCatalog`，不伪造数据、统计、上游 URL 或 API Key；示例凭据仅为 `<YOUR_API_KEY>`。
- 可访问性：公共页面使用 `header`、`nav`、`main`、`footer`、表单标签、`role=status`、`role=alert` 和可见 `:focus-visible` 焦点环；移动菜单使用 `aria-expanded`、`aria-controls` 和键盘可聚焦按钮。
- 品牌边界：改动的 Logo/Footer/登录标题不再引用 FastAPI；未扩展修改任务简报之外的旧路由文件。
- 独立只读子代理：当前会话未提供可调用的子代理工具，因此没有伪造独立审查结果；本报告仅记录主代理的只读 self-review。

## 提交

- 实现提交主题：`feat: split public and protected web shells`
- 提交 SHA：`0acbfc3`。
- 报告状态：本文件随实现提交写入；本次回填 SHA 后产生一个仅文档的收尾提交。

## 未验证项

- 真实 Chromium 浏览器中的匿名 `/`、`/catalog`、登录成功 `/dashboard`、登出和 `/items` 认证跳转。
- TanStack Router 生成 `routeTree.gen.ts` 后的最终 TypeScript/build 结果。
- 真实后端目录 API 返回项在浏览器中的展示。
- 生产环境、Docker Compose、数据库、SMTP、GitHub OAuth、DNS、TLS、Nginx 和线上回归。
