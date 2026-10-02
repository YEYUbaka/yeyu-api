import { Link } from "@tanstack/react-router"

import type { CatalogItem } from "@/client"

import { formatUpdatedAt } from "./catalog-types"

interface CatalogCardProps {
  item: CatalogItem
}

export function CatalogCard({ item }: CatalogCardProps) {
  return (
    <article className="catalog-card" data-testid={`catalog-card-${item.slug}`}>
      <div className="catalog-card-path">
        <span className="catalog-method-badge">{item.method}</span>
        <code>{item.path}</code>
      </div>
      <div className="catalog-card-content">
        <Link
          to="/catalog/$slug"
          params={{ slug: item.slug }}
          className="catalog-card-title"
        >
          {item.name}
        </Link>
        <p className="catalog-card-summary">{item.summary}</p>
      </div>
      <div className="catalog-card-meta">
        <span className="catalog-tag">{item.category}</span>
        {item.is_free ? (
          <span className="catalog-tag catalog-tag-free">免费</span>
        ) : null}
        <span className="catalog-tag catalog-tag-status">{item.status}</span>
        <time dateTime={item.updated_at ?? undefined}>
          更新于 {formatUpdatedAt(item.updated_at)}
        </time>
      </div>
    </article>
  )
}

export default CatalogCard
