import { createFileRoute } from "@tanstack/react-router"

import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/dashboard")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Yeyu API 控制台",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const displayName = currentUser?.full_name || currentUser?.email || "开发者"

  return (
    <section className="flex flex-col gap-3" data-testid="dashboard-page">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">
        Yeyu API / 控制台
      </p>
      <h1 className="max-w-2xl truncate text-3xl font-semibold tracking-tight">
        Yeyu API 控制台
      </h1>
      <p className="text-lg text-muted-foreground">你好，{displayName}。</p>
      <p className="max-w-2xl text-muted-foreground">
        在这里管理你的账户、API Key 和调用设置。公共目录仍然可以从站点首页查看。
      </p>
    </section>
  )
}
