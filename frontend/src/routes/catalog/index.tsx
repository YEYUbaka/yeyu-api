import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import { type CatalogItem, type CatalogPage, CatalogService } from "@/client"
import CatalogFilters from "@/components/ApiCatalog/CatalogFilters"
import CatalogGrid from "@/components/ApiCatalog/CatalogGrid"
import CatalogPagination from "@/components/ApiCatalog/CatalogPagination"
import CatalogSearch from "@/components/ApiCatalog/CatalogSearch"
import {
  CatalogEmptyState,
  CatalogErrorState,
  CatalogLoadingState,
} from "@/components/ApiCatalog/CatalogStates"
import {
  type CatalogSearchParams,
  normalizeSearchValue,
  parseCatalogSearch,
} from "@/components/ApiCatalog/catalog-types"
import PublicLayout from "@/components/PublicSite/PublicLayout"

const FACET_PAGE_SIZE = 100
const MAX_FACET_PAGES = 100

async function fetchCatalogFacetItems(): Promise<CatalogItem[]> {
  const items: CatalogItem[] = []

  for (let page = 1; page <= MAX_FACET_PAGES; page += 1) {
    const response = await CatalogService.searchCatalog({
      query: {
        page,
        page_size: FACET_PAGE_SIZE,
      },
    })
    const catalogPage = response.data
    items.push(...catalogPage.data)

    if (items.length >= catalogPage.count || catalogPage.data.length === 0) {
      return items
    }
  }

  return items
}

export const Route = createFileRoute("/catalog/")({
  validateSearch: (search): CatalogSearchParams => parseCatalogSearch(search),
  component: CatalogRoutePage,
  head: () => ({
    meta: [
      {
        title: "API 目录 - Yeyu API",
      },
    ],
  }),
})

function CatalogRoutePage() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const [draftQuery, setDraftQuery] = useState(search.query ?? "")

  useEffect(() => {
    setDraftQuery(search.query ?? "")
  }, [search.query])

  useEffect(() => {
    const normalizedQuery = normalizeSearchValue(draftQuery)
    if (normalizedQuery === search.query) return

    const timeoutId = window.setTimeout(() => {
      void navigate({
        search: (previous) => ({
          ...previous,
          query: normalizedQuery,
          page: 1,
        }),
        replace: true,
      })
    }, 400)

    return () => window.clearTimeout(timeoutId)
  }, [draftQuery, navigate, search.query])

  const catalogQuery = useQuery<CatalogPage>({
    queryKey: [
      "public-catalog",
      search.query ?? "",
      search.category ?? "",
      search.status ?? "",
      search.page,
    ],
    queryFn: async () => {
      const response = await CatalogService.searchCatalog({
        query: {
          query: search.query,
          category: search.category,
          status: search.status,
          page: search.page,
          page_size: 20,
        },
      })
      return response.data
    },
  })

  const catalogFacetQuery = useQuery<CatalogItem[]>({
    queryKey: ["public-catalog-facets"],
    queryFn: fetchCatalogFacetItems,
    staleTime: 60_000,
  })

  const items = catalogQuery.data?.data ?? []
  const filterItems = catalogFacetQuery.data ?? items
  const updateFilter = (key: "category" | "status", value: string) => {
    void navigate({
      search: (previous) => ({
        ...previous,
        [key]: normalizeSearchValue(value),
        page: 1,
      }),
      replace: true,
    })
  }

  return (
    <PublicLayout>
      <div className="public-container catalog-page-shell">
        <header className="catalog-page-header">
          <p className="public-eyebrow">公开目录 / REAL DATA</p>
          <h1 className="catalog-page-title">API 目录</h1>
          <p className="catalog-page-lede">
            只展示后端公开、健康或已发布的真实接口。先搜索，再阅读完整调用契约。
          </p>
        </header>

        <CatalogSearch value={draftQuery} onChange={setDraftQuery} />
        <CatalogFilters
          items={filterItems}
          category={search.category}
          status={search.status}
          onCategoryChange={(value) => updateFilter("category", value)}
          onStatusChange={(value) => updateFilter("status", value)}
        />
        {catalogFacetQuery.isError && !catalogQuery.isError ? (
          <CatalogErrorState onRetry={() => void catalogFacetQuery.refetch()} />
        ) : null}

        <section
          className="catalog-results"
          aria-labelledby="catalog-results-heading"
        >
          <div className="catalog-results-heading">
            <div>
              <p className="public-eyebrow">RESULTS</p>
              <h2
                id="catalog-results-heading"
                className="catalog-results-title"
              >
                可用接口
              </h2>
            </div>
            {catalogQuery.data ? (
              <p className="catalog-results-count">
                共 {catalogQuery.data.count} 条
              </p>
            ) : null}
          </div>

          {catalogQuery.isFetching && !catalogQuery.isPending ? (
            <p className="catalog-refreshing" role="status">
              正在更新目录……
            </p>
          ) : null}
          {catalogQuery.isPending ? <CatalogLoadingState /> : null}
          {catalogQuery.isError ? (
            <CatalogErrorState onRetry={() => void catalogQuery.refetch()} />
          ) : null}
          {!catalogQuery.isPending &&
          !catalogQuery.isError &&
          items.length === 0 ? (
            <CatalogEmptyState />
          ) : null}
          {!catalogQuery.isPending &&
          !catalogQuery.isError &&
          items.length > 0 ? (
            <CatalogGrid items={items} />
          ) : null}
          {!catalogQuery.isPending &&
          !catalogQuery.isError &&
          catalogQuery.data ? (
            <CatalogPagination
              count={catalogQuery.data.count}
              page={search.page}
              pageSize={catalogQuery.data.page_size}
              isFetching={catalogQuery.isFetching}
              onPageChange={(page) =>
                void navigate({
                  search: (previous) => ({ ...previous, page }),
                  replace: true,
                })
              }
            />
          ) : null}
        </section>
      </div>
    </PublicLayout>
  )
}
