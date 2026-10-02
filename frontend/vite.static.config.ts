import { existsSync, renameSync, unlinkSync } from "node:fs"
import path from "node:path"

import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

function normalizeStaticIndex() {
  return {
    name: "normalize-static-index",
    closeBundle() {
      const outputDir = path.resolve(
        import.meta.dirname,
        "../deploy/static-catalog",
      )
      const source = path.join(outputDir, "static-catalog.html")
      const target = path.join(outputDir, "index.html")

      if (!existsSync(source)) return
      if (existsSync(target)) unlinkSync(target)
      renameSync(source, target)
    },
  }
}

export default defineConfig({
  publicDir: false,
  build: {
    rollupOptions: {
      input: {
        index: path.resolve(import.meta.dirname, "./static-catalog.html"),
      },
    },
    outDir: "../deploy/static-catalog",
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  plugins: [react(), tailwindcss(), normalizeStaticIndex()],
})
