# Task 8 独立实现复审报告

- 复审代理：Popper（agent `01a0fc69-4599-77f1-a4ee-178f4271a876`）
- 复审方式：只读静态检查；实现与测试由主代理执行。
- 最终结论：Approved
- 复审日期：2026-10-02

## 复审范围

- SSRF、资源限制、统一错误 envelope、日志脱敏和候选接口证据边界。
- `ApiRunner` future 生命周期与 `QuotaLease` 续租、fencing、释放。
- Redis Lua 的 acquire/release/renew/fence/cancel 五类脚本及三套测试 fake 的参数和状态语义。
- 不确定 acquire 的延迟命令屏障、tombstone 保留期、清理 reservation 计数和全局清理调度器。

## 复审中发现并已修复的问题

1. HTTP 超时后过早释放并发租约，已改为 future 完成回调释放并在 future 生命周期内续租。
2. public API 的 404/405/422 和 request ID envelope 不一致，已补统一、脱敏的 ASGI 错误响应。
3. 租约过期后新任务可能抢占旧任务，已采用原子 active marker/fencing 语义。
4. Redis acquire 返回结果不确定时可能遗留 token，已增加三键原子 cancel tombstone，防止延迟 acquire 复活。
5. 释放失败原先可能为每个租约创建无限 daemon 重试线程，已改为有界、去重、退避的进程级调度器。
6. 清理槽位可能泄漏或在容量满时静默丢失，已加入每次生产 acquire 的 reservation、fail-closed admission 和 1025 次回归测试。
7. tombstone 永久增长和 timeout 边界不明确，已改为带 EXPIRE 的 ZSET，并在配置中校验其 TTL 大于 Redis 歧义窗口。

## 最终确认

- 未发现新的 Critical 或 Important 问题。
- 未发现正常 acquire/fence/release/cancel 路径的锁序死锁或并发放行窗口。
- 复审代理本轮未运行测试；测试、lint、compile 和 diff-check 证据由主代理分别记录在 `plans\\verification\\task-8-implementation-evidence.md`。
- 该报告不代表真实 PostgreSQL/Redis、Docker、SMTP、GitHub OAuth、DNS、Nginx、服务器或线上验收已经完成。
