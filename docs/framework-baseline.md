# Yeyu API 框架基线

## Task 1 初始失败检查（导入前）

记录时间：2026-09-30

本检查在模板导入前执行，用于确认基线缺失条件；初始状态为 `RED`。

- [x] 模板仓库引用可解析：`https://github.com/fastapi/full-stack-fastapi-template.git`
- [x] 模板 `master` 在本次检查解析为固定 commit：`cb740b656d7a0a6c5e12c7bf8e50343ec94ee9c7`
- [x] 项目外暂存目录：`E:\AI_projects\yeyu-api-template-staging`
- [x] 暂存仓库 HEAD 应与上述 commit 一致（导入前检查已通过）。
- [ ] `E:\AI_projects\yeyu-api\backend\pyproject.toml` 尚未存在。
- [ ] `E:\AI_projects\yeyu-api\backend\tests` 尚未存在。
- [ ] `E:\AI_projects\yeyu-api\frontend` 尚未存在。
- [ ] `E:\AI_projects\yeyu-api\compose.yml` 尚未存在。
- [ ] `E:\AI_projects\yeyu-api\uv.lock` 尚未存在。
- [x] Python `uv.lock` 已保留；由同一模板 SHA 导出的 runtime/dev hash lock 已生成。

## 固定来源与约束

- 官方模板仓库：`https://github.com/fastapi/full-stack-fastapi-template.git`
- 本次导入 commit：`cb740b656d7a0a6c5e12c7bf8e50343ec94ee9c7`
- 模板许可证：MIT（来源：模板根目录 `LICENSE`）。
- Python 约束：`backend\pyproject.toml` 的 `requires-python = ">=3.14,<4.0"`。
- 模板关键路径：`compose.yml`、`backend\`、`frontend\`、`backend\tests\`。
- 本项目使用独立 conda 环境 `yeyu-api`；Python 命令入口必须是 `conda run -n yeyu-api ...`。
- 前端包管理迁移为 pnpm，版本固定为 `pnpm@10.28.2`，Node 版本固定为 `24.18.0`。

## 导入边界

- 保留本项目已有的 `AGENTS.md`、`docs\2026-09-30-yeyu-api-platform-design.md`、`plans\` 和 `.gitignore`。
- 不导入模板 `.git`、任意真实 `.env`、`bun.lock` 或临时构建产物。
- 模板示例 `Item` 仅作为官方骨架的初始代码随模板导入；Yeyu API 后续业务不复用其示例领域语义，Task 1 不处理业务替换。

## 完成状态

记录时间：2026-09-30（Task 1 修复轮次）

- [x] 模板代码已按固定 SHA 导入；项目已有 `AGENTS.md`、设计文档、`plans`、`.gitignore` 未覆盖。
- [x] `frontend\pnpm-lock.yaml` 已使用 pnpm `10.28.2` 生成；Node 版本固定为 `24.18.0`。
- [x] Dockerfile、Playwright、根/前端脚本、pre-commit、CI 和开发文档已迁移为 pnpm 入口；baseline CI push 分支统一为 `main`。
- [x] 新导入但不属于 Task 1 的 FastAPI Cloud、自托管 runner、发布/项目自动化和模板截图资产已删除；React Email 源文件保留。
- [x] `pnpm --version` 输出 `10.28.2`；`node --version` 输出 `v24.18.0`；前端 `pnpm install` 退出码为 0。
- [x] 前端 `pnpm exec playwright --version` 退出码为 0，输出 `Version 1.62.1`。
- [ ] 前端 `pnpm run build` 已执行但退出码为 1：本机 `@swc/core` 原生绑定加载失败并报告 Windows SWC 缓存 DACL 校验错误，不能记为通过。
- [ ] conda 环境 `yeyu-api` 可启动 Python `3.14.7`，但 `conda run --no-capture-output -n yeyu-api python -m pytest --version` 退出码为 1（`No module named pytest`）；本轮按用户要求未继续安装或等待，因此 pytest 未运行。
- [ ] Docker Compose 未验证：本机 Docker 不可用；未安装 Docker、未触碰服务器或线上服务。

健康检查、构建成功不等同于产品验收；上述未验证项必须在依赖安装和 Docker 可用后单独复核。
