import { Link } from "@tanstack/react-router"

export function PublicFooter() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="public-footer">
      <div className="public-container flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-semibold text-[var(--yeyu-ink)]">
            Yeyu API 公益平台
          </p>
          <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
            面向学生与个人开发者的公开工具目录 · {currentYear}
          </p>
        </div>
        <nav aria-label="页脚导航" className="flex flex-wrap gap-4 text-sm">
          <Link
            className="public-footer-link"
            to="/catalog"
            search={{ page: 1 }}
          >
            API 目录
          </Link>
          <Link className="public-footer-link" to="/" hash="usage">
            使用规范
          </Link>
          <Link className="public-footer-link" to="/login">
            登录
          </Link>
        </nav>
      </div>
    </footer>
  )
}

export default PublicFooter
