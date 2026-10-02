import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <>
        <span
          aria-hidden="true"
          className={cn(
            "inline-flex h-7 items-center gap-1.5 text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden",
            className,
          )}
        >
          <span className="logo-mark">Y</span>
          <span>Yeyu API</span>
        </span>
        <span
          aria-hidden="true"
          className={cn(
            "logo-mark hidden size-7 items-center justify-center text-sm group-data-[collapsible=icon]:inline-flex",
            className,
          )}
        >
          Y
        </span>
      </>
    ) : (
      <span
        aria-hidden="true"
        className={cn(
          "inline-flex items-center gap-2 text-lg font-semibold tracking-tight",
          className,
        )}
      >
        <span className="logo-mark">Y</span>
        {variant === "full" ? <span>Yeyu API</span> : null}
      </span>
    )

  if (!asLink) {
    return content
  }

  return (
    <Link to="/" aria-label="Yeyu API 首页" className="inline-flex">
      {content}
    </Link>
  )
}
