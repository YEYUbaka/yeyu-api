import { readFile } from "node:fs/promises"
import { fileURLToPath } from "node:url"

const dataPath = fileURLToPath(
  new URL("../src/staticCatalog/data.json", import.meta.url),
)

const allowedRedistributionModes = new Set([
  "self-operated",
  "reference-only",
  "link-only",
])
const allowedOwnershipValues = new Set(["yeyu", "third-party"])
const allowedDisplayStatuses = new Set([
  "candidate",
  "verified-reference",
  "self-operated-ready",
])
const allowedAuthRequirements = new Set([
  "none",
  "optional",
  "required",
  "unknown",
])
const allowedStabilityValues = new Set(["unknown", "experimental", "stable"])
const sensitiveKeyPattern =
  /(api[-_]?key|token|secret|password|authorization|cookie|private[-_]?key|credential)/i
const sensitiveValuePattern =
  /(bearer\s+[a-z0-9._-]+|-----begin|sk-[a-z0-9_-]{12,}|eyj[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+)/i

function fail(message) {
  console.error(`Static catalog validation failed: ${message}`)
  process.exitCode = 1
}

function isHttpsUrl(value) {
  try {
    return new URL(value).protocol === "https:"
  } catch {
    return false
  }
}

function inspectSensitiveValues(value, path = "entry") {
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      inspectSensitiveValues(item, `${path}[${index}]`)
    })
    return
  }

  if (value && typeof value === "object") {
    for (const [key, nestedValue] of Object.entries(value)) {
      if (sensitiveKeyPattern.test(key)) {
        fail(`${path}.${key} uses a sensitive field name`)
      }
      inspectSensitiveValues(nestedValue, `${path}.${key}`)
    }
    return
  }

  if (typeof value === "string" && sensitiveValuePattern.test(value)) {
    fail(`${path} contains a credential-like value`)
  }
}

let raw
try {
  raw = await readFile(dataPath, "utf8")
} catch (error) {
  fail(`cannot read ${dataPath}: ${error.message}`)
  process.exit(1)
}

let entries
try {
  entries = JSON.parse(raw)
} catch (error) {
  fail(`data is not valid JSON: ${error.message}`)
  process.exit(1)
}

if (!Array.isArray(entries) || entries.length === 0) {
  fail("data must be a non-empty array")
}

const requiredFields = [
  "slug",
  "name",
  "providerName",
  "ownership",
  "category",
  "summary",
  "sourceUrl",
  "officialDocsUrl",
  "licenseStatus",
  "redistributionMode",
  "freeTier",
  "authRequired",
  "stability",
  "updatedAt",
  "displayStatus",
]
const slugs = new Set()

for (const [index, entry] of (Array.isArray(entries)
  ? entries
  : []
).entries()) {
  const path = `entries[${index}]`
  if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
    fail(`${path} must be an object`)
    continue
  }

  for (const field of requiredFields) {
    if (typeof entry[field] !== "string" || entry[field].trim() === "") {
      fail(`${path}.${field} must be a non-empty string`)
    }
  }

  if (typeof entry.slug === "string") {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(entry.slug)) {
      fail(`${path}.slug must be kebab-case`)
    }
    if (slugs.has(entry.slug)) fail(`${path}.slug is duplicated: ${entry.slug}`)
    slugs.add(entry.slug)
  }

  for (const field of ["sourceUrl", "officialDocsUrl"]) {
    if (typeof entry[field] === "string" && !isHttpsUrl(entry[field])) {
      fail(`${path}.${field} must be an HTTPS URL`)
    }
  }

  if (!allowedRedistributionModes.has(entry.redistributionMode)) {
    fail(`${path}.redistributionMode is unsupported`)
  }
  if (!allowedOwnershipValues.has(entry.ownership)) {
    fail(`${path}.ownership is unsupported`)
  }
  if (!allowedDisplayStatuses.has(entry.displayStatus)) {
    fail(`${path}.displayStatus is unsupported`)
  }
  if (entry.ownership === "yeyu") {
    if (entry.redistributionMode !== "self-operated") {
      fail(`${path} Yeyu entries must use self-operated redistributionMode`)
    }
    if (entry.displayStatus !== "self-operated-ready") {
      fail(`${path} Yeyu entries must use self-operated-ready displayStatus`)
    }
  }
  if (entry.ownership === "third-party") {
    if (entry.redistributionMode === "self-operated") {
      fail(
        `${path} third-party entries cannot use self-operated redistributionMode`,
      )
    }
    if (entry.displayStatus === "self-operated-ready") {
      fail(
        `${path} third-party entries cannot use self-operated-ready displayStatus`,
      )
    }
  }
  if (!allowedAuthRequirements.has(entry.authRequired)) {
    fail(`${path}.authRequired is unsupported`)
  }
  if (!allowedStabilityValues.has(entry.stability)) {
    fail(`${path}.stability is unsupported`)
  }
  if (
    typeof entry.updatedAt === "string" &&
    Number.isNaN(Date.parse(entry.updatedAt))
  ) {
    fail(`${path}.updatedAt must be an ISO-compatible date`)
  }

  inspectSensitiveValues(entry, path)
}

if (process.exitCode) process.exit(1)
console.log(`Static catalog validation passed: ${entries.length} entries`)
