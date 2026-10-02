# Task 7 类型检查收口修复计划

## 目标

修复当前官方路由树生成后 `pnpm exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json` 暴露的 7 个类型错误，不改变业务边界或生成文件。

## 允许修改范围

- `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`
- `E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicFooter.tsx`
- `E:\AI_projects\yeyu-api\frontend\src\components\PublicSite\PublicHeader.tsx`
- `E:\AI_projects\yeyu-api\frontend\src\routes\index.tsx`
- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-final-fix-report.md`

## 要求

- 用目标库兼容的正则替换替代 `replaceAll`，保留原有输出语义并保持回调参数类型安全。
- 所有指向 `/catalog` 的 TanStack Router Link 提供合法的默认 search（至少包含 `page: 1`），不手工编辑 `routeTree.gen.ts`。
- 先运行 TypeScript 和 Biome，再把真实结果追加到报告；不得写入凭据或运行线上操作。
