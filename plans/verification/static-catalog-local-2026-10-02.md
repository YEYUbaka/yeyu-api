# 静态 API 收集目录本地验证证据

验证日期：2026-10-02（Asia/Hong_Kong）
项目：`E:\AI_projects\yeyu-api`
验证与打包对应的 clean HEAD：`c17cfc276a75ad10b8db47a2f6ed11e503606869`
远程分支：`origin/main`

## 验证范围

本记录只证明本地静态 API 收集目录的范围校验、构建、浏览器行为和可追溯打包。页面只做本地搜索/筛选和官方链接展示，不执行 API 调用。没有执行服务器、DNS、证书、Nginx、远程上传或线上验收；历史动态平台不属于当前交付范围。

## 命令与结果

1. 目录数据校验：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend run validate:static-catalog
   Static catalog validation passed: 6 entries
   ```

   校验包含必填字段、HTTPS 来源、第三方 ownership、资料/链接状态、日期、重复 slug、敏感字段和值模式；当前校验器拒绝 Yeyu 自营条目。

2. TypeScript：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json --noEmit
   exit code 0
   ```

3. Biome：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend exec biome check ...
   Checked 9 files in 20ms. No fixes applied.
   ```

4. 静态构建：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend run build:static-catalog
   ✓ 20 modules transformed.
   ✓ build succeeded
   ```

   `E:\AI_projects\yeyu-api\deploy\static-catalog\build-meta.json` 记录：

   ```json
   {
     "project": "yeyu-api",
      "commit": "c17cfc276a75ad10b8db47a2f6ed11e503606869",
     "workingTreeClean": true
   }
   ```

5. Playwright：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend exec playwright test --config=E:\AI_projects\yeyu-api\frontend\playwright.static.config.ts
   Running 12 tests using 10 workers
   12 passed (4.8s)
   ```

   覆盖桌面和 Pixel 5：首屏资料、搜索、空结果、分类筛选、官方文档 href、搜索/分类交互后的严格同源 origin、窄屏可用性。官方链接只断言 href，没有自动点击公网地址。

6. 发布包：

   ```text
   E:\AI_projects\yeyu-api\deploy\scripts\package-static-catalog.ps1
   Static catalog package created: ...\static-catalog-c17cfc276a75ad10b8db47a2f6ed11e503606869.zip
   Manifest created: ...\static-catalog-c17cfc276a75ad10b8db47a2f6ed11e503606869.manifest.json
   ```

   manifest 中的 commit 与 build metadata、当前 HEAD 一致；包内文件为 `index.html`、JS、CSS 和 `build-meta.json`。包内没有 Secret、后端、数据库、缓存或动态 API 资源。

7. 独立范围审查：

   `E:\AI_projects\yeyu-api\plans\agent-reports\static-api-directory-scope-review.md` 记录了 Peirce 的只读审查。审查确认静态入口符合纯资料收集边界，同时发现并推动修正了默认动态构建、默认测试和 CI 残留；动态流程现仅手动保留为历史检查。

## 未验证和后续门禁

- SMTP、GitHub OAuth、PostgreSQL、Redis、动态 API Key、限流和管理端不属于当前静态目录交付范围；仓库中的历史动态代码未作为本产品发布或验收。
- 静态站正式发布前必须重新只读检查服务器、DNS、TLS、80/443 和现有 Nginx；本次复检证据见 `E:\AI_projects\yeyu-api\plans\verification\server-preflight-2026-10-03.md`，仍需等待用户确认后才允许上传或改 Nginx。
- 正式上线后的 HTTPS、移动端、旧站和 `new.api.yeyubaka.top` 不受本地证据覆盖，不能据此宣称线上通过。
