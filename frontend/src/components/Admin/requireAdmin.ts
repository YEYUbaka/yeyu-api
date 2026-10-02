import { redirect } from "@tanstack/react-router"

import { UsersService } from "@/client"

export async function requireAdmin() {
  const { data: user } = await UsersService.readUserMe()
  if (!user.is_superuser) {
    throw redirect({ to: "/" })
  }
}
