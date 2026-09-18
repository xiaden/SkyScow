/**
 * ECC Plugin Hooks for OpenCode (SkyScow-trimmed)
 *
 * This file follows the upstream ECC OpenCode hook where its behavior is useful,
 * while retaining SkyScow's deliberate reduction of ECC's broader hook surface.
 *
 * Kept hooks:
 * - file.edited / file.watcher.updated → change recording
 * - session.idle → incremental console.log audit + desktop notification
 * - session.deleted → cleanup
 * - shell.env → PROJECT_ROOT, PACKAGE_MANAGER, and language detection
 * - permission.ask → auto-approve reads, formatters, and tests
 *
 * Custom tools:
 * - changed-files → session change tree with +/- indicators
 *
 * Removed from upstream ECC:
 * - Git and package-manager auto-approval
 * - automatic formatting and per-edit console.log checks
 * - TypeScript checks, PR reminders, documentation warnings, and long-command reminders
 * - session-created, todo, compaction, profile, and dependency-analyzer features
 */

import type { PluginInput } from "@opencode-ai/plugin"
import * as fs from "fs"
import * as path from "path"
import {
  initStore,
  recordChange,
  clearChanges,
} from "./lib/changed-files-store.js"
import changedFilesTool from "./lib/changed-files.js"

// ── Types ────────────────────────────────────────────────────────────────────

interface PermissionEvent {
  tool: string
  args: unknown
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getECCVersion(): string {
  try {
    const packageJsonPath = path.resolve(__dirname, "../../package.json")
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf-8"))
    return packageJson.version || "2.0.0"
  } catch {
    return "2.0.0"
  }
}

// ── Plugin ───────────────────────────────────────────────────────────────────

export const ECCHooksPlugin = async ({
  client,
  $,
  directory,
  worktree,
}: PluginInput) => {
  const worktreePath = worktree || directory
  const editedFiles = new Set<string>()
  initStore(worktreePath)

  const resolvePath = (p: string): string =>
    path.isAbsolute(p) ? p : path.join(worktreePath, p)

  const hasProjectFile = (relativePath: string): boolean => {
    try { return fs.statSync(resolvePath(relativePath)).isFile() } catch { return false }
  }

  const log = (level: "debug" | "info" | "warn" | "error", message: string) =>
    client.app.log({ body: { service: "ecc", level, message } })

  return {
    // ── Change Recording ─────────────────────────────────────────────────

    /** Records agent-initiated edits (powers changed-files tool) */
    "file.edited": async (event: { path: string }) => {
      editedFiles.add(event.path)
      recordChange(event.path, "modified")
    },

    /** Records external file system changes */
    "file.watcher.updated": async (event: { path: string; type: string }) => {
      let changeType: "added" | "modified" | "deleted" = "modified"
      if (event.type === "create" || event.type === "add") changeType = "added"
      else if (event.type === "delete" || event.type === "remove") changeType = "deleted"
      recordChange(event.path, changeType)
      if (event.type === "change" && /\.(ts|tsx|js|jsx)$/.test(event.path)) {
        editedFiles.add(event.path)
      }
    },

    // ── Session Lifecycle ────────────────────────────────────────────────

    /** Incremental console.log audit across files edited since the last idle */
    "session.idle": async () => {
      if (editedFiles.size === 0) return

      let totalCount = 0
      const filesWithLogs: string[] = []

      for (const filePath of editedFiles) {
        if (!/\.(ts|tsx|js|jsx)$/.test(filePath)) continue

        try {
          const result = await $`grep -c "console\\.log" ${resolvePath(filePath)} 2>/dev/null`.text()
          const count = Number.parseInt(result.trim(), 10)
          if (count > 0) {
            totalCount += count
            filesWithLogs.push(filePath)
          }
        } catch {
          // file may have been deleted since the change was recorded
        }
      }

      if (totalCount > 0) {
        log(
          "warn",
          `[ECC] Audit: ${totalCount} console.log(s) in ${filesWithLogs.length} file(s)`
        )
        filesWithLogs.forEach((f) => log("warn", `  - ${f}`))
        log("warn", "[ECC] Remove console.log statements before committing")
      } else {
        log("info", "[ECC] Audit passed: No console.log statements found")
      }

      editedFiles.clear()

      // Desktop notification
      try {
        if (process.platform === "darwin") {
          await $`osascript -e 'display notification "Task completed!" with title "OpenCode ECC"' 2>/dev/null`
        } else if (process.platform === "linux") {
          await $`notify-send "OpenCode ECC" "Task completed!" 2>/dev/null`
        }
      } catch {
        // notification unavailable — non-critical
      }
    },

    /** Clean up session state */
    "session.deleted": async () => {
      editedFiles.clear()
      clearChanges()
    },

    // ── Environment Injection ─────────────────────────────────────────────

    /** Inject PROJECT_ROOT, PACKAGE_MANAGER, and DETECTED_LANGUAGES into shell env */
    "shell.env": async () => {
      const env: Record<string, string> = {
        ECC_VERSION: getECCVersion(),
        PROJECT_ROOT: worktreePath,
      }

      const lockfiles: Record<string, string> = {
        "bun.lockb": "bun",
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "package-lock.json": "npm",
      }
      for (const [lockfile, pm] of Object.entries(lockfiles)) {
        if (hasProjectFile(lockfile)) {
          env.PACKAGE_MANAGER = pm
          break
        }
      }

      const langDetectors: Record<string, string> = {
        "tsconfig.json": "typescript",
        "go.mod": "go",
        "pyproject.toml": "python",
        "Cargo.toml": "rust",
        "Package.swift": "swift",
      }
      const detected: string[] = []
      for (const [file, lang] of Object.entries(langDetectors)) {
        if (hasProjectFile(file)) detected.push(lang)
      }
      if (detected.length > 0) {
        env.DETECTED_LANGUAGES = detected.join(",")
        env.PRIMARY_LANGUAGE = detected[0]
      }

      return env
    },

    // ── Permission Auto-Approve ───────────────────────────────────────────

    /**
     * Auto-approve safe operations to reduce permission friction.
     * Categories: read/search tools, formatters/linters, and test runners.
     */
    "permission.ask": async (event: PermissionEvent) => {
      try {
        let cmd = ""
        if (typeof event.args === "string") {
          cmd = event.args
        } else if (event.args && typeof event.args === "object") {
          cmd = String((event.args as Record<string, unknown>).command || "")
        }

        // Read/search tools
        if (["read", "glob", "grep", "search", "list"].includes(event.tool)) {
          return { approved: true, reason: "Read-only operation" }
        }

        // Formatters + linters
        if (
          event.tool === "bash" &&
          /^(npx )?(@biomejs\/biome|prettier|black|gofmt|rustfmt|swift-format|eslint|ruff|djlint)/.test(cmd)
        ) {
          return { approved: true, reason: "Formatter/linter" }
        }

        // Test runners
        if (
          event.tool === "bash" &&
          /^(npm test|npx (vitest|jest|playwright|mocha)|pytest|go test|cargo test|bun test|dotnet test)/.test(cmd)
        ) {
          return { approved: true, reason: "Test execution" }
        }

        // Let user decide
        return { approved: undefined }
      } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : String(error)
        log("error", `[ECC] Permission error for ${event.tool}: ${msg}`)
        return { approved: false, reason: `Error: ${msg}` }
      }
    },

    // ── Custom Tools ──────────────────────────────────────────────────────

    tool: {
      "changed-files": changedFilesTool,
    },
  }
}

export default ECCHooksPlugin
