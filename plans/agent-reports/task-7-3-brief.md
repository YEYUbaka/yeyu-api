## Task 3: Build Search-First Catalog and Detail Pages

**Files:**

- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogSearch.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogFilters.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogCard.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogGrid.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogStates.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx
- Create E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CodeExample.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx
- Modify E:\AI_projects\yeyu-api\frontend\src\index.css
- Modify E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts

### Implementation

- [ ] 在测试中覆盖目录页匿名可访问、搜索参数能反映到 URL、分类筛选能反映到 URL、空结果有明确状态、详情页展示 /v1/tools/time、GET、API Key 鉴权、参数、响应字段和错误码。
- [ ] 目录页通过生成的 CatalogService.getCatalog 和 React Query 获取分页数据，query、category、status 使用 TanStack Router search params 作为唯一可分享状态；输入搜索设置 300 至 500 毫秒防抖并避免逐键请求。
- [ ] 目录页首屏顺序固定为页面标题与搜索框、分类/状态筛选、真实目录卡片；卡片包含名称、中文简介、请求方法、路径、免费标记、健康/发布状态和更新时间，点击后进入 /catalog/:slug。
- [ ] 目录页只展示后端返回数据，不在前端硬编码候选接口；API 返回空、错误和加载状态分别使用可读的 Empty、Error、Skeleton 组件。
- [ ] 详情页通过生成的 CatalogService.getCatalogDetail({ path: { slug } }) 获取数据；展示鉴权说明、参数表、响应结构、错误码、缓存规则、来源标签和 curl、JavaScript、Python 示例。
- [ ] 代码示例只显示 <YOUR_API_KEY>，统一从当前域名拼接请求 URL，不保存或读取真实 API Key，不提供任意 URL 输入；复制按钮使用可访问名称并在成功后有非颜色反馈。
- [ ] 首页保持索引台视觉：上方以一句清晰定位和主搜索入口为主，下面展示由真实目录 API 返回的精选工具卡片、一个可直接跳转的 Quick Start 区块和公益/使用边界说明；不展示假统计。
- [ ] 公共导航在首页、目录页和详情页保持一致；目录页搜索框支持从首页带 query 参数跳转后继续搜索。
- [ ] 移动端将详情页的参数表、代码块和路径行处理为可横向滚动而不撑破页面；桌面端使用窄内容列、明显分隔线和稳定状态色。

### Verification

- [ ] 执行前端构建与静态检查：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec biome check --no-errors-on-unmatched --files-ignore-unknown=true src tests
pnpm build
~~~

- [ ] 在项目 Docker Compose 测试环境可用时执行：

~~~powershell
Set-Location -LiteralPath 'E:\AI_projects\yeyu-api\frontend'
pnpm exec playwright test tests/public-catalog.spec.ts
~~~

- [ ] 通过 API 测试确认种子后端实际提供目录数据：

~~~powershell
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\api\routes\test_catalog.py E:\AI_projects\yeyu-api\backend\tests\api\routes\test_public_api.py -q
~~~

- [ ] 使用真实浏览器尺寸至少检查 1280 像素桌面视口和 390 像素移动视口；记录页面 URL、公开/受保护结果、控制台错误和截图路径。截图若用于审查，只放在项目外部临时目录。
- [ ] 独立只读子代理检查 API client 使用、URL 状态同步、错误/空状态、示例密钥脱敏、移动端溢出、可访问性和视觉方案偏离，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-review.md。
- [ ] 处理审查问题后重跑构建、API 测试和浏览器测试，创建提交 feat: add public catalog and api detail pages 并推送 origin/main。

