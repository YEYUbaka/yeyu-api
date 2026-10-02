# Yeyu API 收集目录

这是一个面向学生和个人开发者的静态免费 API 收集目录，负责整理 API 来源、官方文档、免费说明和使用边界。

页面只做本地搜索、分类筛选和官方链接跳转，不提供 API 调用、登录、API Key、代理、数据库、缓存或在线调试。

当前范围说明见 [`docs/2026-10-02-static-api-directory-scope.md`](./docs/2026-10-02-static-api-directory-scope.md)，实施计划见 [`plans/static-api-directory-only.md`](./plans/static-api-directory-only.md)。

## 当前技术栈

- React、TypeScript、Vite、pnpm；
- 编译期 JSON 资料目录；
- 浏览器端本地搜索和分类筛选；
- Playwright 桌面/移动端静态验收；
- 静态构建包和带 commit 的发布元数据。

仓库中保留的 FastAPI、数据库、Redis、Compose 和登录代码属于历史实验范围，不参与当前默认构建和静态发布。

## 本地验证

使用项目独立的 conda 环境和 pnpm 入口，不使用 conda base 或 Windows Store Python。当前静态目录不需要 Python 运行时。

```powershell
pnpm --dir E:\AI_projects\yeyu-api\frontend run validate:static-catalog
pnpm --dir E:\AI_projects\yeyu-api\frontend run build
pnpm --dir E:\AI_projects\yeyu-api\frontend test
```

默认 `build`、`test` 和 `preview` 只针对静态目录。历史动态平台如需单独研究，使用带 `:legacy` 后缀的脚本，并不得用于 `api.yeyubaka.top` 静态发布。

## 前端开发

前端目录说明见 [`frontend/README.md`](./frontend/README.md)。静态入口是 `frontend/static-catalog.html`，资料数据是 `frontend/src/staticCatalog/data.json`。

## 发布边界

当前只生成本地静态产物。未来正式发布前，必须单独确认 DNS、证书、服务器权限和 `api.yeyubaka.top` 专用 Nginx vhost；不得覆盖旧个人网站、`new.api.yeyubaka.top` 或其他服务。

第三方 API 的许可、免费额度和使用规则以各自官方页面为准；目录本身不代表再分发授权。
