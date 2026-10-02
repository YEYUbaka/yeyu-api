## Task 2: Split Public and Protected Route Shells

**Files:**

- Create E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\routes\_layout\dashboard.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicLayout.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicFooter.tsx
- Delete E:\AI_projects\yeyu-api\frontend\src\routes\_layout\index.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\routes\_layout.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\hooks\useAuth.ts
- Modify E:\AI_projects\yeyu-api\frontend\src\routes\login.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\components\Sidebar\AppSidebar.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\components\Common\Logo.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\components\Common\Footer.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\index.css
- Create or modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts
- Modify E:\AI_projects\yeyu-api\frontend\tests\login.spec.ts

### Implementation

- [ ] 先更新 Playwright 断言：匿名访问 / 不跳转 /login；匿名访问 /catalog 不跳转 /login；登录成功后的目标为 /dashboard；受保护的 /items 仍在未登录时跳转 /login。
- [ ] 实现 PublicLayout、PublicHeader、PublicFooter，导航至少包含首页、API 目录、登录；移动端提供可访问的折叠菜单或等价的键盘可用导航；登录状态下显示控制台入口。
- [ ] 将受保护根页面从 _layout/index.tsx 迁移为 _layout/dashboard.tsx，路由标题改为 Yeyu API 控制台，保留当前用户欢迎信息，不把公共首页内容复制到控制台。
- [ ] 将 useAuth 登录成功跳转、GitHub callback 成功跳转和 login.tsx 的已登录重定向统一改为 /dashboard；登录失败、回调失败和登出行为保持现有语义。
- [ ] 将侧边栏 Dashboard 链接改为 /dashboard，避免继续指向公共首页；更新 Logo 和 Footer，移除 FastAPI Template 品牌、链接和文案，替换为 Yeyu API 公益平台信息。
- [ ] 让 E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx 使用 PublicLayout 作为公共首页入口，首页只渲染真实目录数据、搜索入口、公益说明和使用规范入口；数据加载失败时显示明确的错误状态，不伪造接口卡片。
- [ ] 修改 index.css 建立设计变量：纸白背景、墨色正文、青绿色主色、浅青绿色表面、琥珀色警示色和可见焦点环；保留 Tailwind/shadcn 现有组件可用，不引入远程 CSS。
- [ ] 保证公共壳层的 main、导航、按钮、表单控件有语义标签、键盘焦点、可读颜色和移动端溢出处理。

### Verification

- [ ] 执行前端格式与类型构建：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
pnpm build
~~~

- [ ] 执行只覆盖路由边界的 Playwright 测试：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec playwright test tests/public-catalog.spec.ts tests/login.spec.ts
~~~

- [ ] 记录构建、Biome 和 Playwright 的实际结果；没有运行 Docker 依赖时标明具体阻塞。
- [ ] 独立只读子代理检查路由树迁移是否完整、匿名/登录边界、键盘可用性、品牌残留和是否误触及旧项目，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-2-review.md。
- [ ] 处理审查问题后重新构建和运行边界测试，创建提交 feat: split public and protected web shells 并推送 origin/main。

