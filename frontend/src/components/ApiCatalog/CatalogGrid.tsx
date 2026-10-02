import type { CatalogItem } from "@/client"

import CatalogCard from "./CatalogCard"

interface CatalogGridProps {
  items: CatalogItem[]
}

export function CatalogGrid({ items }: CatalogGridProps) {
  return (
    <div className="catalog-grid" data-testid="catalog-grid">
      {items.map((item) => (
        <CatalogCard key={item.slug} item={item} />
      ))}
    </div>
  )
}

export default CatalogGrid
