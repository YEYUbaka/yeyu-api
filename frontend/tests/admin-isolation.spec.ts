import { expect, test } from "@playwright/test"

import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

test("普通账号不能进入任何管理工作区", async ({ page }) => {
  const email = randomEmail()
  const password = randomPassword()
  await createUser({ email, password })
  await logInUser(page, email, password)

  for (const route of [
    "/admin",
    "/admin-apis",
    "/admin-trial-pool",
    "/admin-policies",
    "/admin-health",
    "/admin-audit",
  ]) {
    await page.goto(route)
    await expect(page).not.toHaveURL(new RegExp(`${route}$`))
    await expect(page).toHaveURL("/")
  }
})
