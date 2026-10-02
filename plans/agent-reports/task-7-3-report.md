# Task 3：公共目录与 API 详情页实现报告

日期：2026-10-02
项目：`E:\AI_projects\yeyu-api`
实现提交：待提交（代码提交后回填）

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
$env:FIRST_SUPERUSER='playwright@example.invalid'; $env:FIRST_SUPERUSER_PASSWORD='Playwright-Only-Password-123!'; pnpm exec playwright test tests/public-catalog.spec.ts
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

提交 SHA：待提交后回填。
