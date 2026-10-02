export type StaticCatalogRedistributionMode =
  | "self-operated"
  | "reference-only"
  | "link-only"

export type StaticCatalogDisplayStatus =
  | "candidate"
  | "verified-reference"
  | "self-operated-ready"

export type StaticCatalogAuthRequirement =
  | "none"
  | "optional"
  | "required"
  | "unknown"

export type StaticCatalogStability = "unknown" | "experimental" | "stable"

export interface StaticCatalogEntry {
  slug: string
  name: string
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
