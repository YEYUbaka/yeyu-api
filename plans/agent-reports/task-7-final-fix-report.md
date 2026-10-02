# Task 7 整体验收复审问题修复报告

## 结论

**DONE_WITH_CONCERNS**

已完成本次允许范围内的最小修复并生成提交。Task 7 总审查中的 Critical/Important 代码与证据问题已处理；前端完整 TypeScript、Vite build 和有效的 yeyu-api Playwright 运行时验收仍未通过或未获得有效环境证据，不能标记为完全验收通过。

本报告中的测试环境变量均为明确的非秘密占位值；未写入真实密码、Token、API Key 或 Secret。

## 修复内容

- 使用 TanStack Router 官方 generator API（与 `@tanstack/router-plugin` 同一官方生成链）刷新 `E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts`，没有手工编辑生成文件。
- 生成树现在包含公共 `/`、`/catalog`、`/catalog/$slug` 和受保护 `/dashboard`；其中生成器的 full-path 类型将目录文件表示为 `/catalog/`，to 类型和生成声明保留 `/catalog`。
- 将 `E:\AI_projects\yeyu-api\frontend\tests\auth.setup.ts` 的成功等待目标改为 `/dashboard`。
- 将 `public-catalog.spec.ts` 放入不依赖 setup 的 `public-chromium` 项目；受保护及登录测试仍由依赖 `setup` 的 `chromium` 项目运行。新增匿名首页回归断言。
- `ApiCatalogService.search()` 现在同时匹配 `slug`、`name`、`summary` 和 `path`；新增 `/v1/tools/time` 路径搜索后端回归测试。
- 将 `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md` 的状态改为“审查中止—未批准”，明确它不是独立 Approved 证据，未伪造复审结果。

## 修改文件

- `E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts`（仅由官方生成链产生）
- `E:\AI_projects\yeyu-api\frontend\tests\auth.setup.ts`
- `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`
- `E:\AI_projects\yeyu-api\frontend\playwright.config.ts`
- `E:\AI_projects\yeyu-api\backend\app\services\catalog.py`
- `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py`
- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md`
- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-final-fix-report.md`

未修改 `E:\AI_projects\yeyubakahome_Web`、旧 API 服务、服务器、DNS、Nginx、线上数据库或任何真实凭据。

## 命令与真实结果

### TDD 红测

命令（未提供配置时）：

```powershell
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\api\routes
```

原始结果：收集阶段因 Settings 缺少 `SECRET_KEY`、`PROJECT_NAME`、`DATABASE_URL`、`FIRST_SUPERUSER`、`FIRST_SUPERUSER_PASSWORD` 失败。

使用仅当前进程的非秘密测试占位配置重新执行同一测试后，新增路径测试在修复前真实失败：

```text
FAILED tests/api/routes/test_catalog.py::test_public_catalog_search_matches_api_path
1 failed, 5 passed
AssertionError: assert [] == ['time']
```

### 后端绿测与 Ruff

命令：

```powershell
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\api\routes
conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app\services\catalog.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py
```

原始结果：

```text
......                                                                   [100%]
6 passed, 3 warnings in 2.06s
All checks passed!
```

警告为 Starlette `httpx` 弃用提示、应用 frontend 目录不存在提示；没有测试失败。测试使用 SQLite fixture，没有连接线上数据库。

### Biome

命令：

```powershell
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
```

原始结果：

```text
Checked 74 files in 49ms. No fixes applied.
```

### TanStack Router 官方生成链

先尝试项目标准 Vite 链：

```powershell
pnpm exec vite build
```

原始阻塞：

```text
failed to load config from E:\AI_projects\YEYU-API\frontend\vite.config.ts
Error: Failed to load native binding
Cannot find module './swc.win32-x64-msvc.node'
Error: SWC native addon ... ERR_SWC_NATIVE_CACHE
```

因 Vite 在加载配置前被现有 `@swc/core` 原生绑定/DACL 缓存问题阻塞，使用同一 `@tanstack/router-plugin` 的官方 generator API 完成路由生成：

