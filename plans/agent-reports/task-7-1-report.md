# Task 7-1 交付报告：公共 builtin-tools 目录种子

## Status

DONE_WITH_CONCERNS。实现、任务级 SQLite 测试和 Ruff 已通过；按简报原命令运行时，项目全局 PostgreSQL fixture 因本机认证环境阻塞。代码已提交，未执行线上操作。

## 实现内容

- 新增不可变的 `PUBLIC_CATALOG_SEEDS`，包含 `time` 与 `uuid` 两条公开目录定义。
- 复用 `ApiDefinition` 字段和 builtin-tools 约束：GET、`api_key`、`builtin-tools`、public、published、`/v1/tools/<slug>`、免费。
- time 元数据描述可选 `timezone`（默认 UTC），响应为 `utc`、`unix_timestamp`、`timezone`、`local`；uuid 元数据描述无参数且返回 `uuid`、`version=4`。
- 示例仅使用 `<YOUR_API_KEY>` 占位符；种子不读取环境密钥、不访问网络、不输出日志。
- `seed_public_catalog(session)` 对每个 slug 显式查询，只新增缺失记录；已有记录完全跳过，不覆盖管理员的 `summary`、`status`、`examples`、`cache_rules` 或 `updated_at`。
- `initial_data.init()` 保留原有 `init_db(session)`，并在其后使用同一 session 调用种子函数。

## 文件

- `E:\AI_projects\yeyu-api\backend\app\catalog_seed.py`
- `E:\AI_projects\yeyu-api\backend\app\initial_data.py`
- `E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py`
- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-report.md`
- `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md`

## TDD RED

1. 简报原命令：

   `conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q`

   原始结果：测试收集阶段失败，`Settings()` 缺少 `SECRET_KEY`、`PROJECT_NAME`、`DATABASE_URL`、`FIRST_SUPERUSER`、`FIRST_SUPERUSER_PASSWORD` 五项配置。

2. 在不落盘的测试配置下、隔离项目全局数据库 fixture 的 RED 命令：

   `conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\services`

   原始结果：`ModuleNotFoundError: No module named 'app.catalog_seed'`，4 个测试均未进入断言。

## GREEN

命令：

`conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q --confcutdir=E:\AI_projects\yeyu-api\backend\tests\services`

实际输出：

`....                                                                     [100%]`

`4 passed in 0.79s`

Ruff 命令：

`conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app\catalog_seed.py E:\AI_projects\yeyu-api\backend\app\initial_data.py E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py`

实际输出：`All checks passed!`

## 其他测试

- `test_catalog.py`：`5 passed in 0.68s`。
- `test_execution.py`：`51 passed in 0.26s`。
- `git diff --check`：无 whitespace 错误。

## 阻塞与未解决风险

- 简报原始 pytest 命令会加载 `backend\tests\conftest.py` 的 session 级 PostgreSQL fixture；使用仅限当前进程的非生产测试配置运行时，数据库连接在认证阶段失败，得到 4 个 setup errors，未进入本任务测试。未修改数据库、环境文件或线上服务。
- 独立只读 `codex review --uncommitted` 进程已启动，但按用户要求中止，未返回审查结论；因此 `task-7-1-review.md` 只记录审查未完成，不能把独立审查说成通过。已完成本地 diff、字段契约、敏感数据边界和测试覆盖的自审。
- 尚未做真实 PostgreSQL/生产初始化验收；本任务没有 DNS、Nginx、服务器或线上变更。

## 提交

提交主题：`feat: seed public builtin catalog`

提交 SHA：`feb0136be09b0c3ddaed37af62b40b518f159c40`

## Self-review

- 变更范围仅涉及简报列出的种子、初始化调用、任务测试及交付记录。
- 种子元数据通过递归冻结并在写入模型前复制解冻，避免常量被修改，也避免共享可变 JSON 对象污染数据库记录。
- 重复调用没有更新路径；只有发现缺失记录时才 commit。
- 测试覆盖初次创建、完整公共字段、time/uuid 参数与响应契约、API Key 占位符、深层不可变性、幂等性、管理员编辑保留和初始化调用顺序。
