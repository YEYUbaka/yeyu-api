import type { ApiDetail, CatalogItem } from "@/client"

export type CatalogSearchParams = {
  query?: string
  category?: string
  status?: string
  page: number
}

export type CatalogMetadata = Record<string, unknown>

export type CatalogFacetResult =
  | {
      items: CatalogItem[]
      complete: true
    }
  | {
      items: []
      complete: false
      reason: "page-limit"
    }

export const PUBLIC_API_BASE_URL = "https://api.yeyubaka.top"
export const PUBLIC_API_AUTH_HEADER = "X-API-Key"

const SENSITIVE_METADATA_KEY_PARTS = [
  "token",
  "secret",
  "password",
  "authorization",
  "cookie",
  "apikey",
  "credential",
  "privatekey",
  "providerref",
]
const SAFE_QUERY_KEY_PATTERN = /^[A-Za-z][A-Za-z0-9_.-]{0,63}$/
const SAFE_QUERY_VALUE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/+:-]{0,127}$/
const QUERY_VALUE_SCHEME_PATTERN = /^[A-Za-z][A-Za-z0-9+.-]*:/
const SENSITIVE_QUERY_VALUE_PATTERN =
  /(token|secret|password|authorization|cookie|api[-_]?key|credential|private[-_]?key|bearer)/i
const JWT_LIKE_PATTERN =
  /^[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}$/

function normalizedMetadataKey(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9]/g, "")
}

function isSensitiveMetadataKey(key: string): boolean {
  const normalized = normalizedMetadataKey(key)
  return SENSITIVE_METADATA_KEY_PARTS.some((part) => normalized.includes(part))
}

export function normalizeSearchValue(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined
  const normalized = value.trim()
  return normalized || undefined
}

export function normalizeSafeQueryKey(value: unknown): string | undefined {
  return typeof value === "string" &&
    SAFE_QUERY_KEY_PATTERN.test(value) &&
    !isSensitiveMetadataKey(value)
    ? value
    : undefined
}

export function normalizeSafeQueryValue(value: unknown): string | undefined {
  const text =
    typeof value === "string"
      ? value
      : typeof value === "number" && Number.isFinite(value)
        ? String(value)
        : typeof value === "boolean"
          ? String(value)
          : undefined

  if (
    !text ||
    text !== text.trim() ||
    !SAFE_QUERY_VALUE_PATTERN.test(text) ||
    text.includes("://") ||
    QUERY_VALUE_SCHEME_PATTERN.test(text) ||
    SENSITIVE_QUERY_VALUE_PATTERN.test(text) ||
    JWT_LIKE_PATTERN.test(text)
  ) {
    return undefined
  }

  return text
}

export function normalizePage(value: unknown): number {
  const page =
    typeof value === "number"
      ? value
      : typeof value === "string" && value.trim()
        ? Number(value)
        : Number.NaN

  return Number.isSafeInteger(page) && page > 0 ? page : 1
}

export function normalizeInternalApiPath(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined

  const normalized = value.trim()
  if (!normalized) return undefined

  if (
    !normalized.startsWith("/") ||
    normalized.startsWith("//") ||
    normalized.includes("//") ||
    /https?:/i.test(normalized) ||
    normalized.includes("\\") ||
    /[?#%]/.test(normalized) ||
    normalized.includes("..")
  ) {
    return undefined
  }

  return normalized
}

export function buildPublicApiUrl(value: unknown): string | undefined {
  const path = normalizeInternalApiPath(value)
  return path ? `${PUBLIC_API_BASE_URL}${path}` : undefined
}

export function parseCatalogSearch(
  search: Record<string, unknown>,
): CatalogSearchParams {
  return {
    query: normalizeSearchValue(search.query),
    category: normalizeSearchValue(search.category),
    status: normalizeSearchValue(search.status),
    page: normalizePage(search.page),
  }
}

export function formatUpdatedAt(value?: string | null): string {
  if (!value) return "更新时间待补充"

  const timestamp = Date.parse(value)
  if (Number.isNaN(timestamp)) return value

  return new Intl.DateTimeFormat("zh-HK", {
    dateStyle: "medium",
  }).format(new Date(timestamp))
}

export function asRecord(value: unknown): CatalogMetadata | undefined {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return undefined
  }
  return value as CatalogMetadata
}

export function asText(value: unknown, fallback = "—"): string {
  if (typeof value === "string") return value
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value)
  }
  return fallback
}

export function sanitizeMetadata(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeMetadata(item))
  }

  if (typeof value !== "object" || value === null) return value

  const sanitized: CatalogMetadata = {}
  for (const [key, nestedValue] of Object.entries(value)) {
    if (isSensitiveMetadataKey(key)) continue
    sanitized[key] = sanitizeMetadata(nestedValue)
  }
  return sanitized
}

export function formatMetadata(value: unknown): string {
  const sanitized = sanitizeMetadata(value)
  if (sanitized === null || sanitized === undefined) return "—"
  if (typeof sanitized === "string") return sanitized
  if (typeof sanitized === "number" || typeof sanitized === "boolean") {
    return String(sanitized)
  }

  try {
    return JSON.stringify(sanitized, null, 2) ?? "无法展示"
  } catch {
    return "无法展示"
  }
}

export function responseProperties(
  detail: ApiDetail,
): Array<[string, CatalogMetadata]> {
  const safeResponseSchema = asRecord(sanitizeMetadata(detail.response_schema))
  const properties = safeResponseSchema?.properties
  if (!properties || typeof properties !== "object") return []

  return Object.entries(properties)
    .map(
      ([name, value]) =>
        [name, asRecord(value) ?? {}] as [string, CatalogMetadata],
    )
    .sort(([left], [right]) => left.localeCompare(right))
}

export function uniqueCatalogValues(
  items: CatalogItem[],
  field: "category" | "status",
  currentValue?: string,
): string[] {
  const values = new Set(items.map((item) => item[field]).filter(Boolean))
  if (currentValue) values.add(currentValue)
  return Array.from(values).sort((left, right) => left.localeCompare(right))
}
