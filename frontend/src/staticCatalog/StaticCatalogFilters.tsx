interface StaticCatalogFiltersProps {
  categories: string[]
  selectedCategory: string
  onSelect: (category: string) => void
}

export function StaticCatalogFilters({
  categories,
  selectedCategory,
  onSelect,
}: StaticCatalogFiltersProps) {
  return (
    <fieldset className="static-catalog-filters">
      <legend className="static-visually-hidden">按分类筛选</legend>
      {categories.map((category) => (
        <button
          className="static-catalog-filter"
          data-active={selectedCategory === category}
          key={category}
          type="button"
          onClick={() => onSelect(category)}
        >
          {category}
        </button>
      ))}
    </fieldset>
  )
}

export default StaticCatalogFilters
