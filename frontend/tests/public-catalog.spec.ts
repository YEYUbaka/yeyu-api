import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("Anonymous users can open the public home without login redirect", async ({
  page,
}) => {
  await page.goto("/")

  await expect(page).toHaveURL(/\/$/)
  await expect(
    page.getByRole("heading", {
      name: "给学生和个人开发者的免费 API 工具箱",
    }),
  ).toBeVisible()
  await expect(page).not.toHaveURL(/\/login/)
})

test("Anonymous users can open the catalog entry without login redirect", async ({
  page,
}) => {
  await page.goto("/catalog")

  await expect(page).not.toHaveURL(/\/login/)
})

test("Public navigation exposes keyboard-accessible catalog and login links", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/")

  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
  await expect(page.getByRole("link", { name: "API 目录" })).toBeVisible()
  await expect(page.getByRole("link", { name: "登录" })).toBeVisible()

  await page.getByRole("link", { name: "登录" }).focus()
  await expect(page.getByRole("link", { name: "登录" })).toBeFocused()
})
