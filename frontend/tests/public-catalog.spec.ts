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

test("Anonymous users can open the public catalog placeholder", async ({
  page,
}) => {
  await page.goto("/catalog")

  await expect(page).toHaveURL("/catalog")
  await expect(
    page.getByRole("heading", { name: "API 目录建设中" }),
  ).toBeVisible()
  await expect(page.getByText("由公开目录驱动")).toBeVisible()
  await expect(page.getByRole("navigation", { name: "公共导航" })).toBeVisible()
})

test("Public navigation exposes keyboard-accessible catalog and login links", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
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

  await navigation.getByRole("link", { name: "登录" }).focus()
  await expect(navigation.getByRole("link", { name: "登录" })).toBeFocused()
})
