# Task 7-3 独立只读审查报告

## Spec Compliance

- ✅ 使用 CatalogService、TanStack Router search params 和 400ms 防抖：routes/catalog/index.tsx:21-77。
- ✅ 目录卡片、详情字段、状态组件、占位 API Key、复制反馈和移动端滚动边界均有实现。
- ❌ 示例 URL 不完全符合当前域名/禁止任意 URL 边界：ApiDetailView.tsx:36-47、:68。
- ⚠️ 无法从 diff 验证 build、路由生成、Playwright 完整执行、真实后端响应、1280/390 浏览器验收；报告显示 Playwright 被既有 auth.setup.ts 阻塞。

## Strengths

- 目录数据来自真实 CatalogService，未硬编码候选接口或统计。
- 搜索、分类、状态通过 URL 保存，并保留其他 search 参数。
- 加载、错误、空结果有独立可读状态；详情展示鉴权、参数、响应、错误、缓存、来源和三种示例。
- 代码复制按钮有可访问名称和 aria-live 成功/失败反馈；表格、路径和代码块具备移动端滚动边界。

## Issues

### Critical (Must Fix)

- 无。

### Important (Should Fix)

- E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx:36-47,68：curl/Python 硬编码正式域名且 JavaScript 的 new URL 信任 detail.path；应只接受内部绝对路径并统一使用受控 API 基址。
- E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts:53-65 与 ApiDetailView.tsx:232,316：response_schema 和 cache_rules 任意 metadata 直接 JSON 序列化回显；应增加前端敏感键过滤/脱敏，作为后端 DTO 清洗的防御层。
- E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx:67-80 与 CatalogFilters.tsx:20-21：固定 page=1、page_size=20，无分页且筛选项只来自当前页，目录超过 20 条会静默遗漏；应增加分页 search param 或等价的继续加载。
- E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx:38-42：详情重试失败而 React Query 保留旧 data 时会同时渲染错误和旧详情；应隐藏旧详情或明确标识 stale 状态。
- E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts:84-93,149-157：mock 使用 **/api/v1/catalog* 可能不能可靠匹配带路径的详情请求；应使用正则或分别注册列表与详情精确路由。

### Minor (Nice to Have)

- public-catalog.spec.ts:168-181 的一次性 fill 加 150ms 等待不能完全证明 400ms 防抖；分类/状态只断言 URL，未断言请求参数。
- public-catalog.spec.ts:88-121,184-251 未覆盖加载、错误、重试、详情移动端溢出和 clipboard 内容。

## Assessment

**Task quality:** Needs fixes

**Reasoning:** 主流程和 UI 结构基本符合需求，但示例 URL 信任边界、分页、详情错误状态和 Playwright mock 存在明确风险；build、真实后端和浏览器验收尚未完成。
