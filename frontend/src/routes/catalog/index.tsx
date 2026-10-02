import { createFileRoute, Link } from "@tanstack/react-router"

import PublicLayout from "@/components/PublicSite/PublicLayout"

export const Route = createFileRoute("/catalog/")({
  component: CatalogPlaceholder,
  head: () => ({
    meta: [
      {
        title: "API 目录 - Yeyu API",
      },
    ],
  }),
})

function CatalogPlaceholder() {
  return (
    <PublicLayout>
      <div className="public-container py-16 sm:py-24">
        <section
          className="public-state mx-auto max-w-2xl text-center"
          aria-labelledby="catalog-placeholder-heading"
          data-testid="catalog-placeholder"
        >
          <p className="public-eyebrow">公开目录</p>
          <h1
            id="catalog-placeholder-heading"
            className="public-section-title mt-3"
          >
            API 目录建设中
          </h1>
          <p className="public-section-copy mx-auto mt-4 max-w-xl">
            由公开目录驱动的真实接口条目将在下一阶段开放，当前先保留清晰的公共入口。
          </p>
          <p className="mt-3 text-sm text-[var(--yeyu-muted)]">
            目录建设中，请稍后再来查看。
          </p>
          <Link to="/" className="public-primary-button mt-8 inline-flex">
            返回首页
          </Link>
        </section>
      </div>
    </PublicLayout>
  )
}
