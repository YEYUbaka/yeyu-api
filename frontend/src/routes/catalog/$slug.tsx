import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { CatalogService } from "@/client"
import ApiDetailView from "@/components/ApiCatalog/ApiDetailView"
import {
  CatalogDetailErrorState,
  CatalogLoadingState,
} from "@/components/ApiCatalog/CatalogStates"
import PublicLayout from "@/components/PublicSite/PublicLayout"

export const Route = createFileRoute("/catalog/$slug")({
  component: CatalogDetailRoute,
  head: () => ({
    meta: [
      {
        title: "API 详情 - Yeyu API",
      },
    ],
  }),
})

function CatalogDetailRoute() {
  const { slug } = Route.useParams()
  const detailQuery = useQuery({
    queryKey: ["public-catalog-detail", slug],
    queryFn: async () => {
      const response = await CatalogService.getCatalogDetail({
        path: { slug },
      })
      return response.data
    },
  })

  return (
    <PublicLayout>
      <div className="public-container catalog-detail-shell">
        {detailQuery.isPending ? (
          <CatalogLoadingState />
        ) : detailQuery.isError ? (
          <CatalogDetailErrorState onRetry={() => void detailQuery.refetch()} />
        ) : detailQuery.data ? (
          <ApiDetailView detail={detailQuery.data} />
        ) : null}
      </div>
    </PublicLayout>
  )
}
