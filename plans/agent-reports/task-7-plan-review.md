# Task 7 计划独立审查报告

- 审查方式：独立子代理只读核对
- 审查范围：E:\AI_projects\yeyu-api\plans\task-7-admin-health-audit.md 与当前后端关键文件
- 审查代理：Helmholtz（只读，未修改文件）
- 总评：Needs changes

## Critical

### 1. 试验池存在演变为任意 URL 代理的风险

审查指出，E:\AI_projects\yeyu-api\backend\app\models.py 中 ApiDefinition.path、adapter_name、provider_ref、status 的模型约束不足，现有 E:\AI_projects\yeyu-api\backend\app\api\routes\admin_catalog.py 的 mutation payload 也不能单独证明固定执行边界。

修订要求：

- 使用固定 adapter/provider 注册表作为唯一可持久化和可执行集合；
- 拒绝包含 URL、host、协议或开放代理语义的 provider/path 值；
- 对 status、path、adapter_name、provider_ref 增加 schema/服务层和必要的数据库约束；
- 增加测试证明 status=trial 搭配 https://...、外部 host 或未知 adapter 不能持久化，也不能执行；
- 管理端只展示内部 provider 引用，不提供任意 URL 输入。

## Important

### 2. 健康检查必须先于前端 catch-all 注册

E:\AI_projects\yeyu-api\backend\app\main.py 当前在 API router 后挂载前端目录。计划必须明确：

- 根路径 /health、/ready 在前端静态挂载前注册；
- 只有 FRONTEND_DIR.is_dir() 才挂载前端，避免无构建产物时后端 collection 失败；
- RedisStore 增加安全、可替换的 ping() 抽象；
- /ready 只返回固定状态字段，不返回连接字符串、异常文本、版本表细节或 Secret。

### 3. 审计和业务 mutation 必须共用一个事务

不能让 AuditService.record() 自己独立提交后再提交业务 mutation，也不能业务已提交后才发现审计写失败。应改为：

- AuditService.record() 只向传入的 Session add()，不自行 commit()；
- 业务 mutation 与 AuditEvent 共用同一个 Session/事务；
- route/service 的唯一提交点统一执行 commit()，异常统一 rollback；
- 审计失败时业务 mutation 一并失败关闭并返回安全错误；
- 增加测试证明不会出现业务成功而审计缺失的静默状态。

### 4. 新增管理路由必须完整复用 superuser 保护

现有 E:\AI_projects\yeyu-api\backend\app\api\routes\admin_catalog.py 与 E:\AI_projects\yeyu-api\backend\app\api\deps.py 的保护目前有效。新增 catalog list、audit list、admin health 以及前端调用的管理 mutation 必须继续使用 get_current_active_superuser，并覆盖：

- 未登录；
- 普通网页登录用户；
- API Key 请求；
- 失效/非活动会话；
- superuser 正常访问。

不能把前端菜单隐藏或页面 redirect 当成授权证据。

### 5. AuditEvent 迁移需要落到当前迁移链

计划需要补齐：

- 新迁移的明确文件名、down_revision（当前链末端）；
- actor_id 外键、SET NULL 行为、查询索引；
- details JSON 字段的非空/大小策略；
- upgrade 与 downgrade 的离线测试；
- downgrade 在审计表非空时 fail closed，禁止静默删除真实审计数据。

## Minor

### 6. models.py 的前置类型引用需要确认

E:\AI_projects\yeyu-api\backend\app\models.py 未启用 postponed annotations，却有 User 提前引用 Item、ApiKey。实现前应在当前项目 Python 版本和 SQLModel 版本下验证导入行为；如确有需要，再添加 from __future__ import annotations，并用现有模型测试验证，不要为审查建议做无关重构。

## 处理结论

本报告未批准原计划直接进入编码。以上 Critical/Important 项必须先写回计划并在实现阶段以测试覆盖；修订后再进行一次独立代码审查。
