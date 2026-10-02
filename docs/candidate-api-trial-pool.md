# 候选 API 试验池证据表

## 0. 结论与边界

- 证据检查日期：2026-10-02（Asia/Hong_Kong）。
- 本表只记录候选，不代表已经注册、申请 Key、接受条款、调用公网或获得再分发授权。
- 本轮没有第三方 provider 进入公开 API registry，也没有把免费额度、开源代码许可证或可访问的公开端点当成我方公开代理许可。
- status 取值：
  - approved：自营实现或已完成内部法务确认的能力。
  - trial：只有在条款明确允许、且试验范围、额度、缓存和署名义务已经书面固定时才可使用。
  - research_only：只允许继续研究，不得接入线上调用链。
  - link_only：只允许向用户提供原官方链接，不得代请求、缓存或改写。
- registry_eligible 是独立字段；status 为 research_only 或 link_only 时必须为 false。

## 1. 自营基准

### builtin-tools:time

- status：approved。
- registry_eligible：true。
- 来源与官方文档：Yeyu API 自有代码和固定 adapter registry；不依赖第三方上游。
- 账号或 Key：调用方必须使用 Yeyu API API Key；服务端不需要上游账号。
- 免费额度：沿用账号、Key、IP 和接口级策略；默认每日 1000、每分钟 60 的策略可由后台配置。
- 条款与授权主体：由项目运营者自营；公开使用规范、隐私政策和接口文档需要在正式上线前定稿。
- 再分发、缓存、改写：不存在第三方再分发问题；返回值按自营接口契约提供。
- 署名、商业/非商业：公益免费；仍需遵守站点使用规范，不得用于攻击、刷量或规避限制。
- 地域与隐私：不接受用户提交 URL；参数只允许固定 schema；请求记录不得保存明文 Key 或敏感正文。
- 稳定性与延迟：本地纯工具实现；真实部署延迟和容量尚未线上验证。
- 返回格式：统一 ApiResponse envelope。
- 缓存规则：时间结果不做跨请求内容缓存。
- 服务器成本：仅计算资源和日志/数据库开销；正式容量尚未评估。
- 推荐动作：继续作为首期公开工具。
- 证据：E:\AI_projects\yeyu-api\backend\app\services\execution\adapters\tools.py、E:\AI_projects\yeyu-api\backend\app\services\execution\registry.py。

### builtin-tools:uuid

- status：approved。
- registry_eligible：true。
- 来源与官方文档：Yeyu API 自有代码和固定 adapter registry；不依赖第三方上游。
- 账号或 Key：调用方必须使用 Yeyu API API Key；服务端不需要上游账号。
- 免费额度：沿用账号、Key、IP 和接口级策略；默认值可由后台配置。
- 条款与授权主体：自营能力，公开使用规范待正式发布。
- 再分发、缓存、改写：无第三方上游；返回值按自营契约提供。
- 署名、商业/非商业：公益免费；禁止用于刷量或资源耗尽。
- 地域与隐私：不接收 URL、文件或个人数据。
- 稳定性与延迟：本地纯工具实现；真实部署容量尚未线上验证。
- 返回格式：统一 ApiResponse envelope。
- 缓存规则：不缓存随机 UUID。
- 服务器成本：仅计算资源和日志/数据库开销。
- 推荐动作：继续作为首期公开工具。
- 证据：E:\AI_projects\yeyu-api\backend\app\services\execution\adapters\tools.py、E:\AI_projects\yeyu-api\backend\app\services\execution\registry.py。

## 2. 外部候选

### Open-Meteo：天气与空气质量

