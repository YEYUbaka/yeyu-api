import { Link } from "@tanstack/react-router"

import type { ApiDetail } from "@/client"

import CodeExample from "./CodeExample"
import {
  asRecord,
  asText,
  buildPublicApiUrl,
  formatMetadata,
  formatUpdatedAt,
  normalizeInternalApiPath,
  normalizeSafeQueryKey,
  normalizeSafeQueryValue,
  PUBLIC_API_AUTH_HEADER,
  PUBLIC_API_BASE_URL,
  responseProperties,
  sanitizeMetadata,
} from "./catalog-types"

type QueryExample = {
  name: string
  value: string
}

function parameterExamples(detail: ApiDetail): QueryExample[] {
  return detail.parameters.flatMap((parameter) => {
    const safeParameter = asRecord(sanitizeMetadata(parameter))
    if (!safeParameter || asText(safeParameter.in, "") !== "query") {
      return []
    }

    const name = normalizeSafeQueryKey(safeParameter.name)
    if (!name) return []

    const schema = asRecord(safeParameter.schema)
    const candidates = [
      ...(Array.isArray(schema?.examples) ? schema.examples : []),
      schema?.default,
    ]
    const value = candidates
      .map((candidate) => normalizeSafeQueryValue(candidate))
      .find((candidate): candidate is string => candidate !== undefined)
    if (!value) return []

    return [{ name, value }]
  })
}

function quoteCurlArgument(value: string): string {
  return `'${value.replace(/'/g, "'\\''")}'`
}

function buildCodeExamples(detail: ApiDetail) {
  const candidateMethod = detail.method.toUpperCase()
  const method = /^[A-Z]{1,16}$/.test(candidateMethod) ? candidateMethod : "GET"
  const queryParameters = parameterExamples(detail)
  const path = normalizeInternalApiPath(detail.path)
  const absoluteUrl = buildPublicApiUrl(path)
  if (!path || !absoluteUrl) {
    const unavailable = "无法生成示例：目录路径不可用。"
    return {
      curl: unavailable,
      javascript: unavailable,
      python: unavailable,
    }
  }

  const curlStart =
    method === "GET"
      ? `curl -G ${quoteCurlArgument(absoluteUrl)}`
      : `curl -X ${method} ${quoteCurlArgument(absoluteUrl)}`
  const curlLines = [
    curlStart,
    `  -H ${quoteCurlArgument(`${PUBLIC_API_AUTH_HEADER}: <YOUR_API_KEY>`)}`,
  ]
  for (const parameter of queryParameters) {
    curlLines.push(
      `  --data-urlencode ${quoteCurlArgument(`${parameter.name}=${parameter.value}`)}`,
    )
  }

  const javascriptLines = [
    `const endpoint = new URL(${JSON.stringify(path)}, ${JSON.stringify(PUBLIC_API_BASE_URL)});`,
    ...queryParameters.map(
      (parameter) =>
        `endpoint.searchParams.set(${JSON.stringify(parameter.name)}, ${JSON.stringify(parameter.value)});`,
    ),
    "",
    "const response = await fetch(endpoint, {",
    `  method: ${JSON.stringify(method)},`,
    "  headers: {",
    `    ${JSON.stringify(PUBLIC_API_AUTH_HEADER)}: "<YOUR_API_KEY>",`,
    "  },",
    "});",
    "const data = await response.json();",
    "console.log(data);",
  ]

  const pythonLines = [
    "import requests",
    "",
    "response = requests.request(",
    `    ${JSON.stringify(method)},`,
    `    ${JSON.stringify(absoluteUrl)},`,
    `    headers={${JSON.stringify(PUBLIC_API_AUTH_HEADER)}: "<YOUR_API_KEY>"},`,
    ...(queryParameters.length
      ? [
          `    params=${JSON.stringify(Object.fromEntries(queryParameters.map((parameter) => [parameter.name, parameter.value])))},`,
        ]
      : []),
    "    timeout=10,",
    ")",
    "response.raise_for_status()",
    "print(response.json())",
  ]

  return {
    curl: curlLines.join(" \\\n"),
    javascript: javascriptLines.join("\n"),
    python: pythonLines.join("\n"),
  }
}

function readableCacheKey(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character: string) => character.toUpperCase())
}

interface ApiDetailViewProps {
  detail: ApiDetail
}

