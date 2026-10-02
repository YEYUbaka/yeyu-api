import { expect, type Page, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

const timeItem = {
  slug: "time",
  name: "时间查询",
  summary: "按可选 IANA 时区返回当前 UTC、Unix 时间戳和本地时间。",
  category: "tools",
  method: "GET",
  path: "/v1/tools/time",
  auth_type: "api_key",
  is_free: true,
  status: "published",
  updated_at: "2026-10-02T00:00:00Z",
}

const uuidItem = {
  slug: "uuid",
  name: "UUID v4 生成器",
  summary: "生成一个随机 UUID v4，不接受任何查询参数。",
  category: "tools",
  method: "GET",
  path: "/v1/tools/uuid",
  auth_type: "api_key",
  is_free: true,
  status: "published",
  updated_at: "2026-10-02T00:00:00Z",
}

const timeDetail = {
  ...timeItem,
  auth: { type: "api_key", header: "X-API-Key" },
  parameters: [
    {
      name: "timezone",
      in: "query",
      required: false,
      description: "可选的 IANA 时区名称，省略时使用 UTC。",
      schema: {
        type: "string",
        default: "UTC",
        examples: ["UTC", "Asia/Shanghai"],
      },
    },
  ],
  response_schema: {
    type: "object",
    properties: {
      utc: { type: "string", format: "date-time" },
      unix_timestamp: { type: "number" },
      timezone: { type: "string" },
      local: { type: "string", format: "date-time" },
    },
    required: ["utc", "unix_timestamp", "timezone", "local"],
  },
  errors: [
    {
      status: 401,
      code: "API_KEY_REQUIRED",
      description: "请求必须提供 X-API-Key。",
    },
    { status: 404, code: "API_NOT_FOUND", description: "接口不存在或未公开。" },
  ],
  examples: [
    {
      language: "curl",
      request:
        'curl -G https://api.yeyubaka.top/v1/tools/time -H "X-API-Key: <YOUR_API_KEY>" --data-urlencode "timezone=Asia/Shanghai"',
    },
  ],
  source: "Yeyu API",
  cache_rules: { cacheable: false, ttl_seconds: 0, stale_if_error: false },
}

type CatalogPage = {
  data: (typeof timeItem)[]
  count: number
  page: number
  page_size: number
}

async function mockCatalogApi(page: Page) {
  await page.route("**/api/v1/catalog*", async (route) => {
    const url = new URL(route.request().url())

    if (url.pathname.endsWith("/time")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(timeDetail),
      })
      return
    }

    const query = url.searchParams.get("query") ?? ""
    const category = url.searchParams.get("category")
    const status = url.searchParams.get("status")
    const data =
      query === "missing"
        ? []
        : query === "uuid"
          ? [uuidItem]
          : [timeItem, uuidItem]
    const filtered = data.filter(
      (item) =>
        (!category || item.category === category) &&
        (!status || item.status === status),
    )
    const response: CatalogPage = {
      data: filtered,
      count: filtered.length,
      page: 1,
      page_size: 20,
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(response),
    })
  })
}

test("Anonymous users can browse the real public catalog", async ({ page }) => {
  await mockCatalogApi(page)
  await page.goto("/catalog")

  await expect(page).toHaveURL("/catalog")
  await expect(page.getByRole("heading", { name: "API 目录" })).toBeVisible()
  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
  await expect(page.getByTestId("catalog-card-time")).toContainText(
    "/v1/tools/time",
  )
  await expect(page.getByText("免费", { exact: true }).first()).toBeVisible()
  await expect(
    page.getByText("published", { exact: true }).first(),
  ).toBeVisible()
  await expect(page.getByRole("link", { name: /时间查询/ })).toHaveAttribute(
    "href",
    "/catalog/time",
  )
})

test("Catalog search is debounced and filters are shareable in the URL", async ({
  page,
}) => {
  const catalogRequests: string[] = []
  await page.route("**/api/v1/catalog*", async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith("/time")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(timeDetail),
      })
      return
    }
    catalogRequests.push(url.search)
    const item = url.searchParams.get("query") === "uuid" ? uuidItem : timeItem
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [item], count: 1, page: 1, page_size: 20 }),
    })
  })

  await page.goto("/catalog")
  const searchInput = page.getByRole("searchbox", { name: "搜索公开 API" })
  await searchInput.fill("uuid")
  await page.waitForTimeout(150)
  expect(
    catalogRequests.filter((request) => request.includes("query=uuid")),
  ).toHaveLength(0)
  await expect(page).toHaveURL(/\/catalog\?query=uuid$/)
  await expect(page.getByTestId("catalog-card-uuid")).toBeVisible()

  await page.getByLabel("分类").selectOption("tools")
  await expect(page).toHaveURL(/query=uuid.*category=tools/)
  await page.getByLabel("状态").selectOption("published")
  await expect(page).toHaveURL(/query=uuid.*category=tools.*status=published/)
})

test("Catalog displays an explicit empty state for an empty result", async ({
  page,
}) => {
  await mockCatalogApi(page)
  await page.goto("/catalog?query=missing")

  await expect(page.getByTestId("catalog-empty")).toBeVisible()
  await expect(page.getByText("没有找到匹配的公开接口")).toBeVisible()
  await expect(page.getByTestId("catalog-grid")).not.toBeVisible()
})

test("Time detail documents the request contract and safe code examples", async ({
  page,
}) => {
  await mockCatalogApi(page)
  await page.goto("/catalog/time")

  await expect(page).toHaveURL("/catalog/time")
  await expect(page.getByRole("heading", { name: "时间查询" })).toBeVisible()
  await expect(page.getByText("/v1/tools/time", { exact: true })).toBeVisible()
  await expect(page.getByText("GET", { exact: true }).first()).toBeVisible()
  await expect(
    page.getByText("API Key", { exact: false }).first(),
  ).toBeVisible()
  await expect(page.getByText("timezone", { exact: true })).toBeVisible()
  await expect(page.getByText("utc", { exact: true })).toBeVisible()
  await expect(page.getByText("unix_timestamp", { exact: true })).toBeVisible()
  await expect(
    page.getByText("API_KEY_REQUIRED", { exact: true }),
  ).toBeVisible()
  await expect(page.getByText("Yeyu API", { exact: true })).toBeVisible()
  await expect(page.getByRole("heading", { name: "curl" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "JavaScript" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Python" })).toBeVisible()
  await expect(
    page.locator("code").filter({ hasText: "<YOUR_API_KEY>" }).first(),
  ).toBeVisible()
  await expect(
    page.locator("code").filter({ hasText: "api.yeyubaka.top" }).first(),
  ).toBeVisible()

  const copyButton = page.getByRole("button", { name: "复制 curl 示例" })
  await expect(copyButton).toBeVisible()
  await copyButton.click()
  await expect(copyButton).toContainText("已复制")
})

test("Public navigation remains keyboard accessible on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mockCatalogApi(page)
  await page.goto("/")

  const navigation = page.getByRole("navigation", { name: "公共导航" })
  const menuButton = navigation.getByRole("button", { name: /菜单/ })

  await expect(navigation).toBeVisible()
  await expect(menuButton).toHaveAttribute("aria-expanded", "true")

  await menuButton.press("Enter")
  await expect(menuButton).toHaveAttribute("aria-expanded", "false")

  await menuButton.press("Space")
  await expect(menuButton).toHaveAttribute("aria-expanded", "true")
  await expect(navigation.getByRole("link", { name: "API 目录" })).toBeVisible()
  await expect(navigation.getByRole("link", { name: "登录" })).toBeVisible()
})