```powershell
node --input-type=module -e "import { unpluginRouterGeneratorFactory } from '@tanstack/router-plugin'; const plugin = unpluginRouterGeneratorFactory({ target: 'react', autoCodeSplitting: true }); await plugin.vite.configResolved({ root: 'E:/AI_projects/yeyu-api/frontend' }); console.log('TanStack Router official generator completed');"
```

原始结果：

```text
TanStack Router official generator completed
```

生成后校验 `routeTree.gen.ts` 中的官方输出字符串：

```text
ROUTE_TREE_REQUIRED_ROUTES=present: /, /catalog, /catalog/$slug, /dashboard
```

生成 diff 只包含路由导入、父子关系、类型映射和生成树内容；没有手工修改生成文件。

### TypeScript

命令：

```powershell
pnpm exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json
```

原始结果：失败，7 个现有类型错误。主要包括 `ApiDetailView.tsx` 的 ES2020 `replaceAll`、多个现有 `/catalog` Link 缺少 search 参数，以及由新生成类型暴露的 search 参数约束。错误文件不在本次允许修改范围内，因此没有越界修改。

```text
src/components/ApiCatalog/ApiDetailView.tsx(51,20): error TS2550: Property 'replaceAll' does not exist
src/components/ApiCatalog/ApiDetailView.tsx(127,6): error TS2550: Property 'replaceAll' does not exist
src/components/ApiCatalog/ApiDetailView.tsx(128,24): error TS7006: Parameter 'character' implicitly has an 'any' type.
src/components/ApiCatalog/ApiDetailView.tsx(146,10): error TS2741: Property 'search' is missing
src/components/PublicSite/PublicFooter.tsx(18,12): error TS2741: Property 'search' is missing
src/components/PublicSite/PublicHeader.tsx(21,8): error TS2741: Property 'search' is missing
src/routes/index.tsx(51,10): error TS2741: Property 'search' is missing
```

### Playwright 项目边界清单

公共项目命令：

```powershell
pnpm exec playwright test tests/public-catalog.spec.ts --project=public-chromium --list
```

原始结果：`[public-chromium]` 共 11 个测试，未列出 `[setup]`，证明公共目录项目不依赖认证 setup。

认证项目命令（仅使用非秘密环境占位值读取配置）：

```powershell
pnpm exec playwright test tests/login.spec.ts --project=chromium --list
```

原始结果：列出 `[setup] › auth.setup.ts` 和 `[chromium]` 登录测试，共 12 个测试，证明受保护登录项目仍保留 setup 依赖。

### Playwright 实际尝试

命令：

```powershell
pnpm exec playwright test tests/public-catalog.spec.ts --project=public-chromium
```

原始结果：

```text
Running 11 tests using 10 workers
11 failed
```

该结果无效于 yeyu-api 产品验收：`localhost:5173` 被已有旧项目进程占用，进程命令行为：

```text
E:\Project\KnowTrace\frontend\node_modules\.bin\..\vite\bin\vite.js
```

其 HTTP 200 页面实际返回 `知溯 KnowTrace` 登录页，而不是 Yeyu API。Playwright 错误上下文也显示 `heading "知溯 KnowTrace"`、用户名和密码输入框。未终止、重启或修改该旧项目进程；没有真实 yeyu-api 后端和账号，因此未伪造 Playwright 通过结果。

### Diff 检查

命令：

```powershell
git diff --check
```

原始结果：无 whitespace 错误；仅报告 Windows 工作树的 LF/CRLF 转换提示。

## 未验证风险

- Vite production build 仍受现有 `@swc/core` 原生绑定/DACL 缓存环境问题阻塞。
- TypeScript build 仍有上面列出的既有组件类型错误；解决它们需要修改本次明确禁止修改的组件/配置文件。
- Playwright 需要独立、正确的 yeyu-api 前端进程、后端和真实测试账号；当前运行被旧 KnowTrace 进程污染，未形成有效浏览器验收证据。
- PostgreSQL、SMTP、OAuth、DNS、Nginx 和线上服务未验证，也未被本任务修改。
- `task-7-1-review.md` 现在明确为中止且未批准；后续若需要独立批准，必须另行完成可追溯复审，不能沿用本文件作为 Approved 证据。

## 提交

提交主题：`fix: close final catalog review findings`

提交 SHA 由最终 `git commit` 结果返回。
