import { Link } from "@tanstack/react-router"
import type { ReactNode } from "react"

const adminLinks = [
  { to: "/admin", label: "用户" },
  { to: "/admin-apis", label: "接口元数据" },
  { to: "/admin-trial-pool", label: "候选试验池" },
  { to: "/admin-policies", label: "限额策略" },
  { to: "/admin-health", label: "健康状态" },
  { to: "/admin-audit", label: "审计记录" },
] as const

export function AdminPageShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-6" data-testid="admin-workspace">
      <nav
        aria-label="管理端导航"
        className="flex flex-wrap gap-2 border-b pb-3 text-sm"
      >
        {adminLinks.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            activeProps={{
              className:
                "rounded-md bg-primary px-3 py-1.5 text-primary-foreground",
            }}
            inactiveProps={{
              className:
                "rounded-md px-3 py-1.5 text-muted-foreground hover:bg-muted hover:text-foreground",
            }}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  )
}

export default AdminPageShell
