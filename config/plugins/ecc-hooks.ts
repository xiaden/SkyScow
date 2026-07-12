/**
 * ECC Plugin Hooks for OpenCode (trimmed)
 *
 * Kept hooks:
 * - file.edited → change recording (powers changed-files tool)
 * - file.watcher.updated → external change recording
 * - session.idle → console.log audit + desktop notification
 * - session.deleted → cleanup
 * - shell.env → environment injection (PROJECT_ROOT, PACKAGE_MANAGER, DETECTED_LANGUAGES)
 * - permission.ask → auto-approve safe operations (reads, formatters, tests, read-only git)
 *
 * Custom tools:
 * - changed-files → session change tree with +/- indicators
 *
 * Removed (redundant with agent system / aft_inspect / lint rules):
 * - file.edited prettier auto-format (agents handle formatting)
 * - file.edited per-file console.log grep (duplicated by idle sweep)
 * - tool.execute.after tsc check (aft_inspect does this better)
 * - tool.execute.after PR logging (agents don't create PRs)
 * - tool.execute.before git push / doc warning / long cmd reminders (agents can't push; instructions cover the rest)
 * - session.created CLAUDE.md check (legacy Claude Code artifact)
 * - todo.updated progress logging (noise)
 * - dependency-analyzer tool (shallow — never ran real checks)
 * - profile gating system (all kept hooks run unconditionally)
 */

import type { PluginInput } from "@opencode-ai/plugin"
import * as fs from "fs"
import * as path from "path"
import {
  initStore,
  recordChange,
  clearChanges,
  getChangedPaths,
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
      recordChange(event.path, "modified")
    },

    /** Records external file system changes */
    "file.watcher.updated": async (event: { path: string; type: string }) => {
      let changeType: "added" | "modified" | "deleted" = "modified"
      if (event.type === "create" || event.type === "add") changeType = "added"
      else if (event.type === "delete" || event.type === "remove") changeType = "deleted"
      recordChange(event.path, changeType)
    },

    // ── Session Lifecycle ────────────────────────────────────────────────

    /** Final console.log sweep across all changed files + desktop notification */
    "session.idle": async () => {
      const changed = getChangedPaths()
      if (changed.length === 0) return

      const jsTsFiles = changed.filter(({ path: p }) =>
        /\.(ts|tsx|js|jsx)$/.test(p)
      )

      let totalCount = 0
      const filesWithLogs: string[] = []

      for (const { path: filePath } of jsTsFiles) {
        try {
          const content = fs.readFileSync(resolvePath(filePath), "utf-8")
          const count = content.split("\n").filter((line) =>
            line.includes("console.log")
          ).length
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
     * Categories: read-only tools, read-only git, formatters/linters,
     * test runners, package manager info commands.
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

        // Read-only git
        if (
          event.tool === "bash" &&
          /^git (diff|status|log|show|branch|stash list|remote -v)/.test(cmd)
        ) {
          return { approved: true, reason: "Read-only git" }
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

        // Package manager info (read-only)
        if (
          event.tool === "bash" &&
          /^(npm|pnpm|yarn|bun) (ls|list|outdated|audit|why|info|view|explain)/.test(cmd)
        ) {
          return { approved: true, reason: "Package manager info" }
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
