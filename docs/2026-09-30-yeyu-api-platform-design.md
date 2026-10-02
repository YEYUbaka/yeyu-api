# Yeyu API 公益聚合平台设计说明

> 历史设计记录：用户已将首期范围改为纯静态 API 收集目录。本文中的登录、API Key、动态服务、数据库、缓存和代理设计均不属于当前交付范围；当前范围以 `E:\AI_projects\yeyu-api\docs\2026-10-02-static-api-directory-scope.md` 为准。

状态：设计稿 v0.1，已确认首页采用 A+B 组合方向；本文件完成后仍需用户审阅，审阅通过后才进入实施计划和代码阶段。

项目根目录：`E:\AI_projects\yeyu-api`

正式域名：`https://api.yeyubaka.top`

## 1. 产品边界

Yeyu API 是面向学生和个人开发者的公益、免费、自营优先 API 聚合平台。它提供可搜索的接口目录、可读的 API 文档、登录后的在线调试和独立 API Key 调用能力。

首期接口分成两类：

1. 无上游或低依赖的稳定工具接口，例如时间戳、时区、UUID、随机字符串、哈希、编码转换、JSON 校验和二维码生成。
2. 有来源、有缓存和降级规则的公共数据/内容适配器，例如天气、节假日、汇率、每日一言等。

第三方免费服务不会因为“能调用”就直接包装为公开接口。候选接口先进入试验池，完成来源、官方文档、账号/Key、额度、服务条款、再分发许可、署名、稳定性、延迟、格式、缓存、隐私、合规和成本记录后，才决定自研、调用上游、仅做链接或放弃。

明确不做：开放投稿、充值/套餐/商业计费、任意 URL 抓取、开放代理、代理 IP、端口扫描、临时邮箱、匿名文件托管、短信/邮件代发、短链接、未经授权的平台内容搬运、身份/银行卡/实名核验，以及 NewAPI 或大模型中转逻辑。

## 2. 已确认的视觉与信息结构

首页采用 A+B 组合：

- A「索引台」负责搜索优先、分类清晰、状态透明和公益可信度。
- B「开发者仪表盘」负责在首屏或一跳内展示请求方法、路径、鉴权、限额、缓存状态和 Quick Start 示例。
- 不展示虚假调用量、用户数、收益或“实时稳定”承诺。
- 示例使用真实候选接口名称，例如“时间戳与时区”“UUID”“天气”“DNS 查询”，并区分自营、缓存、试验池和待核验状态。
- 页面语言优先中文，代码示例同时提供 curl、JavaScript 和 Python。

信息层级：

1. 首页：搜索、分类、可信说明、少量推荐接口和 Quick Start。
2. 接口目录：搜索、分类、鉴权要求、免费标记、运行状态、更新时间和来源状态。
3. 接口详情/调试：请求方法、路径、参数、响应结构、错误码、示例、在线调试、限额和缓存/stale 说明。
4. 用户中心：身份绑定、API Key、额度、调用趋势、接口分布、脱敏请求记录和封禁/限流原因。
5. 管理端：用户、Key、接口元数据、策略、健康检查、试验池、凭据引用、异常调用和审计。

## 3. 框架复用调研与选型

### 3.1 推荐基础：官方 Full Stack FastAPI Template

[Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template) 作为项目起始骨架，而不是从空目录重写。其当前公开仓库已包含 FastAPI、SQLModel、PostgreSQL、React、TypeScript、Vite、Tailwind、shadcn/ui、自动生成前端客户端、Playwright、Docker Compose、JWT、密码恢复、React Email、Mailpit、Pytest、CI/CD、交互式 API 文档和基础管理面板；仓库使用 MIT 许可证。[README](https://raw.githubusercontent.com/fastapi/full-stack-fastapi-template/master/README.md) [许可证](https://raw.githubusercontent.com/fastapi/full-stack-fastapi-template/master/LICENSE)

复用范围：

- 保留项目目录结构、配置加载、数据库迁移、基础用户模型、JWT 管理登录、密码恢复、邮件模板、前端生成客户端、基础管理页、Docker Compose、测试和 CI 习惯。
- 把模板的示例 `Item` 域替换成 API 目录、接口策略、Key、调用记录和试验池域。
- 通过同一套 OpenAPI 生成前端类型，减少手写前后端 DTO。
- 复用模板的 Playwright 和 pytest 基础设施，不另造一套测试启动器。

模板已有 `is_active`、`is_superuser`、密码哈希、JWT 和密码恢复基础，但没有完整覆盖本项目的邮箱验证、GitHub 绑定、API Key 生命周期、调用额度和上游适配器。因此只补齐业务缺口，不另建第二套用户系统。

### 3.2 认证组件取舍

FastAPI Users 的文档覆盖邮箱验证、密码重置、JWT/Cookie/Redis 策略、OAuth 路由和 verified/superuser 依赖，理论上能减少认证胶水代码。[官方概览](https://fastapi-users.github.io/fastapi-users/latest/configuration/overview/) [路由文档](https://fastapi-users.github.io/fastapi-users/latest/usage/routes/?h=verify)

但其 SQLModel 数据库适配器仓库已在 2025-06-11 归档为只读。[fastapi-users-db-sqlmodel](https://github.com/fastapi-users/fastapi-users-db-sqlmodel) 因此首期不把它作为核心依赖，避免在已有 SQLModel 模板上引入一个需要自行维护的适配层。

邮件验证会沿用模板已有的邮件发送、token、配置和 Mailpit 测试方式，仅增加验证状态、一次性 token 哈希和 anti-enumeration 行为。GitHub OAuth 使用 Authlib 的 Starlette/FastAPI 客户端集成，服务端保存 OAuth 关联信息和必要的 token 元数据，不把 GitHub token 当作 Yeyu API Key。[Authlib Starlette 客户端](https://docs.authlib.org/en/latest/client/oauth2.html) [GitHub OAuth 流程](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)

### 3.3 其他候选基础及不选原因

| 候选 | 可复用能力 | 不作为首期基础的原因 |
|---|---|---|
| Supabase 自托管 | Auth、Postgres、Studio、REST、Realtime、Storage 和 Docker 部署 | 官方自托管架构包含多个服务，且数据库维护、备份、安全和升级责任全部转移给运营方；当前 2 核/3.4 GiB 服务器不适合再承载完整栈，且 Yeyu 需要自定义受控执行层而非通用后端平台。[自托管说明](https://supabase.com/docs/guides/self-hosting) [Docker 架构](https://supabase.com/docs/guides/self-hosting/docker) |
| Appwrite | Auth、数据库、Functions、Messaging、Storage、REST/GraphQL 和管理控制台 | 能力覆盖过宽，会增加独立平台服务和运维面；API 目录、Key 轮换、接口权重和安全适配器仍需自定义。[官方文档](https://appwrite.io/docs) |
| Django + DRF + allauth | Django Admin、成熟用户系统、社交登录、DRF 可浏览 API | 复用认证/后台能力很强，但会放弃已确认的 FastAPI/React 模板方向，并形成另一套 API schema 与前后端组织方式。[Django 认证](https://docs.djangoproject.com/en/6.1/topics/auth/default/) [DRF Browsable API](https://www.django-rest-framework.org/topics/browsable-api/) |
| SQLAdmin/Starlette Admin | 可嵌入 FastAPI 的数据库管理界面 | SQLAdmin 的认证是可选的，需要自行接入；模板已有 React 管理面板，首期不维护两个后台入口。[SQLAdmin 认证](https://github.com/smithyhq/sqladmin/blob/main/docs/authentication.md) |

结论：采用官方 Full Stack FastAPI Template 作为骨架，Authlib 作为 GitHub OAuth 客户端，继续使用模板已有的 React 管理界面；不引入 Supabase/Appwrite，也不叠加第二套后台或用户系统。

## 4. 运行架构

首期采用模块化单体 + 独立数据服务：

```text
浏览器
  ├─ 公共站点 / 目录 / 文档 / 管理 UI
  └─ 管理登录 Cookie 或短期管理 Token
          │ HTTPS
          ▼
宿主机 Nginx 独立 vhost（只负责 api.yeyubaka.top）
          │ 独立 Compose 网络
          ▼
FastAPI 应用容器
  ├─ account：邮箱、验证、密码重置、GitHub 绑定
  ├─ catalog：接口、分类、版本、文档、状态
  ├─ key：创建、前缀展示、撤销、轮换、哈希校验
  ├─ policy：账号/Key/IP 限流、每日额度、接口权重
  ├─ executor：固定的自营 handler 和 allowlist 上游 adapter
  ├─ cache：缓存、过期、stale fallback、数据时间
  ├─ audit：脱敏请求元数据、异常调用、封禁、管理审计
  └─ health：/health、/ready、上游健康检查
       │                         │
       ▼                         ▼
 PostgreSQL（权威业务数据）       Redis（限流、短缓存、并发控制）
```

前端沿用模板的 React/Vite 构建方式，生产构建由应用服务提供或由部署层独立提供静态资源；宿主机仍使用独立 Nginx vhost 做 TLS 和反向代理。数据库、Redis、日志和容器命名必须使用独立前缀，不能复用已有 NewAPI、Meter Vision 或个人网站资源。

部署候选优先是 `yeyuhome`，原因是它已有 Docker Compose/Nginx 且磁盘和内存相对充足；这只是候选，不代表已经授权部署。正式变更前仍需重新做端口、路径、权限、DNS、证书和回滚检查，并单独取得确认。

## 5. 关键数据与鉴权设计

核心实体：

- `User`：账号、邮箱验证状态、启用/封禁状态、管理员标记、时间字段。
- `OAuthIdentity`：provider、provider subject、关联用户、邮箱快照和更新时间；不把 OAuth token 当作 API Key。
- `ApiKey`：用户、不可逆 secret hash、公开 prefix、创建/最后使用/撤销/轮换时间和状态。
- `ApiDefinition`：slug、名称、分类、方法、路径、文档 Schema、免费标记、来源状态、公开状态和更新时间。
- `ApiPolicy`：账号默认额度、Key 额度、分钟/IP 限频、并发和接口权重。
- `ProviderAdapter`：固定适配器名称、允许的目标、超时、重试、缓存和合规状态；不接受用户任意 URL。
- `CacheEntry`：接口、参数指纹、响应、数据时间、过期时间、stale 状态和上游版本信息。
- `UsageDaily`：UTC 日期、用户/Key/接口维度的权威调用计数和加权计数。
- `RequestRecord`：时间、用户/Key ID、接口、状态码、耗时、缓存命中、stale、错误类别和脱敏 IP；不保存明文 Key 或敏感正文。
- `AuditEvent`：管理员、目标对象、动作、结果、时间和脱敏上下文。

鉴权边界：

- 管理网站使用模板的管理登录机制；浏览器登录状态只用于管理页面和在线调试页面。
- `/v1/*` 调用必须通过 `X-API-Key` 或明确文档规定的 API Key 位置，不能使用浏览器 Cookie 作为替代。
- API Key 使用足够长度的随机值，数据库只存哈希和 prefix；创建页面只返回完整值一次。
- 无 Key、错误 Key、已撤销 Key、被封禁账号和未验证邮箱分别返回统一错误结构和可诊断错误码，不泄漏内部信息。

## 6. 限流、缓存和失败降级

- 默认策略为每日 1000 次、每分钟 60 次，但所有值由数据库策略配置，不能硬编码到接口 handler。
- Redis 负责分钟、IP、并发和短期缓存计数；PostgreSQL 通过原子更新保存每日额度权威计数。
- 接口权重用于高成本接口消耗额外额度；高成本接口可以配置独立日额度和更严格的并发限制。
- 每个上游请求必须有固定 allowlist、连接/读取超时、响应大小限制、有限重试和熔断/降级状态。
- 缓存命中返回 `meta.cache_hit`；过期缓存允许返回时必须显式返回 `meta.stale=true`、`meta.data_at` 和 `meta.stale_reason`。
- 上游不可用且没有有效缓存时返回统一的可重试错误；不得用当前时间、空数组或虚构对象伪造实时数据。

## 7. 安全边界

- 不提供通用 URL、代理、任意文件、端口、Webhook 或用户可控上游地址。
- 所有 URL 型上游配置只来自管理员维护的 allowlist，解析后检查协议、DNS、IP、重定向目标和私网/链路本地/云元数据地址。
- 限制请求体、查询参数长度、JSON 深度、上传大小、响应大小、超时、并发和重试次数。
- 管理 API 使用 `is_superuser` 或更细的管理员权限依赖；普通用户不能读取凭据引用的值，只能看到状态和脱敏名称。
- 日志采用字段级脱敏，错误响应不能回显上游 Secret、请求头、完整 URL 查询参数或内部堆栈。
- 以 OWASP API Security Top 10 的认证、资源耗尽、SSRF、不安全上游调用、错误配置和资产盘点风险作为安全测试目录。[OWASP API Security Top 10](https://api-security.owasp.org/editions/2023/en/0x00-header/)

## 8. 测试与验收边界

测试分层：

1. 单元测试：Key hash/verify、状态机、限流算法、额度计算、缓存 stale、allowlist/SSRF、脱敏。
2. 集成测试：PostgreSQL 迁移、Redis 原子计数、认证流程、API Key 生命周期、统一错误响应。
3. 浏览器 E2E：注册/验证/重置、GitHub OAuth（使用可控测试凭据或明确阻塞）、目录搜索、详情、在线调试、用户中心和管理员隔离。
4. 上游契约测试：每个适配器的超时、重试、响应 Schema、缓存、stale fallback 和许可状态；不把不稳定的真实第三方调用当成默认 CI 必过项。
5. 部署验收：DNS/HTTPS、移动端、邮件、OAuth、Key、限流/额度、工具接口、内容接口、降级、后台权限、健康检查、日志脱敏和原有服务无影响。

通过 `/health`、`/ready`、构建成功或静态测试不能直接宣称产品完成；缺少 SMTP、GitHub OAuth、DNS、证书或服务器权限时必须记录为阻塞或未验证。

## 9. 实施顺序（只定义边界，不是本轮执行计划）

1. 固定模板版本、复制许可证和依赖清单，建立独立 conda 环境和 pnpm 工作流。
2. 将模板示例域替换为用户/认证扩展、API 目录和策略基础模型，先完成迁移与测试。
3. 加入邮箱验证和 GitHub OAuth 绑定，验证同一邮箱/身份合并与冲突策略。
4. 加入 API Key 生命周期和 `/v1/*` 独立鉴权。
5. 加入 Redis/PostgreSQL 限流、额度、审计和统一响应。
6. 先交付自营工具接口，再建立第三方试验池和第一个内容接口。
7. 完成 A+B 首页、目录、详情/调试、用户中心和管理端。
8. 完成安全测试、部署 preflight、可回滚发布和线上验收。

任何 DNS、Nginx、证书、服务器权限或生产数据变更都不属于本设计阶段授权范围。
