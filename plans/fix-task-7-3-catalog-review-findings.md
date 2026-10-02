# Task 7-3 Catalog Review Findings Fix Plan

> **For agentic workers:** Execute this plan in the current `E:\AI_projects\yeyu-api` worktree. Keep the existing public shell and generated route tree unchanged.

**Goal:** Close the five Important findings from the Task 7-3 read-only review with the smallest safe frontend changes and focused regression coverage.

**Architecture:** Keep catalog state in TanStack Router search params. Add pure path and metadata guards in `catalog-types.ts`, use those guards at every detail rendering boundary, and keep pagination as a focused `CatalogPagination` component. Make the detail route render exactly one loading, error, or success state.

**Tech Stack:** React, TypeScript, TanStack Router, TanStack Query, generated `CatalogService`, Playwright route mocks, Biome.

## Global Constraints

- Modify only the Task 7-3 frontend catalog files, focused catalog tests, this plan, and the Task 7-3 report.
- Do not edit `frontend\src\routeTree.gen.ts`, Task 2 authentication/public shell behavior, backend, online services, DNS, Nginx, or credentials.
- Use `https://api.yeyubaka.top` only as the controlled public API base in generated examples.
- Retain `<YOUR_API_KEY>` and use `<NON_SECRET_TEST_VALUE>` for any sensitive-looking test value.
- Write or update regression tests before implementation; do not run long Playwright or build commands.

### Task 1: Add failing regression coverage

**Files:**
- Modify: `E:\AI_projects\yeyu-api\frontend\tests\public-catalog.spec.ts`

- [ ] Replace the broad catalog glob with separate regular expressions for `/api/v1/catalog` list URLs with optional query strings and `/api/v1/catalog/time` detail URLs.
- [ ] Add route-mocked assertions for page 2 and page 1 navigation while retaining `query`, `category`, and `status`.
- [ ] Add route-mocked detail data containing an unsafe absolute path and sensitive nested keys, then assert the unsafe host and `<NON_SECRET_TEST_VALUE>` are absent from rendered examples/metadata.
- [ ] Add a stale-detail failure flow that asserts the detail error state does not render the previous detail heading.
- [ ] Run only the permitted short static check on the updated test file; do not run Playwright.

### Task 2: Harden detail path and metadata boundaries

**Files:**
- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\ApiDetailView.tsx`

**Interfaces:**
- `normalizeInternalApiPath(value: unknown): string | undefined` trims and accepts only a single-slash internal path without `http(s)`, `//`, backslash, query/hash, percent encoding, or `..`.
- `sanitizeMetadata(value: unknown): unknown` recursively removes object keys whose normalized lowercase form contains `token`, `secret`, `password`, `authorization`, `cookie`, `apikey`, `credential`, `privatekey`, or `providerref`.
- `formatMetadata` sanitizes before JSON formatting; `responseProperties`, parameter display/examples, error display, and cache display consume sanitized values.

- [ ] Implement the two pure guards in `catalog-types.ts` without changing generated client types.
- [ ] Build curl, JavaScript, and Python snippets from the controlled base plus the normalized path; render `路径不可用` and a non-URL message when the backend path is rejected.
- [ ] Keep `<YOUR_API_KEY>` unchanged and do not add arbitrary URL input or credential reads.

### Task 3: Add legal page state and mutually exclusive detail states

**Files:**
- Modify: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\catalog-types.ts`
- Create: `E:\AI_projects\yeyu-api\frontend\src\components\ApiCatalog\CatalogPagination.tsx`
- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\index.tsx`
- Modify: `E:\AI_projects\yeyu-api\frontend\src\routes\catalog\$slug.tsx`

- [ ] Add `page: number` to parsed search state, normalize only positive safe integers, and default invalid/missing input to 1.
- [ ] Include `page` in the query key and send `page` plus `page_size: 20` to `CatalogService.searchCatalog`.
- [ ] Reset `page` to 1 on debounced query changes and category/status changes while preserving the other search params.
- [ ] Render accessible previous/next controls using `count` and `page_size`; disable controls at boundaries and while fetching.
- [ ] Render detail loading, error, and success as an exclusive branch so stale detail data is hidden when `isError` is true.

### Task 4: Verify and record evidence

**Files:**
- Modify: `E:\AI_projects\yeyu-api\plans\agent-reports\task-7-3-report.md`

- [ ] Run targeted Biome on every changed frontend source/test file and record the real exit code/output.
- [ ] Run `git diff --check` and record the real result, including any non-failure line-ending warning.
- [ ] Do not claim Playwright, build, backend tests, route generation, or browser acceptance unless actually run; record them as unverified.
- [ ] Inspect the final diff and status, append the five fixes and evidence to the report, then commit with `fix: close catalog review findings`.
