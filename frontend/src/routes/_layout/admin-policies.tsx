import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import { AdminCatalogService, AdminPoliciesService } from "@/client"
import AdminPageShell from "@/components/Admin/AdminPageShell"
import { requireAdmin } from "@/components/Admin/requireAdmin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export const Route = createFileRoute("/_layout/admin-policies")({
  component: AdminPolicies,
  beforeLoad: requireAdmin,
  head: () => ({
    meta: [{ title: "限额策略 - Yeyu API" }],
  }),
})

function AdminPolicies() {
  const queryClient = useQueryClient()
  const catalogQuery = useQuery({
    queryKey: ["admin-catalog-for-policies"],
    queryFn: async () =>
      (
        await AdminCatalogService.catalogReadAdminCatalog({
          query: { page: 1, page_size: 100 },
        })
      ).data,
  })
  const [selectedSlug, setSelectedSlug] = useState("")
  const [minuteLimit, setMinuteLimit] = useState("60")
  const [ipMinuteLimit, setIpMinuteLimit] = useState("60")
  const [dailyLimit, setDailyLimit] = useState("1000")
  const [concurrencyLimit, setConcurrencyLimit] = useState("1")
  const [weight, setWeight] = useState("1")

  useEffect(() => {
    if (!selectedSlug && catalogQuery.data?.data[0]) {
      setSelectedSlug(catalogQuery.data.data[0].slug)
    }
  }, [catalogQuery.data, selectedSlug])

  const policyQuery = useQuery({
    enabled: Boolean(selectedSlug),
    queryKey: ["admin-policy", selectedSlug],
    queryFn: async () =>
      (
        await AdminPoliciesService.policiesGetPolicy({
          path: { api_slug: selectedSlug },
        })
      ).data,
  })

  useEffect(() => {
    if (!policyQuery.data) return
    setMinuteLimit(String(policyQuery.data.minute_limit))
    setIpMinuteLimit(String(policyQuery.data.ip_minute_limit))
    setDailyLimit(String(policyQuery.data.daily_limit))
    setConcurrencyLimit(String(policyQuery.data.concurrency_limit))
    setWeight(String(policyQuery.data.weight))
  }, [policyQuery.data])

  const mutation = useMutation({
    mutationFn: async () =>
      (
        await AdminPoliciesService.policiesUpdatePolicy({
          path: { api_slug: selectedSlug },
          body: {
            minute_limit: Number(minuteLimit),
            ip_minute_limit: Number(ipMinuteLimit),
            daily_limit: Number(dailyLimit),
            concurrency_limit: Number(concurrencyLimit),
            weight: Number(weight),
          },
        })
      ).data,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["admin-policy", selectedSlug],
      })
    },
  })

  return (
    <AdminPageShell>
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
          管理端 / 限额策略
        </p>
        <h1 className="mt-2 text-2xl font-semibold">限额策略</h1>
        <p className="mt-2 text-muted-foreground">
          每日额度、分钟限频、IP 限频和并发上限均为服务端策略；页面提交不会绕过
          API Key 鉴权。
        </p>
      </header>
      {catalogQuery.isPending && (
        <p className="text-muted-foreground">正在读取接口目录…</p>
      )}
      {catalogQuery.isError && (
        <p className="text-destructive">接口目录暂时无法读取，请稍后重试。</p>
      )}
      {catalogQuery.data && (
        <form
          className="grid max-w-2xl gap-5 rounded-xl border p-6"
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate()
          }}
          data-testid="admin-policy-form"
        >
          <div className="grid gap-2">
            <Label htmlFor="policy-api">接口</Label>
            <select
              id="policy-api"
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={selectedSlug}
              onChange={(event) => setSelectedSlug(event.target.value)}
            >
              {catalogQuery.data.data.map((api) => (
                <option key={api.id} value={api.slug}>
                  {api.name} ({api.slug})
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="minute-limit">每分钟账号限额</Label>
              <Input
                id="minute-limit"
                min="0"
                type="number"
                value={minuteLimit}
                onChange={(event) => setMinuteLimit(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ip-minute-limit">每分钟 IP 限额</Label>
              <Input
                id="ip-minute-limit"
                min="0"
                type="number"
                value={ipMinuteLimit}
                onChange={(event) => setIpMinuteLimit(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="daily-limit">每日额度</Label>
              <Input
                id="daily-limit"
                min="0"
                type="number"
                value={dailyLimit}
                onChange={(event) => setDailyLimit(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="concurrency-limit">并发上限</Label>
              <Input
                id="concurrency-limit"
                min="1"
                type="number"
                value={concurrencyLimit}
                onChange={(event) => setConcurrencyLimit(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="weight">接口权重</Label>
              <Input
                id="weight"
                min="1"
                type="number"
                value={weight}
                onChange={(event) => setWeight(event.target.value)}
              />
            </div>
          </div>
          {mutation.isError && (
            <p className="text-sm text-destructive">
              策略保存失败，请检查输入或稍后重试。
            </p>
          )}
          {mutation.isSuccess && (
            <p className="text-sm text-emerald-600">
              策略已保存，并已写入管理审计。
            </p>
          )}
          <Button type="submit" disabled={!selectedSlug || mutation.isPending}>
            {mutation.isPending ? "保存中…" : "保存策略"}
          </Button>
        </form>
      )}
    </AdminPageShell>
  )
}
