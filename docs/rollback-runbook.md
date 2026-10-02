# Yeyu API 回滚手册

## 1. 适用范围

本手册只适用于独立的 Yeyu API 发布单元，不得操作旧个人网站、音乐 API、Waline、new.api.yeyubaka.top 或其他既有服务。正式域名、DNS、Nginx、证书、服务器账号和权限变更必须先获得用户确认，并在变更前给出影响文件、验证方式和回滚方案。

生产主机使用抽象目录：

- 应用发布根目录：/opt/yeyu-api/
- 版本目录：/opt/yeyu-api/releases/<commit-sha>/
- current：指向当前版本目录的可切换引用。
- previous：保留上一个已验收版本。
- 独立 Compose project：yeyu-api。
- 独立 PostgreSQL、Redis、应用日志和 Nginx vhost；不得复用旧站目录或服务容器。

上面的路径是部署设计占位，不是当前服务器事实。本 Task 不创建、不修改、不检查生产路径。

## 2. 发布前不变量

1. 发布包必须来自已经推送的、可追溯 commit；镜像/静态产物与 commit 一一对应。
2. 发布前保留 previous 版本和上一份可恢复配置；Secret 只由服务器环境变量或 Secret 文件注入，不复制进版本目录和日志。
3. 数据库迁移采用 expand/contract：先增加兼容结构，再发布读写代码，确认旧版本可读后才清理旧结构。
4. 默认回滚是应用版本切换，不是数据库 downgrade；禁止为了“回到旧代码”自动删除数据或执行 downgrade。
5. 备份、恢复、重建 Redis 和删除发布目录都必须单独确认；不要把不可逆操作放进无人确认的脚本。
6. Redis concurrency lease 在续租失败时可能留下 fail-closed fencing marker；marker 只能由确认 future 已结束、检查请求状态并记录审计的受控管理操作清理，禁止自动清除后放行。

## 3. 发布步骤

1. 只读核对目标 commit、镜像 digest、环境变量名、Secret 文件权限、Compose project 名和独立端口。
2. 在 releases/<commit-sha> 写入或准备版本，不覆盖 current、旧站目录或共享日志目录。
3. 如包含 expand 迁移，在独占数据库上先备份并记录迁移输出；生产数据库操作必须按独立变更审批执行。
4. 启动新版本的独立 Compose 服务，先检查容器状态、/health、/ready、数据库迁移状态、Redis ping 和应用日志脱敏。
5. 在切换 current 前执行受控 smoke：公开首页、API 文档、无 Key 拒绝、一个工具接口、管理端权限隔离。
6. 原子切换 current，并保留 previous；Nginx/证书/DNS 仅在已确认的独立变更窗口内切换。
7. 切换后再次检查新域名、TLS、健康检查、关键接口和旧站只读 smoke；记录 commit、时间和证据。

## 4. 触发回滚的条件

出现以下任一项，停止继续扩大流量并评估回滚：

- /health 或 /ready 失败；
- 数据库连接、Redis 连接或迁移状态不符合清单；
- API Key 鉴权绕过、限流失效、权限越界或 Secret 进入响应/日志；
- 工具接口错误 envelope 或 request ID 不一致；
- 内容接口返回未标 stale 的过期数据，或上游异常未降级；
- 旧网站、音乐 API、Waline 或其他既有服务出现异常；
- TLS、DNS、Nginx 或路由冲突；
- 发布版本无法证明来源或无法恢复 previous。

## 5. 应用版本回滚

1. 记录当前异常、请求 ID、当前 commit 和最后一个可用 commit；不要把请求正文、API Key 或 Secret 写进工单/日志。
2. 停止新版本流量或将 current 原子切回 previous；只操作 Yeyu API 的独立 Compose project。
3. 用 previous 版本启动独立服务，检查 /health、/ready、数据库连接、Redis 和最小 smoke。
4. 如 Nginx/证书/DNS 已在获批窗口内变更，仅回滚 Yeyu API 独立 vhost/路由；不得改旧站配置。
5. 将失败版本标记为不可用，保留其日志和镜像摘要用于审查；不要删除证据。
6. 回滚完成后更新发布清单为 blocked 或 not_verified，并由负责人决定修复窗口。

## 6. 数据库不兼容时

- 默认先保持数据库结构，回滚应用代码；不要自动执行 downgrade。
- 只有在已确认新旧版本都不再需要该结构、已有可验证备份、维护窗口和用户明确批准时，才评估反向迁移。
- upgrade → downgrade -1 → upgrade 只在本 Task 独占、可销毁的临时 PostgreSQL 上验证；共享开发库、现有业务库和生产库禁止作为回滚测试对象。
- 恢复备份、删除表、重建数据库或重放数据需要单独的操作记录和回滚方案；本手册不包含真实账号、Secret 或生产连接串。

## 7. 回滚后验收

必须记录：

- 实际切回的 commit SHA、镜像 digest 和时间；
- /health、/ready、API Key 鉴权、限流、管理权限和日志脱敏结果；
- 旧网站及其他既有服务未被修改的只读证据；
- 数据库迁移状态、备份/恢复动作（如有）和未解决风险；
- 下一步修复负责人和重新发布前必须补齐的清单项。

未完成这些证据前，状态只能是 blocked 或 not_verified，不得宣称线上恢复完成。
