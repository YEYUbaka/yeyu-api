export type StaticCatalogRedistributionMode = "reference-only" | "link-only"

export type StaticCatalogOwnership = "third-party"

export type StaticCatalogDisplayStatus = "candidate" | "verified-reference"

export type StaticCatalogAuthRequirement =
  | "none"
  | "optional"
  | "required"
  | "unknown"

export type StaticCatalogStability = "unknown" | "experimental" | "stable"

export interface StaticCatalogEntry {
  slug: string
  name: string
  providerName: string
  ownership: StaticCatalogOwnership
  category: string
  summary: string
  sourceUrl: string
  officialDocsUrl: string
  licenseStatus: string
  redistributionMode: StaticCatalogRedistributionMode
  freeTier: string
  authRequired: StaticCatalogAuthRequirement
  stability: StaticCatalogStability
  updatedAt: string
  displayStatus: StaticCatalogDisplayStatus
}
