import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { AdminAuditService } from "@/client"
import AdminPageShell from "@/components/Admin/AdminPageShell"
import { requireAdmin } from "@/components/Admin/requireAdmin"
import { Badge } from "@/components/ui/badge"

export const Route = createFileRoute("/_layout/admin-audit")({
  component: AdminAudit,
  beforeLoad: requireAdmin,
  head: () => ({
    meta: [{ title: "审计记录 - Yeyu API" }],
  }),
})

function AdminAudit() {
  const query = useQuery({
    queryKey: ["admin-audit"],
    queryFn: async () =>
      (
        await AdminAuditService.auditReadAuditEvents({
          query: { page: 1, page_size: 100 },
        })
      ).data,
  })

  return (
    <AdminPageShell>
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
          管理端 / 审计记录
        </p>
        <h1 className="mt-2 text-2xl font-semibold">审计记录</h1>
        <p className="mt-2 text-muted-foreground">
          只展示已脱敏的动作摘要和字段名，不展示密码、API Key、OAuth token
          或请求正文。
        </p>
      </header>
      {query.isPending && (
        <p className="text-muted-foreground">正在读取审计记录…</p>
      )}
      {query.isError && (
        <p className="text-destructive">审计记录暂时无法读取，请稍后重试。</p>
      )}
      {query.data && (
        <div
          className="overflow-x-auto rounded-xl border"
          data-testid="admin-audit"
        >
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-muted/40">
              <tr>
                <th className="px-4 py-3 font-medium">时间</th>
                <th className="px-4 py-3 font-medium">动作</th>
                <th className="px-4 py-3 font-medium">对象</th>
                <th className="px-4 py-3 font-medium">结果</th>
                <th className="px-4 py-3 font-medium">脱敏字段</th>
              </tr>
            </thead>
            <tbody>
              {query.data.data.map((event) => (
                <tr key={event.id} className="border-b last:border-0">
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">
                    {new Date(event.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {event.action}
                  </td>
                  <td className="px-4 py-3">
                    <div>{event.object_type}</div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {event.object_id}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant={
                        event.outcome === "success" ? "default" : "secondary"
                      }
                    >
                      {event.outcome}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {Object.keys(event.details).join(", ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {query.data.data.length === 0 && (
            <p className="p-6 text-sm text-muted-foreground">
              还没有审计事件。
            </p>
          )}
        </div>
      )}
    </AdminPageShell>
  )
}
