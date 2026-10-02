import type { ApiDetail, CatalogItem } from "@/client"

export type CatalogSearchParams = {
  query?: string
  category?: string
  status?: string
}

export type CatalogMetadata = Record<string, unknown>

export function normalizeSearchValue(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined
  const normalized = value.trim()
  return normalized || undefined
}

export function parseCatalogSearch(
  search: Record<string, unknown>,
): CatalogSearchParams {
  return {
    query: normalizeSearchValue(search.query),
    category: normalizeSearchValue(search.category),
    status: normalizeSearchValue(search.status),
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

export function formatMetadata(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "string") return value
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value)
  }

  try {
    return JSON.stringify(value, null, 2) ?? "无法展示"
  } catch {
    return "无法展示"
  }
}

export function responseProperties(
  detail: ApiDetail,
): Array<[string, CatalogMetadata]> {
  const properties = asRecord(detail.response_schema)?.properties
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
