import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import { AdminCatalogService } from "@/client"
import AdminPageShell from "@/components/Admin/AdminPageShell"
import { requireAdmin } from "@/components/Admin/requireAdmin"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export const Route = createFileRoute("/_layout/admin-apis")({
  component: AdminApis,
  beforeLoad: requireAdmin,
  head: () => ({
    meta: [{ title: "接口元数据 - Yeyu API" }],
  }),
})

function AdminApis() {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ["admin-catalog"],
    queryFn: async () =>
      (
        await AdminCatalogService.catalogReadAdminCatalog({
          query: { page: 1, page_size: 100 },
        })
      ).data,
  })
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const selectedApi = query.data?.data.find((api) => api.slug === selectedSlug)
  const [name, setName] = useState("")
  const [summary, setSummary] = useState("")
  const [category, setCategory] = useState("")
  const [status, setStatus] = useState("trial")
  const [source, setSource] = useState("")

  useEffect(() => {
    if (!selectedApi) return
    setName(selectedApi.name)
    setSummary(selectedApi.summary)
    setCategory(selectedApi.category)
    setStatus(selectedApi.status)
    setSource(selectedApi.source)
  }, [selectedApi])

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedApi) throw new Error("No API selected")
      return (
        await AdminCatalogService.catalogUpdateCatalogDefinition({
          path: { slug: selectedApi.slug },
          body: { name, summary, category, status, source },
        })
      ).data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin-catalog"] })
    },
  })

  return (
    <AdminPageShell>
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
          管理端 / 接口元数据
        </p>
        <h1 className="mt-2 text-2xl font-semibold">接口元数据</h1>
        <p className="mt-2 text-muted-foreground">
          维护已登记的自营接口。这里展示的是内部 adapter/provider
          标识，不展示任何上游凭据。
        </p>
      </header>
      {query.isPending && (
        <p className="text-muted-foreground">正在读取接口目录…</p>
      )}
      {query.isError && (
        <p className="text-destructive">接口目录暂时无法读取，请稍后重试。</p>
      )}
      {query.data && (
        <div
          className="overflow-x-auto rounded-xl border"
          data-testid="admin-api-table"
        >
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-muted/40">
              <tr>
                <th className="px-4 py-3 font-medium">接口</th>
                <th className="px-4 py-3 font-medium">路径</th>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">执行边界</th>
                <th className="px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {query.data.data.map((api) => (
                <tr
                  key={api.id}
                  className={`border-b last:border-0 ${selectedSlug === api.slug ? "bg-muted/50" : ""}`}
                >
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      className="text-left font-medium underline-offset-4 hover:underline"
                      onClick={() => setSelectedSlug(api.slug)}
                    >
                      {api.name}
                    </button>
                    <div className="text-xs text-muted-foreground">
                      {api.slug}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {api.method} {api.path}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant={
                        api.status === "published" ? "default" : "secondary"
                      }
                    >
                      {api.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-mono text-xs">{api.adapter_name}</div>
                    <div className="text-xs text-muted-foreground">
                      {api.provider_ref ?? "未设置内部引用"}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedSlug(api.slug)}
                    >
                      编辑
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {selectedApi && (
        <form
          className="grid max-w-2xl gap-5 rounded-xl border p-6"
          data-testid="admin-api-editor"
          onSubmit={(event) => {
            event.preventDefault()
            updateMutation.mutate()
          }}
        >
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
              编辑 / {selectedApi.slug}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              这里只编辑展示元数据和发布状态。路径、adapter、provider
              由服务端固定校验，不能从页面改成任意上游地址。
            </p>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="api-name">名称</Label>
            <Input
              id="api-name"
              value={name}
              maxLength={255}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="api-summary">简介</Label>
            <textarea
              id="api-summary"
              className="min-h-24 rounded-md border bg-background px-3 py-2 text-sm"
              value={summary}
              maxLength={1000}
              onChange={(event) => setSummary(event.target.value)}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="api-category">分类</Label>
              <Input
                id="api-category"
                value={category}
                maxLength={64}
                onChange={(event) => setCategory(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="api-status">状态</Label>
              <select
                id="api-status"
                className="h-9 rounded-md border bg-background px-3 text-sm"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                {[
                  ["trial", "试验池"],
                  ["healthy", "健康"],
                  ["published", "已发布"],
                  ["draft", "草稿"],
                  ["disabled", "已停用"],
                ].map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="api-source">来源说明</Label>
            <Input
              id="api-source"
              value={source}
              maxLength={255}
              onChange={(event) => setSource(event.target.value)}
            />
          </div>
          {updateMutation.isError && (
            <p className="text-sm text-destructive">
              元数据保存失败，请检查内容或稍后重试。
            </p>
          )}
          {updateMutation.isSuccess && (
            <p className="text-sm text-emerald-600">
              元数据已保存，并已写入管理审计。
            </p>
          )}
          <div className="flex gap-2">
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "保存中…" : "保存元数据"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setSelectedSlug(null)}
            >
              取消
            </Button>
          </div>
        </form>
      )}
    </AdminPageShell>
  )
}
