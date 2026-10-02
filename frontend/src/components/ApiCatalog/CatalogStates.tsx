interface CatalogErrorStateProps {
  onRetry: () => void
}

export function CatalogLoadingState() {
  return (
    <div
      className="catalog-state catalog-skeleton-list"
      data-testid="catalog-loading"
      role="status"
      aria-label="正在加载公开目录"
    >
      <span className="catalog-skeleton-line catalog-skeleton-line-wide" />
      <span className="catalog-skeleton-line" />
      <span className="catalog-skeleton-line catalog-skeleton-line-short" />
      <span className="sr-only">正在读取真实目录……</span>
    </div>
  )
}

export function CatalogErrorState({ onRetry }: CatalogErrorStateProps) {
  return (
    <div
      className="catalog-state catalog-state-error"
      data-testid="catalog-error"
      role="alert"
    >
      <div>
        <p className="catalog-state-kicker">目录读取失败</p>
        <p>公开目录暂时无法读取，请稍后重试。</p>
      </div>
      <button type="button" className="public-inline-button" onClick={onRetry}>
        重试
      </button>
    </div>
  )
}

export function CatalogEmptyState() {
  return (
    <div className="catalog-state" data-testid="catalog-empty" role="status">
      <p className="catalog-state-kicker">没有匹配结果</p>
      <p>没有找到匹配的公开接口，请换一个关键词或清除筛选。</p>
    </div>
  )
}

export function CatalogDetailErrorState({ onRetry }: CatalogErrorStateProps) {
  return (
    <div
      className="catalog-state catalog-state-error"
      data-testid="catalog-detail-error"
      role="alert"
    >
      <div>
        <p className="catalog-state-kicker">详情读取失败</p>
        <p>该接口可能已下线，或目录服务暂时不可用。</p>
      </div>
      <button type="button" className="public-inline-button" onClick={onRetry}>
        重试
      </button>
    </div>
  )
}
