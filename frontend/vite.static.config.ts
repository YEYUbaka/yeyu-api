import { execFileSync } from "node:child_process"
import { existsSync, renameSync, unlinkSync, writeFileSync } from "node:fs"
import path from "node:path"

import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

function normalizeStaticIndex() {
  return {
    name: "normalize-static-index",
    closeBundle() {
      const projectRoot = path.resolve(import.meta.dirname, "..")
      const outputDir = path.resolve(
        import.meta.dirname,
        "../deploy/static-catalog",
      )
      const source = path.join(outputDir, "static-catalog.html")
      const target = path.join(outputDir, "index.html")

      if (!existsSync(source)) return
      if (existsSync(target)) unlinkSync(target)
      renameSync(source, target)

      const commit = execFileSync(
        "git",
        ["-C", projectRoot, "rev-parse", "--verify", "HEAD"],
        { encoding: "utf8" },
      ).trim()
      const workingTreeStatus = execFileSync(
        "git",
        ["-C", projectRoot, "status", "--porcelain", "--untracked-files=all"],
        { encoding: "utf8" },
      ).trim()
      const metadata = {
        project: "yeyu-api",
        commit,
        workingTreeClean: workingTreeStatus === "",
        generatedAtUtc: new Date().toISOString(),
      }
      writeFileSync(
        path.join(outputDir, "build-meta.json"),
        `${JSON.stringify(metadata, null, 2)}\n`,
        "utf8",
      )
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
