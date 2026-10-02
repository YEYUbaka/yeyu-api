import { Search, X } from "lucide-react"

interface CatalogSearchProps {
  value: string
  onChange: (value: string) => void
}

export function CatalogSearch({ value, onChange }: CatalogSearchProps) {
  return (
    <section
      className="catalog-search-panel"
      aria-labelledby="catalog-search-heading"
    >
      <div className="catalog-search-heading">
        <div>
          <p className="public-eyebrow">搜索优先</p>
          <h2 id="catalog-search-heading" className="catalog-search-title">
            先按接口名、简介或路径查找
          </h2>
        </div>
        <p className="catalog-search-hint">输入停止后约 400ms 更新目录</p>
      </div>
      <div className="catalog-search-control">
        <Search aria-hidden="true" className="catalog-search-icon" />
        <label className="sr-only" htmlFor="catalog-search-input">
          搜索公开 API
        </label>
        <input
          id="catalog-search-input"
          data-testid="catalog-search-input"
          className="catalog-search-input"
          type="search"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="例如：时间、UUID、工具"
          autoComplete="off"
        />
        {value ? (
          <button
            type="button"
            className="catalog-search-clear"
            aria-label="清除搜索"
            onClick={() => onChange("")}
          >
            <X aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </section>
  )
}

export default CatalogSearch
