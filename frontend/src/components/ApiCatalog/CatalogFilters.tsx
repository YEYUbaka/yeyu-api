import type { CatalogItem } from "@/client"

import { uniqueCatalogValues } from "./catalog-types"

interface CatalogFiltersProps {
  items: CatalogItem[]
  category?: string
  status?: string
  onCategoryChange: (value: string) => void
  onStatusChange: (value: string) => void
}

export function CatalogFilters({
  items,
  category,
  status,
  onCategoryChange,
  onStatusChange,
}: CatalogFiltersProps) {
  const categories = uniqueCatalogValues(items, "category", category)
  const statuses = uniqueCatalogValues(items, "status", status)

  return (
    <section
      className="catalog-filters"
      aria-labelledby="catalog-filter-heading"
    >
      <div>
        <p className="public-eyebrow">筛选</p>
        <h2 id="catalog-filter-heading" className="catalog-filter-title">
          缩小公开接口范围
        </h2>
      </div>
      <div className="catalog-filter-controls">
        <div className="catalog-filter-field">
          <label htmlFor="catalog-category">分类</label>
          <select
            id="catalog-category"
            aria-label="分类"
            value={category ?? ""}
            onChange={(event) => onCategoryChange(event.target.value)}
          >
            <option value="">全部分类</option>
            {categories.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <div className="catalog-filter-field">
          <label htmlFor="catalog-status">状态</label>
          <select
            id="catalog-status"
            aria-label="状态"
            value={status ?? ""}
            onChange={(event) => onStatusChange(event.target.value)}
          >
            <option value="">全部状态</option>
            {statuses.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
      </div>
    </section>
  )
}

export default CatalogFilters
