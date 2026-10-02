import type { ReactNode } from "react"

import PublicFooter from "./PublicFooter"
import PublicHeader from "./PublicHeader"

interface PublicLayoutProps {
  children: ReactNode
}

export function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="public-site flex min-h-svh flex-col">
      <PublicHeader />
      <main className="min-w-0 flex-1">{children}</main>
      <PublicFooter />
    </div>
  )
}

export default PublicLayout
