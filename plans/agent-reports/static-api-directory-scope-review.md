# 静态 API 收集目录范围只读审查

审查日期：2026-10-02（Asia/Hong_Kong）

审查代理：Peirce（agent `01a0fd00-22e4-7ec0-886f-959859d15187`）

审查方式：独立只读检查；未修改文件、未提交、未推送，未运行会写入项目的命令。

## 结论

静态入口本身符合“资料收集目录”：数据来自本地 `data.json`，页面只做本地搜索和分类筛选，没有登录、API Key、在线调用或代理请求；6 条目录记录均为第三方资料。

审查同时发现，仓库仍保留历史动态平台代码、Compose、旧前端和默认动态 CI。若不收紧默认入口，未来容易误把动态平台当作当前产品发布。因此本阶段将默认构建、默认测试、GitHub Actions 和根测试脚本切换为静态目录；动态流程保留为明确的 `legacy/manual` 历史检查，不进入静态发布门禁。

## 发现与处理

| 严重度 | 证据 | 处理 |
| --- | --- | --- |
| 高 | `backend\app\api\routes\login.py`、`api_keys.py`、`public_api.py`、`compose.yml` | 保留为历史代码，不进入静态入口；`frontend\package.json` 默认 build/test/preview 改为静态脚本 |
| 高 | `.github\workflows\playwright.yml`、`test-backend.yml`、`test-docker-compose.yml` | Playwright 工作流改为静态目录门禁；动态后端和 Docker 工作流仅保留手动触发 |
| 高 | `frontend\src\routes\index.tsx`、`login.tsx`、`dashboard.tsx` | 不参与静态 Vite 入口；README 和范围文档明确为历史实验 |
| 中 | `README.md`、历史设计/契约文档 | README 改为静态目录说明；历史文档顶部增加“不作为当前实施依据”标记 |
| 中 | `deploy\nginx\api.yeyubaka.top.static.conf.example` 的 `/health` 示例 | 暂未修改；后续发布前应改成明确的静态存活说明或移除，避免被理解为动态服务健康状态 |

## 当前确认没有的问题

- `frontend\src\staticCatalog\data.json` 没有 Yeyu 自营条目或 Yeyu API Key；6 条均为 `third-party`。
- 静态数据没有宣称无限免费、已获再分发授权或真实健康状态；额度、条款和可用性均提示回官方核验。
- 静态发布脚本只写入 `E:\AI_projects\yeyu-api\deploy\...`；未发现对旧项目、旧域名或旧站目录的运行时写入依赖。

## 未完成事项

- 需要在 clean commit 上重新生成静态构建和发布包；dirty 工作树时发布脚本应继续拒绝。
- 服务器、DNS、TLS、Nginx 和线上验收仍未执行。
