import { useMemo, useState } from "react"

import rawCatalogData from "./data.json"
import StaticCatalogCard from "./StaticCatalogCard"
import StaticCatalogFilters from "./StaticCatalogFilters"
import "./static-catalog.css"
import type { StaticCatalogEntry } from "./types"

const catalogData = rawCatalogData as StaticCatalogEntry[]
const ALL_CATEGORIES = "全部资料"

interface StaticCatalogAppProps {
  entries?: ReadonlyArray<StaticCatalogEntry>
}

function StaticLogo() {
  return (
    <a
      className="static-catalog-logo"
      href="/"
      aria-label="Yeyu API 免费 API 资料册首页"
    >
      <span className="logo-mark" aria-hidden="true">
        Y
      </span>
      <span>Yeyu API</span>
    </a>
  )
}

export function StaticCatalogApp({
  entries = catalogData,
}: StaticCatalogAppProps) {
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState(ALL_CATEGORIES)
  const categories = useMemo(
    () => [
      ALL_CATEGORIES,
      ...Array.from(new Set(entries.map((entry) => entry.category))).sort(
        (left, right) => left.localeCompare(right, "zh-CN"),
      ),
    ],
    [entries],
  )
  const filteredEntries = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("zh-CN")
    return entries.filter((entry) => {
      const matchesCategory =
        category === ALL_CATEGORIES || entry.category === category
      if (!matchesCategory) return false
      if (!normalizedQuery) return true
      return [entry.name, entry.summary, entry.category, entry.slug].some(
        (value) => value.toLocaleLowerCase("zh-CN").includes(normalizedQuery),
      )
    })
  }, [category, entries, query])

  return (
    <div className="static-catalog-site">
      <header className="static-catalog-header">
        <div className="static-catalog-container static-catalog-header-inner">
          <StaticLogo />
          <div className="static-catalog-header-note">
            <span className="static-signal-dot" aria-hidden="true" />
            资料汇总 · 不做代理调用
          </div>
        </div>
      </header>

      <main>
        <section className="static-catalog-hero">
          <div className="static-catalog-container">
            <div className="static-catalog-kicker">
              <span>FREE API FIELD GUIDE</span>
              <span>2026.10</span>
            </div>
            <div className="static-catalog-hero-grid">
              <div>
                <h1>
                  免费 API
                  <br />
                  <em>资料册</em>
                </h1>
                <p className="static-catalog-lede">
                  给学生和个人开发者的一张清楚地图：先看来源、条款和状态，再决定要不要接入。
                </p>
              </div>
              <aside className="static-catalog-note">
                <span className="static-note-label">阅读原则</span>
                <p>
                  这里整理公开资料，不把“免费”写成“无限”，也不把第三方接口伪装成
                  Yeyu 服务。
                </p>
                <span className="static-note-rule">
                  SOURCE / TERMS / STATUS
                </span>
              </aside>
            </div>

            <search className="static-catalog-search">
              <form onSubmit={(event) => event.preventDefault()}>
                <label htmlFor="static-catalog-search-input">
                  搜索免费 API 资料
                </label>
                <div className="static-search-control">
                  <span className="static-search-glyph" aria-hidden="true">
                    /
                  </span>
                  <input
                    id="static-catalog-search-input"
                    name="query"
                    placeholder="搜索天气、汇率、UUID……"
                    type="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                  <span className="static-search-hint" aria-hidden="true">
                    {query ? "清晰筛选" : "本地搜索"}
                  </span>
                </div>
              </form>
            </search>
          </div>
        </section>

        <section
          className="static-catalog-content"
          aria-labelledby="catalog-heading"
        >
          <div className="static-catalog-container">
            <div className="static-catalog-toolbar">
              <div>
                <p className="static-catalog-eyebrow">CATALOG / 目录</p>
                <h2 id="catalog-heading">公开接口资料</h2>
              </div>
              <p className="static-catalog-count">
                显示 {filteredEntries.length} / {entries.length} 条
              </p>
            </div>

            <StaticCatalogFilters
              categories={categories}
              selectedCategory={category}
              onSelect={setCategory}
            />

            {filteredEntries.length > 0 ? (
              <div className="static-catalog-list">
                {filteredEntries.map((entry) => (
                  <StaticCatalogCard entry={entry} key={entry.slug} />
                ))}
              </div>
            ) : (
              <div className="static-catalog-empty" role="status">
                <span className="static-empty-mark" aria-hidden="true">
                  ∅
                </span>
                <p>没有找到匹配资料。</p>
                <button
                  type="button"
                  onClick={() => {
                    setQuery("")
                    setCategory(ALL_CATEGORIES)
                  }}
                >
                  清除筛选
                </button>
              </div>
            )}

            <div className="static-catalog-disclaimer">
              <span className="static-disclaimer-mark">NOTE</span>
              <p>
                免费额度、服务条款和再分发权限会变化。每条资料都保留核验日期；真正调用前，请阅读官方文档和最新条款。
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="static-catalog-footer">
        <div className="static-catalog-container static-footer-inner">
          <span>Yeyu API 公益资料册</span>
          <span>面向学生与个人开发者 · 不提供开放代理</span>
        </div>
      </footer>
    </div>
  )
}

export default StaticCatalogApp