export function ApiDetailView({ detail }: ApiDetailViewProps) {
  const authHeader = PUBLIC_API_AUTH_HEADER
  const examples = buildCodeExamples(detail)
  const responseFields = responseProperties(detail)
  const safePath = normalizeInternalApiPath(detail.path)
  const safeCacheRules = asRecord(sanitizeMetadata(detail.cache_rules)) ?? {}
  const cacheEntries = Object.entries(safeCacheRules)

  return (
    <div className="api-detail-page">
      <div className="api-detail-breadcrumbs">
        <Link to="/catalog" search={{ page: 1 }} className="public-text-link">
          ← 返回公开目录
        </Link>
        <span aria-hidden="true">/</span>
        <span>{detail.category}</span>
      </div>

      <header className="api-detail-header">
        <div className="api-detail-path-row">
          <span className="catalog-method-badge">{detail.method}</span>
          <code>{safePath ?? "路径不可用"}</code>
        </div>
        <h1 className="api-detail-title">{detail.name}</h1>
        <p className="api-detail-summary">{detail.summary}</p>
        <div className="api-detail-tags">
          {detail.is_free ? (
            <span className="catalog-tag catalog-tag-free">免费</span>
          ) : null}
          <span className="catalog-tag catalog-tag-status">
            {detail.status}
          </span>
          <time dateTime={detail.updated_at ?? undefined}>
            更新于 {formatUpdatedAt(detail.updated_at)}
          </time>
        </div>
      </header>

      <div className="api-detail-layout">
        <main className="api-detail-main">
          <section
            className="api-detail-section"
            aria-labelledby="api-auth-heading"
          >
            <p className="public-eyebrow">AUTHENTICATION</p>
            <h2 id="api-auth-heading" className="api-detail-section-title">
              API Key 鉴权
            </h2>
            <p className="api-detail-copy">
              调用该接口时，请在 <code>{authHeader}</code> 请求头中提供你的 API
              Key。浏览器登录 Cookie 不会替代 API Key。
            </p>
            <div className="api-auth-callout">
              <span>请求头</span>
              <code>{authHeader}: &lt;YOUR_API_KEY&gt;</code>
            </div>
          </section>

          <section
            className="api-detail-section"
            aria-labelledby="api-parameters-heading"
          >
            <p className="public-eyebrow">REQUEST</p>
            <h2
              id="api-parameters-heading"
              className="api-detail-section-title"
            >
              参数
            </h2>
            {detail.parameters.length ? (
              <div className="api-table-scroll">
                <table className="api-detail-table">
                  <thead>
                    <tr>
                      <th scope="col">名称</th>
                      <th scope="col">位置</th>
                      <th scope="col">必填</th>
                      <th scope="col">类型 / 说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.parameters.map((parameter, index) => {
                      const safeParameter =
                        asRecord(sanitizeMetadata(parameter)) ?? {}
                      const schema = asRecord(safeParameter.schema)
                      const name =
                        normalizeSafeQueryKey(safeParameter.name) ??
                        `参数 ${index + 1}`
                      const schemaText = asText(schema?.type, "—")
                      const description = asText(safeParameter.description, "")
                      return (
                        <tr
                          key={`${name}-${asText(safeParameter.in, "unknown")}-${index}`}
                        >
                          <th scope="row">
                            <code>{name}</code>
                          </th>
                          <td>{asText(safeParameter.in)}</td>
                          <td>
                            {safeParameter.required === true ? "是" : "否"}
                          </td>
                          <td>
                            <span>{schemaText}</span>
                            {description ? (
                              <span className="api-table-note">
                                {description}
                              </span>
                            ) : null}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="api-detail-muted">该接口不接受参数。</p>
            )}
          </section>

          <section
            className="api-detail-section"
            aria-labelledby="api-response-heading"
          >
            <p className="public-eyebrow">RESPONSE</p>
            <h2 id="api-response-heading" className="api-detail-section-title">
              响应结构
            </h2>
            {responseFields.length ? (
              <div className="api-response-fields">
                {responseFields.map(([name, schema]) => (
                  <div key={name} className="api-response-field">
                    <code>{name}</code>
                    <span>{asText(schema.type, "object")}</span>
                    {schema.format ? (
                      <span>{asText(schema.format)}</span>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}
            <pre className="api-json-block">
              <code>{formatMetadata(detail.response_schema)}</code>
            </pre>
          </section>

          <section
            className="api-detail-section"
            aria-labelledby="api-errors-heading"
          >
            <p className="public-eyebrow">ERRORS</p>
            <h2 id="api-errors-heading" className="api-detail-section-title">
              错误码
            </h2>
            {detail.errors.length ? (
              <div className="api-table-scroll">
                <table className="api-detail-table">
                  <thead>
                    <tr>
                      <th scope="col">HTTP</th>
                      <th scope="col">错误码</th>
                      <th scope="col">说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.errors.map((error, index) => {
                      const safeError = asRecord(sanitizeMetadata(error)) ?? {}
                      return (
                        <tr key={`${asText(safeError.code, "error")}-${index}`}>
                          <td>{asText(safeError.status)}</td>
                          <th scope="row">
                            <code>{asText(safeError.code)}</code>
                          </th>
                          <td>
                            {asText(
                              safeError.description,
                              asText(safeError.message),
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="api-detail-muted">目录暂未提供错误码说明。</p>
            )}
          </section>

          <section
            className="api-detail-section"
            aria-labelledby="api-examples-heading"
          >
            <p className="public-eyebrow">EXAMPLES</p>
            <h2 id="api-examples-heading" className="api-detail-section-title">
              安全调用示例
            </h2>
            <p className="api-detail-copy">
              示例只使用占位密钥，不会读取或保存浏览器中的真实凭据。
            </p>
            <div className="api-code-grid">
              <CodeExample language="curl" code={examples.curl} />
              <CodeExample language="JavaScript" code={examples.javascript} />
              <CodeExample language="Python" code={examples.python} />
            </div>
          </section>
        </main>

        <aside className="api-detail-aside" aria-label="接口补充信息">
          <section
            className="api-aside-card"
            aria-labelledby="api-source-heading"
          >
            <p className="public-eyebrow">SOURCE</p>
            <h2 id="api-source-heading" className="api-aside-title">
              来源
            </h2>
            <p className="api-aside-value">{detail.source}</p>
          </section>
          <section
            className="api-aside-card"
            aria-labelledby="api-cache-heading"
          >
            <p className="public-eyebrow">CACHE</p>
            <h2 id="api-cache-heading" className="api-aside-title">
              缓存规则
            </h2>
            <dl className="api-cache-list">
              {cacheEntries.map(([key, value]) => (
                <div key={key}>
                  <dt>{readableCacheKey(key)}</dt>
                  <dd>{formatMetadata(value)}</dd>
                </div>
              ))}
            </dl>
          </section>
        </aside>
      </div>
    </div>
  )
}

export default ApiDetailView
