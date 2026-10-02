# 静态 API 资料册发布说明

这份发布单元只包含编译后的静态 HTML、JavaScript、CSS 和资源文件。它用于整理公开免费 API 资料，不提供 API 代理、账号、API Key、登录、OAuth、SMTP、数据库或缓存服务。

## 本地生成

在项目根目录执行：

```powershell
pnpm --dir E:\AI_projects\yeyu-api\frontend run validate:static-catalog
$env:SWC_NATIVE_BINDING_CACHE = 'C:\Users\21239\swc-native-cache'
pnpm --dir E:\AI_projects\yeyu-api\frontend run build:static-catalog
pnpm --dir E:\AI_projects\yeyu-api\frontend exec playwright test --config=E:\AI_projects\yeyu-api\frontend\playwright.static.config.ts
```

构建产物位于 `E:\AI_projects\yeyu-api\deploy\static-catalog\`，入口为 `index.html`，另有不参与页面请求的 `build-meta.json` provenance 文件。该目录由 Git 忽略，不应直接提交；需要交付时必须在 clean commit 上重新构建，再使用 `E:\AI_projects\yeyu-api\deploy\scripts\package-static-catalog.ps1` 生成带 commit 标识的压缩包和文件清单。脚本会拒绝旧产物、脏工作树和 commit 不匹配的产物。

## 目录边界

- 只展示 `E:\AI_projects\yeyu-api\frontend\src\staticCatalog\data.json` 中有来源、官方文档、协议/再分发判断和核验日期的条目。
- `reference-only` 和 `link-only` 只表示资料或官方链接，不代表 Yeyu 获得了代理、缓存或再分发许可。
- 页面初始加载不请求本项目后端或第三方上游；官方链接只在用户主动点击时离开本站。
- 不得把 `.env`、私钥、OAuth Secret、SMTP 密码、API Key 或服务器配置复制到发布目录。

## 服务器发布设计（尚未执行）

目标是单独使用 `/opt/yeyu-api-static/releases/<commit-sha>/` 和 `current` 指针，不使用 `/www/wwwroot/yeyubaka.top`、`new.api.yeyubaka.top` 或动态 API 容器。Nginx 示例在 `E:\AI_projects\yeyu-api\deploy\nginx\api.yeyubaka.top.static.conf.example`，仅供获批后的只读审查和配置准备使用。

DNS、证书、Nginx、服务器目录和发布账号变更必须先单独说明影响文件、验证命令和回滚步骤，并等待用户确认。本目录当前没有执行任何线上变更。
