import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { AdminHealthService } from "@/client"
import AdminPageShell from "@/components/Admin/AdminPageShell"
import { requireAdmin } from "@/components/Admin/requireAdmin"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/_layout/admin-health")({
  component: AdminHealth,
  beforeLoad: requireAdmin,
  head: () => ({
    meta: [{ title: "健康状态 - Yeyu API" }],
  }),
})

function AdminHealth() {
  const query = useQuery({
    queryKey: ["admin-health"],
    queryFn: async () =>
      (await AdminHealthService.healthReadAdminHealth()).data,
  })

  return (
    <AdminPageShell>
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
          管理端 / 健康状态
        </p>
        <h1 className="mt-2 text-2xl font-semibold">依赖健康摘要</h1>
        <p className="mt-2 text-muted-foreground">
          这里只显示固定的成功/失败状态，不回显连接字符串、迁移版本或异常详情。
        </p>
      </header>
      {query.isPending && (
        <p className="text-muted-foreground">正在检查依赖…</p>
      )}
      {query.isError && (
        <p className="text-destructive">
          健康摘要暂时无法读取，请检查后端管理权限。
        </p>
      )}
      {query.data && (
        <div className="grid gap-4 md:grid-cols-4" data-testid="admin-health">
          <Card>
            <CardHeader>
              <CardTitle>总体状态</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge
                variant={
                  query.data.status === "ready" ? "default" : "destructive"
                }
              >
                {query.data.status}
              </Badge>
            </CardContent>
          </Card>
          {Object.entries(query.data.checks).map(([name, value]) => (
            <Card key={name}>
              <CardHeader>
                <CardTitle>{name}</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge variant={value === "ok" ? "default" : "destructive"}>
                  {value}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AdminPageShell>
  )
}
