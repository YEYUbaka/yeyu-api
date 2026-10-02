import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { AdminCatalogService } from "@/client"
import AdminPageShell from "@/components/Admin/AdminPageShell"
import { requireAdmin } from "@/components/Admin/requireAdmin"
import { Badge } from "@/components/ui/badge"

export const Route = createFileRoute("/_layout/admin-trial-pool")({
  component: AdminTrialPool,
  beforeLoad: requireAdmin,
  head: () => ({
    meta: [{ title: "候选试验池 - Yeyu API" }],
  }),
})

function AdminTrialPool() {
  const query = useQuery({
    queryKey: ["admin-trial-pool"],
    queryFn: async () =>
      (
        await AdminCatalogService.catalogReadAdminCatalog({
          query: { status: "trial", page: 1, page_size: 100 },
        })
      ).data,
  })

  return (
    <AdminPageShell>
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
          管理端 / 候选试验池
        </p>
        <h1 className="mt-2 text-2xl font-semibold">候选接口试验池</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          trial 只表示内部待审核定义，不代表已公开，也不允许填写任意
          URL。上游凭据只通过服务器 Secret 引用。
        </p>
      </header>
      {query.isPending && (
        <p className="text-muted-foreground">正在读取候选项…</p>
      )}
      {query.isError && (
        <p className="text-destructive">候选池暂时无法读取，请稍后重试。</p>
      )}
      {query.data && (
        <div
          className="grid gap-3 md:grid-cols-2"
          data-testid="admin-trial-pool"
        >
          {query.data.data.map((api) => (
            <article key={api.id} className="rounded-xl border p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold">{api.name}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {api.summary}
                  </p>
                </div>
                <Badge variant="outline">{api.status}</Badge>
              </div>
              <dl className="mt-4 grid gap-2 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">固定路径</dt>
                  <dd className="font-mono text-xs">
                    {api.method} {api.path}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">adapter</dt>
                  <dd className="font-mono text-xs">{api.adapter_name}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">provider ref</dt>
                  <dd className="font-mono text-xs">
                    {api.provider_ref ?? "—"}
                  </dd>
                </div>
              </dl>
            </article>
          ))}
          {query.data.data.length === 0 && (
            <p className="text-sm text-muted-foreground">
              当前没有 trial 候选接口。
            </p>
          )}
        </div>
      )}
    </AdminPageShell>
  )
}
