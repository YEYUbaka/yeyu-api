# Task 7 整体验收复审问题修复计划

## 目标

关闭 `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-final-review.md` 中的 Critical 和 Important，并保留未验证边界。

## 必须处理

1. 用 TanStack Router 官方生成链刷新 `E:\AI_projects\yeyu-api\frontend\src\routeTree.gen.ts`，不得手工编辑；确保公共首页、目录、详情和受保护 dashboard 都在生成树中。
2. 更新 Playwright 登录 setup 的成功目标为当前 dashboard 路由，并让匿名公共目录测试不依赖认证 setup；保持受保护测试仍有认证覆盖。
3. 后端目录搜索同时匹配 `ApiDefinition.path`，补充覆盖路径搜索的后端测试。
4. 更正 Task 1 的矛盾审查证据：不得把中止的复审写成 Approved；保留真实状态，或补一份有明确范围和结果的独立复审。

## 验证与边界

- 代码修改前先补失败或回归测试；至少运行受影响的静态检查和后端测试。
- 前端优先运行官方路由生成命令，再运行 TypeScript/build；如果仍被 SWC 或环境阻塞，必须记录原始阻塞，不得声称通过。
- Playwright 至少分别验证 auth setup 和不依赖认证的公共目录项目；没有真实账号/后端时不得伪造通过。
- 不触碰 `E:\AI_projects\yeyubakahome_Web`、`new.api.yeyubaka.top`、DNS、Nginx、服务器或任何真实凭据。
- 修复后写入 `plans\agent-reports\task-7-final-fix-report.md`，创建清晰提交并再次执行独立总审查。
