# Task 7-3 第二次复审问题修复计划

## 目标

修复 `9c901eb` 之后独立复审发现的两个 Important，并保留真实验证边界：

1. 代码示例不得从目录参数中带出敏感查询字段（包括 `apiKey`、`access_token`、`client_secret` 等），同时继续只使用固定 API Key 请求头和安全参数值。
2. facets 不能在达到分页上限后静默伪装成完整目录；必须显式表达未完整加载，或采用可证明完整的停止条件，并补测试证明后续分页中的分类/状态进入筛选选项。

## 允许修改范围

- `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
- `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`
- `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`
- `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`
- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-report.md`

禁止修改生成路由树、认证/公共壳层、后端、服务器、DNS、Nginx、旧项目和任何凭据。

## 实施与验证要求

- 先补充或改写针对敏感参数名、完整 facets 分页和截断/错误状态的回归断言，再实现最小修复。
- 不得用静默截断作为“完整目录”；若保留客户端分页抓取，必须在达到上限时返回明确的不完整状态并避免将未加载值当成已知 facet。
- 运行针对变更文件的 Biome 和 `git diff --check`，在报告中记录命令与真实结果。
- 不运行或声称通过长时间 Playwright、构建、后端集成、路由生成或线上验收；如额外运行必须记录实际结果。
- 修复完成后创建清晰提交，并等待新的独立只读复审。
