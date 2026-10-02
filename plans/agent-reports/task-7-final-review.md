# Task 7 公共首页/目录阶段整体验收复审

## 复审范围

- 基线：`068092d`
- 当前提交：`d56e495`
- Diff：`E:\AI_projects\yeyu-api\plans\agent-reports\task-7-final-diff.md`
- 方式：独立只读总审查；复审员未修改文件、未提交、未推送。

## Strengths

- 公共 `/`、`/catalog`、`/catalog/:slug` 与受保护 `_layout` 源路由边界清晰，认证门禁仍保留。
- 后端目录只公开 `visibility=public` 且状态为 `healthy/published` 的记录；未发现任意上游代理、旧项目路径或真实密钥。
- 种子数据不可变、幂等，固定使用 `builtin-tools`；示例使用 `<YOUR_API_KEY>`。
- 目录分页、URL 状态、facet 截断提示、错误/空/加载状态和移动端滚动边界均有实现。
- 代码示例固定 `X-API-Key` 和正式 API 基址，并对路径、参数名和值及 metadata 做防御性过滤。
- 阶段计划如实把 build、Playwright、后端运行时和真实浏览器验收标为未验证。

## Critical

### 生成路由树与源代码不一致

- 文件：`E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts`
- 影响：仍导入已删除的 `_layout/index`，缺少新的公共 `/`、`/catalog`、详情页和受保护 `/dashboard`；在官方生成链未成功执行时无法可靠构建或运行。
- 要求：使用 TanStack Router 官方生成链刷新生成文件，禁止手工编辑；随后验证生成、类型检查和构建。

## Important

1. `E:\AI_projects\yeyu-api\frontend\tests\auth.setup.ts` 仍等待旧的 `/`，而登录已跳转 `/dashboard`；Playwright Chromium 项目强制依赖该 setup，公共测试无法独立运行。需要更新等待目标，并让匿名公共测试使用不依赖认证 setup 的独立项目。
2. `E:\AI_projects\yeyu-api\backend\app\services\catalog.py` 的搜索只匹配 slug、name、summary，没有匹配 path；UI 文案承诺路径搜索，因此搜索 `/v1/tools/time` 会漏掉真实条目。需要加入 path 匹配并补真实后端 API 测试。
3. 当前目录测试主要由 route mock 驱动，阶段报告记录 Playwright、完整 build、真实后端分页/脱敏和浏览器尺寸验收未完成，不能证明真实目录 API 和运行时路由集成可用。需要在上述修复后补跑对应验证。
4. `task-7-1-report.md` 写明独立审查中止、不能称为通过，但 `task-7-1-review.md` 却标为 Approved。需要更正报告或补一份可追溯的独立审查，不能保留矛盾证据。

## Minor

- facets 加载失败或尚未完成时会回退到当前页数据，并复用通用目录错误提示；主结果可能正常但筛选项不完整，错误语义不够精确。
- 受保护和认证页面仍有部分 FastAPI Template 标题残留，暂不阻塞公共目录阶段。

## 结论

**Ready to merge: No（With fixes）。**

公共目录静态实现和安全边界整体扎实，但生成路由树是 Critical 交付阻塞；认证 E2E setup、路径搜索和独立运行时证据仍有 Important 问题。Task 4 暂不通过。