- status：research_only。
- registry_eligible：false。
- 来源与官方文档：[Open-Meteo 文档](https://open-meteo.com/en/docs)、[Open-Meteo 条款](https://open-meteo.com/en/terms)、[官方 GitHub README](https://github.com/open-meteo/open-meteo)。
- 账号或 Key：官方文档展示公开端点，本轮未注册账号或申请 Key。
- 免费额度：条款列出免费 API 的非商业限制和请求上限，包括每日、每小时、每分钟上限；上线前必须按条款原文重新核对，不能把它理解为无限额度。
- 条款版本/生效日期：官方条款页面本轮未提供可供本项目固定的独立版本号或明确生效日期；记录页面 URL 与查询日期 2026-10-02，正式接入前必须保存页面版本/快照或向服务方取得生效版本。
- 条款与授权主体：Open-Meteo 条款说明免费 API 面向非商业使用；数据标注 CC BY 4.0，官方仓库代码为 AGPLv3。公益身份不自动等于获得我方托管代理许可。
- 再分发许可：本轮没有确认“我方公开 API 代理、缓存、改写响应”的明确授权，因此不进入 registry。
- 缓存与改写：未确认可由我方公开缓存或改写；若后续研究，必须先确认条款版本、缓存时长、署名和响应改写边界。
- 署名：数据使用需要按 CC BY 4.0 提供署名；署名位置和完整要求待法务确认。
- 商业/非商业：免费层为非商业限制；本项目若包含广告、赞助权益或其他商业化安排，必须重新取得书面确认。
- 地域与隐私：本轮未确认额外地域限制；请求参数可能包含位置数据，必须限制为必要字段并在隐私政策中说明。
- 稳定性与延迟：未发起公网请求，延迟、配额余量和故障率均未验证。
- 返回格式：官方文档描述 JSON API；未将任何返回结构固化为我方公开契约。
- 缓存规则：在授权明确前不缓存、不 stale fallback、不改写。
- 服务器成本：免费层成本和使用权不能替代自有容量；自托管需要评估计算、数据更新和 AGPL 合规成本。
- 推荐动作：仅继续条款/许可证核验；若选择自托管，另行做 AGPL、数据来源、归因和更新任务审查。
- 查询证据：上限、非商业条件、CC BY 4.0 和 AGPL 信息来自上述官方条款与官方仓库，查询日期为 2026-10-02。

### Frankfurter：汇率

- status：research_only。
- registry_eligible：false。
- 来源与官方文档：[Frankfurter 官方站点](https://frankfurter.dev/)、[Frankfurter license 页面](https://frankfurter.dev/license/)、[Frankfurter OpenAPI](https://api.frankfurter.dev/)、[ECB SDMX API 帮助](https://data.ecb.europa.eu/help/getting-data-web-services-sdmx-0)、[ECB disclaimer](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)。
- 账号或 Key：官方页面展示公开 API；本轮未注册账号、未申请 Key、未调用端点。
- 免费额度：本轮官方材料未确认我方可依赖的免费额度或无限制承诺。
- 条款版本/生效日期：license 页面与数据来源说明未提供本项目可固定的独立服务条款版本/生效日期；仅记录官方页面和查询日期 2026-10-02，不能把 MIT 代码版本当成数据服务授权版本。
- 条款与授权主体：Frankfurter 的代码、文档和 Docker 项目标注 MIT；其 license 页面同时说明汇率来源于央行，Frankfurter 不当然拥有这些数据提供方的权利，提供方条款仍适用。
- 再分发许可：代码 MIT 不等于央行数据或 hosted API 的再分发授权；未确认公开代理、缓存和改写权，因此不进入 registry。
- 缓存与改写：未确认缓存期限、重写字段、stale fallback 和归因要求；研究阶段不缓存。
- 署名：需分别核对 Frankfurter 项目和各数据提供方要求；未确认前不公开包装。
- 商业/非商业：本轮没有取得我方使用场景的明确商业/非商业许可结论。
- 地域与隐私：汇率请求通常不需要个人数据；仍需核对数据提供方地域和使用限制。
- 稳定性与延迟：未发起公网请求；官方材料提示数据可能延迟、缺失或修订，不能承诺实时。
- 返回格式：官方 OpenAPI 可作为研究输入；未固化为我方契约。
- 缓存规则：未取得授权前不做公开缓存或 stale fallback。
- 服务器成本：调用成本、限流和自托管更新成本均未测量。
- 推荐动作：优先做“官方链接”或自有数据源可行性研究；若继续托管，先完成数据权利和条款确认。
- 查询证据：上述页面均在 2026-10-02 查询；没有自动接受任何协议。

### Nager.Date：节假日

- status：research_only；在 hosted API 条款明确前最多只能 link_only。
- registry_eligible：false。
- 来源与官方文档：[Nager.Date 官方 GitHub README](https://github.com/nager/Nager.Date/blob/main/README.md)、[源代码许可证](https://github.com/nager/Nager.Date/blob/main/LICENSE)。
- 账号或 Key：README 描述公开 Web API；README 同时提到离线方案的赞助/许可证 Key 要求。本轮未注册、未申请 Key、未调用 hosted API。
- 免费额度：未确认可供我方公开代理依赖的免费额度。
- 条款版本/生效日期：README/LICENSE 的当前分支页面未给出可固定的 hosted API 条款版本或生效日期；接入前必须固定 repository commit、服务条款快照和支持状态。
- 条款与授权主体：源代码许可证为 MIT，但 MIT 只说明代码使用条件，不能证明 hosted API 服务或节假日数据允许二次提供。README 中关于 Web API v4 的支持日期需要在接入前重新核验。
- 再分发许可：hosted API 条款、缓存、改写和公开代理权本轮未知；不得进入 registry。
- 缓存与改写：未知；不缓存、不改写、不提供 stale fallback。
- 署名：源代码和数据服务署名要求需分别确认。
- 商业/非商业：未知；公益项目也不能替代明确许可。
- 地域与隐私：请求通常只含国家和年份，但地域数据要求需核对；不上传个人信息。
- 稳定性与延迟：未发起公网请求；服务版本和 README 支持信息需要重新核验。
- 返回格式：README 描述 REST API；未固化为我方响应契约。
- 服务器成本：公开调用额度、延迟和自托管更新成本未测量。
- 推荐动作：暂仅提供官方链接；如需要自托管，单独核对代码、数据和许可证 Key 的组合条件。
- 查询证据：上述 README 和 LICENSE 于 2026-10-02 查询；没有向服务方发送请求。

### WorldTimeAPI：时间与时区数据

- status：research_only。
- registry_eligible：false。
- 来源与官方文档：[WorldTimeAPI 官方站点](https://worldtimeapi.org/)。
- 账号或 Key：本轮没有确认账号/Key要求，也没有注册或调用。
- 免费额度：未确认；不能假定无限制。
- 条款版本/生效日期：本轮没有找到可固定的官方服务条款版本或生效日期；候选主页和查询日期不构成授权证据。
- 条款与授权主体：本轮没有取得足以支持公开代理的条款、服务许可或再分发说明。
- 再分发、缓存、改写、署名：均未知；不接入、不缓存、不改写。
- 商业/非商业、地域、隐私：均未确认。
- 稳定性与延迟：未验证。
- 返回格式：可能提供 JSON，但未把未核验格式写入公开契约。
- 服务器成本：未知。
- 推荐动作：若需要时区能力，优先评估自营时区库/标准库实现；外部服务只做 link_only，直到获得完整官方条款证据。
- 查询证据：仅记录候选主页，2026-10-02 未调用端点；本记录不是许可结论。

## 3. 暂不进入试验池的高风险能力

临时邮箱、匿名文件托管、代理 IP、端口扫描、任意 URL 抓取/开放代理、短信或邮件代发、短链接、视频无水印解析、身份/银行卡/实名核验，以及未经授权的新闻全文、图片或平台内容转载，均不进入 registry 或内部 trial。它们需要独立的合规、滥用和数据权利评估。

## 4. 晋级门槛

外部候选只有在保存条款版本和查询日期、授权主体、再分发/缓存/改写权限、署名、额度、地域和隐私限制，并通过固定 adapter allowlist、超时/重试/大小/并发限制、stale 标记、日志脱敏和法务确认后，才可从 research_only 进入受控 trial。trial 不等于公开 registry；公开前还需要独立的线上验收和回滚方案。
