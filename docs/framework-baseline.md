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
- [ ] Python、pnpm 依赖锁定文件尚未生成。

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

本文件将在导入、依赖锁定和基线验证后补充最终状态、实际命令输出摘要、未验证项与 concerns。健康检查、构建成功不等同于产品验收；Docker 不可用时必须单独标记为未验证。
