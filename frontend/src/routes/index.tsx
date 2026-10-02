import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"

import { CatalogService } from "@/client"
import { formatUpdatedAt } from "@/components/ApiCatalog/catalog-types"
import PublicLayout from "@/components/PublicSite/PublicLayout"

export const Route = createFileRoute("/")({
  component: PublicHome,
  head: () => ({
    meta: [
      {
        title: "Yeyu API 公益工具箱",
      },
    ],
  }),
})

function CatalogPreview() {
  const catalogQuery = useQuery({
    queryKey: ["public-catalog-preview"],
    queryFn: async () => {
      const response = await CatalogService.searchCatalog({
        query: {
          page: 1,
          page_size: 4,
        },
      })
      return response.data
    },
  })

  const items = catalogQuery.data?.data ?? []

  return (
    <section
      id="catalog"
      className="public-section public-catalog-section"
      aria-labelledby="catalog-heading"
    >
      <div className="public-section-heading">
        <div>
          <p className="public-eyebrow">目录入口</p>
          <h2 id="catalog-heading" className="public-section-title">
            从真实目录开始
          </h2>
          <p className="public-section-copy">
            这里展示后端公开目录中的接口，不展示虚构卡片或调用统计。
          </p>
        </div>
        <Link className="public-text-link" to="/catalog" search={{ page: 1 }}>
          搜索完整目录 <span aria-hidden="true">→</span>
        </Link>
      </div>

      {catalogQuery.isPending ? (
        <p className="public-state" role="status">
          正在读取真实目录……
        </p>
      ) : null}

      {catalogQuery.isError ? (
        <div className="public-state public-state-error" role="alert">
          <p>目录暂时无法读取，请稍后重试。</p>
          <button
            type="button"
            className="public-inline-button"
            onClick={() => void catalogQuery.refetch()}
          >
            重试
          </button>
        </div>
      ) : null}

      {!catalogQuery.isPending &&
      !catalogQuery.isError &&
      items.length === 0 ? (
        <p className="public-state">当前没有可公开的接口，请稍后再来查看。</p>
      ) : null}

      {!catalogQuery.isPending && !catalogQuery.isError && items.length > 0 ? (
        <ul className="public-catalog-list" data-testid="catalog-preview-list">
          {items.map((item) => (
            <li key={item.slug} className="public-catalog-row">
              <div className="public-path-line">
                <span className="public-method-badge">{item.method}</span>
                <code>{item.path}</code>
              </div>
              <div className="min-w-0">
                <h3 className="truncate text-base font-semibold text-[var(--yeyu-ink)]">
                  <Link
                    to="/catalog/$slug"
                    params={{ slug: item.slug }}
                    className="public-catalog-title-link"
                  >
                    {item.name}
                  </Link>
                </h3>
                <p className="mt-1 text-sm text-[var(--yeyu-muted)]">
                  {item.summary}
                </p>
              </div>
              <div className="public-catalog-meta">
                <span>{item.category}</span>
                {item.is_free ? <span>免费</span> : null}
                <span>{item.status}</span>
                <time dateTime={item.updated_at ?? undefined}>
                  {formatUpdatedAt(item.updated_at)}
                </time>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

function PublicHome() {
  return (
    <PublicLayout>
      <div className="public-container">
        <section className="public-hero" aria-labelledby="home-heading">
          <div className="public-hero-copy">
            <p className="public-eyebrow">YEYU API / 公益工具箱</p>
            <h1 id="home-heading" className="public-hero-title">
              给学生和个人开发者的免费 API 工具箱
            </h1>
            <p className="public-hero-lede">
              从清楚的接口文档开始，按公开规范调用稳定、可核验的自营工具。
            </p>
            <form className="public-search-form" action="/catalog" method="get">
              <label className="sr-only" htmlFor="catalog-query">
                搜索 API 目录
              </label>
              <input
                id="catalog-query"
                name="query"
                className="public-search-input"
                placeholder="搜索时间、UUID 等公开接口……"
                type="search"
              />
              <button className="public-primary-button" type="submit">
                搜索 API 目录
              </button>
            </form>
            <nav className="public-hero-links" aria-label="快速入口">
              <a className="public-text-link" href="/catalog">
                浏览公开目录 <span aria-hidden="true">↗</span>
              </a>
              <a className="public-text-link" href="#usage">
                阅读使用规范 <span aria-hidden="true">↓</span>
              </a>
            </nav>
          </div>

          <aside
            className="public-boundary-note"
            aria-labelledby="boundary-heading"
          >
            <p className="public-eyebrow">调用边界</p>
            <h2 id="boundary-heading" className="public-note-title">
              先看清楚，再开始调用
            </h2>
            <p className="public-note-copy">
              公共页面只负责发现和阅读目录。真正的工具调用需要独立 API
              Key，浏览器登录状态不会替代它。
            </p>
            <div className="public-note-rule" aria-hidden="true" />
            <p className="public-note-label">示例凭据</p>
            <code className="public-code-chip">&lt;YOUR_API_KEY&gt;</code>
          </aside>
        </section>

        <CatalogPreview />

        <section
          id="usage"
          className="public-section public-usage-section"
          aria-labelledby="usage-heading"
        >
          <div>
            <p className="public-eyebrow">使用规范</p>
            <h2 id="usage-heading" className="public-section-title">
              公益服务也需要清楚的边界
            </h2>
          </div>
          <div className="public-usage-grid">
            <p>
              只调用目录中公开、已发布的接口；参数、缓存和来源以对应文档为准。
            </p>
            <p>
              请保管好自己的 API Key，不要把密钥提交到代码仓库或分享给他人。
            </p>
            <p>
              发现异常或文档问题时，请停止重试并通过项目渠道反馈，给公共资源留下余量。
            </p>
          </div>
        </section>

        <div className="public-bottom-cta">
          <p>准备好查找一个清楚、可用的接口了吗？</p>
          <Link className="public-primary-button" to="/login">
            登录并进入控制台
          </Link>
        </div>
      </div>
    </PublicLayout>
  )
}
