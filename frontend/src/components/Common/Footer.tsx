import { Link } from "@tanstack/react-router"

export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t py-4 px-6">
      <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
        <p className="text-muted-foreground text-sm">
          Yeyu API 公益平台 - {currentYear}
        </p>
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            返回公共首页
          </Link>
          <Link
            to="/"
            hash="usage"
            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            使用规范
          </Link>
        </div>
      </div>
    </footer>
  )
}
