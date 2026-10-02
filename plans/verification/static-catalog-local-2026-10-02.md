# 静态 API 资料册本地验证证据

验证日期：2026-10-02（Asia/Hong_Kong）  
项目：`E:\AI_projects\yeyu-api`  
最终提交：`ab8f043a6197926346fdd8bc4ce6e54ce632567f`  
远程分支：`origin/main`

## 验证范围

本记录只证明本地静态资料册的目录校验、构建、浏览器行为和可追溯打包。没有执行服务器、DNS、证书、Nginx、远程上传或线上验收，也没有证明动态 FastAPI 平台已经完成。

## 命令与结果

1. 目录数据校验：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend run validate:static-catalog
   Static catalog validation passed: 6 entries
   ```

   校验包含必填字段、HTTPS 来源、状态枚举、ownership 与 redistributionMode 边界、日期、重复 slug、敏感字段和值模式。

2. TypeScript：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend exec tsc -p E:\AI_projects\yeyu-api\frontend\tsconfig.build.json --noEmit
   exit code 0
   ```

3. Biome：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend exec biome check ...
   Checked 11 files in 12ms. No fixes applied.
   ```

4. 静态构建：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend run build:static-catalog
   ✓ 20 modules transformed.
   ✓ built in 282ms
   ```

   `E:\AI_projects\yeyu-api\deploy\static-catalog\build-meta.json` 记录：

   ```json
   {
     "project": "yeyu-api",
     "commit": "ab8f043a6197926346fdd8bc4ce6e54ce632567f",
     "workingTreeClean": true
   }
   ```

5. Playwright：

   ```text
   pnpm --dir E:\AI_projects\yeyu-api\frontend exec playwright test --config=E:\AI_projects\yeyu-api\frontend\playwright.static.config.ts
   Running 12 tests using 10 workers
   12 passed (5.0s)
   ```

   覆盖桌面和 Pixel 5：首屏资料、搜索、空结果、分类筛选、官方文档 href、搜索/分类交互后的严格同源 origin、窄屏可用性。官方链接只断言 href，没有自动点击公网地址。

6. 发布包：

   ```text
   E:\AI_projects\yeyu-api\deploy\scripts\package-static-catalog.ps1
   Static catalog package created: ...\static-catalog-ab8f043a6197926346fdd8bc4ce6e54ce632567f.zip
   Manifest created: ...\static-catalog-ab8f043a6197926346fdd8bc4ce6e54ce632567f.manifest.json
   ```

   manifest 中的 commit 与 build metadata、当前 HEAD 一致；包内文件为 `index.html`、JS、CSS 和 `build-meta.json`。旧 commit 产物曾被门禁拒绝，原因是“静态产物 commit 与当前 HEAD 不一致”。

## 未验证和后续门禁

- SMTP、GitHub OAuth、PostgreSQL、Redis、动态 API Key、限流和管理端仍未完成本地完整验收。
- 静态站正式发布前必须重新只读检查服务器、DNS、TLS、80/443 和现有 Nginx，并等待用户确认后才允许上传或改配置。
- 正式上线后的 HTTPS、移动端、旧站和 `new.api.yeyubaka.top` 不受本地证据覆盖，不能据此宣称线上通过。
