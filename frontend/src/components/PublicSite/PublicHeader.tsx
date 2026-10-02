import { Link } from "@tanstack/react-router"
import { Menu, X } from "lucide-react"
import { useState } from "react"

import { Logo } from "@/components/Common/Logo"
import { isLoggedIn } from "@/hooks/useAuth"

interface NavigationLinksProps {
  onNavigate?: () => void
}

function NavigationLinks({ onNavigate }: NavigationLinksProps) {
  const linkClassName =
    "public-nav-link rounded-md px-3 py-2 text-sm font-medium"

  return (
    <>
      <Link to="/" className={linkClassName} onClick={onNavigate}>
        首页
      </Link>
      <Link
        to="/catalog"
        search={{ page: 1 }}
        className={linkClassName}
        onClick={onNavigate}
      >
        API 目录
      </Link>
      <Link to="/" hash="usage" className={linkClassName} onClick={onNavigate}>
        使用规范
      </Link>
      {isLoggedIn() ? (
        <Link
          to="/dashboard"
          className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
          onClick={onNavigate}
        >
          控制台
        </Link>
      ) : (
        <Link
          to="/login"
          className="public-nav-link public-nav-link-primary rounded-md px-3 py-2 text-sm font-semibold"
          onClick={onNavigate}
        >
          登录
        </Link>
      )}
    </>
  )
}

export function PublicHeader() {
  const [menuOpen, setMenuOpen] = useState(true)
  const toggleMenu = () => setMenuOpen((open) => !open)
  const closeMenu = () => setMenuOpen(false)

  return (
    <header className="public-header">
      <div className="public-container public-header-inner">
        <Logo variant="full" className="h-8" />

        <nav aria-label="公共导航" className="public-nav">
          <div className="hidden items-center gap-1 md:flex">
            <NavigationLinks />
          </div>
          <button
            type="button"
            className="public-menu-button md:hidden"
            aria-controls="public-mobile-navigation"
            aria-expanded={menuOpen}
            aria-label={menuOpen ? "收起菜单" : "打开菜单"}
            onClick={toggleMenu}
          >
            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
          </button>
          {menuOpen ? (
            <div
              id="public-mobile-navigation"
              className="public-mobile-navigation md:hidden"
            >
              <NavigationLinks onNavigate={closeMenu} />
            </div>
          ) : null}
        </nav>
      </div>
    </header>
  )
}

export default PublicHeader
