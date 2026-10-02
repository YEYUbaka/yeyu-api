## Task 1: Add Idempotent Public Catalog Seeds

**Files:**

- Create E:\AI_projects\yeyu-api\backend\app\catalog_seed.py
- Modify E:\AI_projects\yeyu-api\backend\app\initial_data.py
- Create E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py

### Implementation

- [ ] 在测试中构造 SQLite 或项目现有测试 session，验证初次调用 seed_public_catalog(session) 会创建且只创建 time、uuid 两条 ApiDefinition。
- [ ] 在测试中验证两次调用结果完全幂等，第二次不增加记录、不重置 updated_at、不覆盖管理员已经修改的 summary、status、examples 或 cache_rules。
- [ ] 在测试中验证种子数据的 adapter_name 只能是 builtin-tools，visibility 为 public，status 为 published 或 healthy，auth_type 为 api_key，is_free 为真，路径分别为 /v1/tools/time 与 /v1/tools/uuid。
- [ ] 在测试中验证示例请求不包含真实密钥，示例只出现 <YOUR_API_KEY> 占位符；验证 time 具有可选 timezone 参数，uuid 不允许参数。
- [ ] 在 catalog_seed.py 暴露不可变的 PUBLIC_CATALOG_SEEDS 和 seed_public_catalog(session)，使用显式 slug 查询缺失记录后新增，不调用会覆盖已有字段的批量 upsert。
- [ ] 为 time 和 uuid 填写面向开发者的中文 name、summary、category、method、path、parameters、response_schema、error_codes、examples、source_label、cache_rules；元数据必须与实际 builtin adapter 返回值一致。
- [ ] 在 initial_data.init() 的现有 init_db(session) 之后调用 seed_public_catalog(session)，保留原有超级用户初始化行为。
- [ ] 不在种子文件中读取环境变量中的密钥，不调用第三方网络，不写日志中的敏感信息。

### Verification

- [ ] 使用项目 conda 环境 yeyu-api 执行：

~~~powershell
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py -q
~~~

- [ ] 使用项目 conda 环境执行：

~~~powershell
conda run -n yeyu-api python -m ruff check E:\AI_projects\yeyu-api\backend\app\catalog_seed.py E:\AI_projects\yeyu-api\backend\app\initial_data.py E:\AI_projects\yeyu-api\backend\tests\services\test_catalog_seed.py
~~~

- [ ] 记录 pytest 和 ruff 的真实输出；若数据库依赖导致环境阻塞，只记录阻塞原因，不将未运行结果标为通过。
- [ ] 独立只读子代理检查种子幂等性、适配器字段一致性、敏感数据边界和测试充分性，报告写入 E:\AI_projects\yeyu-api\plans\agent-reports\task-7-1-review.md。
- [ ] 处理审查报告中的 Critical 或 Important 问题后重新运行上述测试，再创建提交 feat: seed public builtin catalog 并推送 origin/main。

