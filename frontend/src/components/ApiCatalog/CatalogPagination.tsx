interface CatalogPaginationProps {
  count: number
  page: number
  pageSize: number
  isFetching?: boolean
  onPageChange: (page: number) => void
}

export function CatalogPagination({
  count,
  page,
  pageSize,
  isFetching = false,
  onPageChange,
}: CatalogPaginationProps) {
  const safePageSize = Math.max(1, pageSize)
  const totalPages = Math.max(1, Math.ceil(count / safePageSize))
  if (totalPages <= 1) return null

  return (
    <nav className="catalog-pagination" aria-label="目录分页">
      <button
        type="button"
        className="public-inline-button"
        disabled={isFetching || page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        上一页
      </button>
      <span aria-live="polite">
        第 {page} / {totalPages} 页
      </span>
      <button
        type="button"
        className="public-inline-button"
        disabled={isFetching || page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        下一页
      </button>
    </nav>
  )
}

export default CatalogPagination
