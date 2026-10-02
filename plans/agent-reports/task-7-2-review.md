# Task 7-2 独立只读审查报告

## Spec Compliance

- ❌ 构建链阻塞：routeTree.gen.ts:17,46-50,67-75,209-224 仍引用已删除的 _layout/index，缺少新的 / 与 /dashboard；pnpm build 在 Vite 生成前的 tsc 阶段退出 2。此缺陷属于本任务应修复范围，但应修复生成顺序，不得手改生成文件。
- ✅ 源文件路由无冲突：公共 routes/index.tsx 与 pathless _layout 平级，_layout/dashboard.tsx 仍受认证布局保护。
- ✅ 登录成功、GitHub callback、已登录 /login 和 Sidebar Dashboard 的静态跳转均统一为 /dashboard。
- ✅ 首页使用真实 CatalogService.searchCatalog，有加载/错误/空结果状态，无虚假统计、任意上游 URL 或真实密钥。
- ⚠️ 无法从 diff 确认浏览器运行时、GitHub OAuth callback、/catalog 是否存在真实公共路由、目录 API 是否确实免认证，以及全仓库 FastAPI 品牌残留。

## Strengths

- 公共壳层使用 header、nav、main、footer、可见焦点环和移动菜单 ARIA 属性。
- 受保护首页已迁移为 dashboard，认证 beforeLoad 保留。
- 示例凭据仅为 <YOUR_API_KEY>；未发现线上资源、旧项目或凭据改动。

## Issues

### Critical (Must Fix)

- E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts:17,46-50,67-75,209-224：生成树引用已删除文件并保留旧受保护根路由，新的 /、/dashboard 类型不存在；pnpm build 在 Vite 生成前失败，当前提交不可交付。修复生成顺序或通过官方生成链刷新并提交生成结果，不得手工编辑 routeTree.gen.ts。

### Important (Should Fix)

- E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts:89-99：测试仍等待 / 并查找已删除的旧欢迎文案；构建修复后会超时，登出及 /settings 保护断言不会执行。应改为等待 /dashboard 并断言新的 dashboard 标题。
- E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts:18-24 与 E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx:61-63,134-151：/catalog 测试只断言不在 /login，404 或空路由也能通过；应断言最终 URL 保持 /catalog，并断言公共壳层。若目录页延后至任务 3，应同步延后该测试和入口验收。
- E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts:27-39：测试仅调用 focus，没有实际操作移动菜单或验证 aria-expanded；应使用键盘 Enter/Space 操作菜单按钮并断言展开、收起和链接可访问性。

### Minor (Nice to Have)

- 无。

## Assessment

**Task quality:** Needs fixes

**Reasoning:** 源码路由拆分和认证跳转方向正确，但生成路由树与构建顺序造成当前交付阻塞，且已有登录测试落后于新路由。
