# API 目录契约

> 历史动态平台契约：当前首期只交付静态 API 收集目录。本文中的 `/api/v1/catalog`、管理员接口和实际执行接口不属于当前交付范围；当前范围以 `E:\AI_projects\yeyu-api\docs\2026-10-02-static-api-directory-scope.md` 为准。

## 目标

目录只保存经过人工维护的 API 元数据，不保存任意用户提交的上游 URL，也不执行代理转发。`adapter_name` 指向后续代码中的固定适配器；`provider_ref` 只能是内部引用，公开响应不会返回它。

## 公开接口

- `GET /api/v1/catalog`
  - 查询参数：`query`、`category`、`status`、`page`、`page_size`。
  - 只返回 `visibility=public` 且 `status=healthy` 或 `published` 的定义。
  - 返回 `{data, count, page, page_size}`。
- `GET /api/v1/catalog/{slug}`
  - 不要求登录。
  - 返回请求方法、路径、`X-API-Key` 鉴权说明、参数、响应结构、错误码、示例、来源、缓存规则和更新时间。
  - 不返回 `provider_ref`、上游凭据或执行器内部配置。

公开目录和实际 `/api/v1/...` 执行接口是两条边界：目录本身不需要 API Key；实际调用接口必须由后续 API Key Task 独立鉴权。

## 管理接口

- `POST /api/v1/admin/catalog/{slug}`：创建目录定义。
- `PATCH /api/v1/admin/catalog/{slug}`：更新目录定义。
- `DELETE /api/v1/admin/catalog/{slug}`：删除目录定义。

管理接口要求已登录超级用户。请求模型拒绝未知字段，因此 `upstream_url` 等任意代理参数不会被静默接受。`path` 必须是以 `/` 开始的内部路径，禁止 URL、反斜杠和路径穿越；`provider_ref` 禁止 URL。

## 状态与发布

候选接口可以先记录为 `trial` 或其他非公开状态。只有 `public + healthy/published` 才会进入公开目录。真实第三方内容适配器必须另行完成来源、条款、再分发许可、署名、缓存、隐私和成本审查；本 Task 不默认授权任何第三方接口。
