import { expect, test } from "@playwright/test"

function expectSameOriginRequests(
  requestUrls: readonly string[],
  baseURL: string | undefined,
) {
  const expectedOrigin = new URL(baseURL ?? "http://127.0.0.1:4174").origin

  expect(requestUrls.length).toBeGreaterThan(0)
  for (const requestUrl of requestUrls) {
    expect(new URL(requestUrl).origin).toBe(expectedOrigin)
  }
}

test.describe("static API catalog", () => {
  test("renders reviewed entries without backend requests", async ({
    page,
    baseURL,
  }) => {
    const requests: string[] = []
    page.on("request", (request) => requests.push(request.url()))

    await page.goto("/")

    await expect(
      page.getByRole("heading", { name: "免费 API 资料册" }),
    ).toBeVisible()
    await expect(page.getByTestId("static-catalog-entry")).toHaveCount(6)
    await expect(page.getByText("Open-Meteo 天气与空气质量")).toBeVisible()
    await expect(page.getByText("仅资料汇总").first()).toBeVisible()

    await page.waitForTimeout(250)
    expectSameOriginRequests(requests, baseURL)
  })

  test("searches entries locally", async ({ page }) => {
    await page.goto("/")

    await page
      .getByRole("searchbox", { name: "搜索免费 API 资料" })
      .fill("天气")

    await expect(page.getByTestId("static-catalog-entry")).toHaveCount(1)
    await expect(page.getByText("Open-Meteo 天气与空气质量")).toBeVisible()
  })

  test("explains an empty local result", async ({ page }) => {
    await page.goto("/")

    await page
      .getByRole("searchbox", { name: "搜索免费 API 资料" })
      .fill("不存在的接口")

    await expect(page.getByTestId("static-catalog-entry")).toHaveCount(0)
    await expect(page.getByRole("status")).toContainText("没有找到匹配资料")
  })

  test("keeps search and category filtering local", async ({
    page,
    baseURL,
  }) => {
    const requests: string[] = []
    page.on("request", (request) => requests.push(request.url()))

    await page.goto("/")
    await page
      .getByRole("searchbox", { name: "搜索免费 API 资料" })
      .fill("天气")
    await page.getByRole("button", { name: "生活与公共数据" }).click()
    await expect(page.getByTestId("static-catalog-entry")).toHaveCount(1)

    await page.waitForTimeout(250)
    expectSameOriginRequests(requests, baseURL)
  })

  test("filters by category and keeps official links explicit", async ({
    page,
  }) => {
    await page.goto("/")

    await page.getByRole("button", { name: "生活与公共数据" }).click()
    await expect(page.getByTestId("static-catalog-entry")).toHaveCount(3)
    await expect(
      page.getByRole("link", { name: "阅读 Open-Meteo 官方文档" }),
    ).toHaveAttribute("href", "https://open-meteo.com/en/docs")
  })

  test("remains usable on a narrow viewport", async ({ page }) => {
    await page.goto("/")

    await expect(
      page.getByRole("heading", { name: "免费 API 资料册" }),
    ).toBeVisible()
    await expect(
      page.getByRole("searchbox", { name: "搜索免费 API 资料" }),
    ).toBeVisible()
    await expect(page.getByTestId("static-catalog-entry").first()).toBeVisible()
  })
})
