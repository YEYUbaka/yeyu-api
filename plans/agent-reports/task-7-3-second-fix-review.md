# Task 7-3 第二次修复复审

## 复审范围

- 基线：`04fcbd4`
- 当前修复：`9c901eb`
- Diff：`E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-second-fix-diff.md`
- 复审方式：独立只读子代理；未修改文件、未提交、未推送。

## 结论

**Approved：否。** 无 Critical，但上一轮两个 Important 均未完全关闭。

## Important

1. **代码示例仍可能泄露敏感 query 参数值。**

   `normalizeSafeQueryKey` 只校验格式，没有拒绝 `apiKey`、`access_token`、`client_secret` 等参数名；值过滤也只能识别关键词、JWT 和特殊字符。类似 `apiKey=1234567890` 仍可能进入三种示例。

   相关位置：

   - `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
   - `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`

2. **facets 仍不能保证完整目录。**

   当前最多请求 100 页，即最多约 10,000 条；达到上限时静默返回部分数据，没有 incomplete/error 信号。测试的 `count=101` 每页只返回 1 条，实际会继续请求到上限，但只断言请求过第 2 页，且没有证明后续页的分类/状态 facet 真正生效。

   相关位置：

   - `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`
   - `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`

## Minor

- facets 请求失败时仍展示完整 `CatalogErrorState`，同时主目录结果可能正常显示，错误语义容易与“目录加载失败”混淆。
- URL 同步链路和当前代码中的明显 TypeScript 错误未见新问题；本次未运行 Playwright、build 或 `tsc`。

## Task gate

Task 7-3 暂不通过，必须修复上述 Important 后重新运行覆盖测试并进行新鲜只读复审。
