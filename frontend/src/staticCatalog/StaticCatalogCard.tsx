import type { StaticCatalogEntry } from "./types"

interface StaticCatalogCardProps {
  entry: StaticCatalogEntry
}

const redistributionLabels: Record<
  StaticCatalogEntry["redistributionMode"],
  string
> = {
  "reference-only": "资料汇总",
  "link-only": "官方链接",
}

const authLabels: Record<StaticCatalogEntry["authRequired"], string> = {
  none: "无需账号",
  optional: "可能需要 Key",
  required: "需要 Key",
  unknown: "鉴权待核验",
}

const stabilityLabels: Record<StaticCatalogEntry["stability"], string> = {
  unknown: "稳定性待核验",
  experimental: "本地候选",
  stable: "稳定资料",
}

const displayStatusLabels: Record<StaticCatalogEntry["displayStatus"], string> =
  {
    candidate: "待核验",
    "verified-reference": "来源已核验",
  }

export function StaticCatalogCard({ entry }: StaticCatalogCardProps) {
  return (
    <article
      className="static-catalog-entry"
      data-testid="static-catalog-entry"
      data-mode={entry.redistributionMode}
    >
      <div className="static-entry-rail" aria-hidden="true">
        <span className="static-entry-marker">◆</span>
        <span className="static-entry-rail-line" />
      </div>
      <div className="static-entry-body">
        <div className="static-entry-meta">
          <span className="static-entry-category">{entry.category}</span>
          <span className="static-entry-status">
            {redistributionLabels[entry.redistributionMode]}
          </span>
        </div>
        <div className="static-entry-heading">
          <div>
            <h2>{entry.name}</h2>
            <p>{entry.summary}</p>
          </div>
          <span className="static-entry-stamp">
            {displayStatusLabels[entry.displayStatus]}
          </span>
        </div>
        <dl className="static-entry-facts">
          <div>
            <dt>免费情况</dt>
            <dd>{entry.freeTier}</dd>
          </div>
          <div>
            <dt>鉴权</dt>
            <dd>{authLabels[entry.authRequired]}</dd>
          </div>
          <div>
            <dt>稳定性</dt>
            <dd>{stabilityLabels[entry.stability]}</dd>
          </div>
          <div>
            <dt>协议/再分发</dt>
            <dd>{entry.licenseStatus}</dd>
          </div>
          <div>
            <dt>核验时间</dt>
            <dd>{entry.updatedAt}</dd>
          </div>
        </dl>
        <div className="static-entry-links">
          <a
            href={entry.officialDocsUrl}
            rel="noopener noreferrer"
            target="_blank"
          >
            打开 {entry.providerName} 官方文档 <span aria-hidden="true">↗</span>
          </a>
          <a href={entry.sourceUrl} rel="noopener noreferrer" target="_blank">
            查看来源 <span aria-hidden="true">↗</span>
          </a>
        </div>
      </div>
    </article>
  )
}

export default StaticCatalogCard
