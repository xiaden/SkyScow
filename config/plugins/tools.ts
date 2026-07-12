import { type Plugin, tool } from "@opencode-ai/plugin"
import path from "path"
import os from "os"

const TOOLS_DIR = path.join(os.homedir(), ".config/opencode/tools")

type ToolArgs = Record<string, unknown>
type ToolContext = {
  directory?: string
  [key: string]: unknown
}

function requiredString(description: string) {
  return tool.schema.string().describe(description)
}

function optionalString(description: string) {
  return tool.schema.string().optional().describe(description)
}

function requiredNumber(description: string) {
  return tool.schema.number().describe(description)
}

function optionalNumber(description: string) {
  return tool.schema.number().optional().describe(description)
}

function optionalBoolean(description: string) {
  return tool.schema.boolean().optional().describe(description)
}

function stringArray(description: string) {
  return tool.schema.array(tool.schema.string()).describe(description)
}

function optionalStringArray(description: string) {
  return tool.schema.array(tool.schema.string()).optional().describe(description)
}

const extraSectionSchema = tool.schema.object({
  heading: tool.schema.string(),
  content: tool.schema.string(),
})

const relatedDocumentSchema = tool.schema.object({
  title: tool.schema.string(),
  path: tool.schema.string(),
  description: tool.schema.string(),
})

function workspaceRoot(context: ToolContext): string {
  if (typeof context.directory === "string" && context.directory.length > 0) {
    return context.directory
  }

  return process.cwd()
}

// ── Runner ───────────────────────────────────────────────────────────────────

async function runPythonTool(moduleName: string, args: ToolArgs, context: ToolContext) {
  const input = JSON.stringify({
    ...args,
    workspace_root: workspaceRoot(context),
  })

  const proc = Bun.spawn({
    cmd: ["python3", "-m", moduleName],
    cwd: TOOLS_DIR,
    stdin: "pipe",
    stdout: "pipe",
    stderr: "pipe",
  })

  proc.stdin.write(input)
  proc.stdin.end()

  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ])

  const trimmedStdout = stdout.trim()
  const trimmedStderr = stderr.trim()

  if (exitCode !== 0) {
    throw new Error(
      `[${moduleName}] exited with code ${exitCode}: ${trimmedStderr || trimmedStdout || "no output"}`,
    )
  }

  if (!trimmedStdout) {
    throw new Error(`[${moduleName}] returned no stdout`)
  }

  let result: unknown
  try {
    result = JSON.parse(trimmedStdout)
  } catch (error) {
    throw new Error(
      `[${moduleName}] invalid JSON: ${error instanceof Error ? error.message : String(error)}\n${trimmedStdout}`,
    )
  }

  if (result && typeof result === "object" && "error" in result) {
    const err = result as { error: string; message?: string }
    throw new Error(`[${moduleName}] ${err.error}: ${err.message ?? "unknown error"}`)
  }

  // If the Python tool already returns { output, title, metadata }, use it directly
  if (result && typeof result === "object" && "output" in result) {
    const r = result as { output: unknown; title?: string; metadata?: Record<string, unknown> }
    return {
      output: typeof r.output === "string" ? r.output : JSON.stringify(r.output),
      title: r.title ?? "",
      metadata: r.metadata ?? {},
    }
  }

  // Fallback: raw JSON (should not be reached for properly configured tools)
  const toolName = moduleName.startsWith("common.tools.") ? moduleName.slice("common.tools.".length) : moduleName
  return {
    output: typeof result === "string" ? result : JSON.stringify(result, null, 2),
    title: toolName,
    metadata: {},
  }
}

// ── Tool definitions ─────────────────────────────────────────────────────────

const tools = {
  adr_read: tool({
    description: "Read and parse an existing Architecture Decision Record.",
    args: {
      name: requiredString("ADR identifier"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.adr_read", args, context)
    },
  }),

  adr_search: tool({
    description: "Search Architecture Decision Records by tag, status, and/or text query.",
    args: {
      query: optionalString("Text to search"),
      tag: optionalString("Filter by exact tag"),
      status: optionalString("Filter by exact status"),
      limit: optionalNumber("Max results, capped at 50"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.adr_search", args, context)
    },
  }),

  adr_suggest: tool({
    description: "Preview an ADR without writing to disk.",
    args: {
      title: requiredString("Title of the architecture decision"),
      status: requiredString("Status: Proposed, Accepted, Deprecated, or Superseded"),
      tags: stringArray("Tags"),
      context: requiredString("Context section"),
      decision: requiredString("Decision section"),
      consequences: requiredString("Consequences section"),
      references: optionalString("References"),
      source_log: optionalString("Source log ref"),
      extra_sections: tool.schema.array(extraSectionSchema).optional().describe("Extra sections"),
      supersedes: optionalStringArray("Supersedes"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.adr_suggest", args, context)
    },
  }),

  adr_commit: tool({
    description: "Write an approved ADR to disk.",
    args: {
      draft_id: requiredString("Slug from adr_suggest"),
      title: optionalString("Title"),
      status: optionalString("Status"),
      tags: optionalStringArray("Tags"),
      context: optionalString("Context"),
      decision: optionalString("Decision"),
      consequences: optionalString("Consequences"),
      references: optionalString("References"),
      source_log: optionalString("Source log ref"),
      extra_sections: tool.schema.array(extraSectionSchema).optional().describe("Extra sections"),
      supersedes: optionalStringArray("Supersedes"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.adr_commit", args, context)
    },
  }),

  asr_create: tool({
    description: "Create a new ASR in artifacts/requirements/.",
    args: {
      priority: requiredNumber("Priority integer"),
      requirement: requiredString("The requirement body"),
      notes: optionalString("Optional notes"),
      status: optionalString("Status"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.asr_create", args, context)
    },
  }),

  asr_read: tool({
    description: "Read and parse an existing ASR.",
    args: {
      name: requiredString("ASR identifier"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.asr_read", args, context)
    },
  }),

  asr_search: tool({
    description: "Search ASRs by status, priority range, and/or text query.",
    args: {
      query: optionalString("Text to search"),
      status: optionalString("Filter by exact status"),
      priority_min: optionalNumber("Minimum priority"),
      priority_max: optionalNumber("Maximum priority"),
      limit: optionalNumber("Max results, capped at 50"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.asr_search", args, context)
    },
  }),

  dd_read: tool({
    description: "Read and parse a Design Document.",
    args: {
      name: requiredString("DD name"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.dd_read", args, context)
    },
  }),

  dd_create: tool({
    description: "Create a new Design Document in artifacts/designs/pending/.",
    args: {
      title: requiredString("Title"),
      slug: requiredString("URL-safe slug"),
      status: requiredString("Status"),
      author: requiredString("Author"),
      scope: requiredString("Scope"),
      problem_statement: requiredString("Problem Statement"),
      architecture: requiredString("Architecture"),
      design_goals: optionalString("Design Goals"),
      constraints: optionalString("Constraints"),
      open_questions: optionalString("Open Questions"),
      related_documents: tool.schema.array(relatedDocumentSchema).optional().describe("Related docs"),
      extra_sections: tool.schema.array(extraSectionSchema).optional().describe("Extra sections"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.dd_create", args, context)
    },
  }),

  dd_archive: tool({
    description: "Archive a design document from pending to completed.",
    args: {
      name: requiredString("DD name"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.dd_archive", args, context)
    },
  }),

  plan_read: tool({
    description: "Read a task plan and return structured JSON summary.",
    args: {
      plan_name: requiredString("Plan name"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.plan_read", args, context)
    },
  }),

  plan_complete_step: tool({
    description: "Mark a step as complete in a task plan.",
    args: {
      plan_name: requiredString("Plan name"),
      step_id: requiredString("Step ID, for example P1-S3"),
      annotation_marker: optionalString("Annotation marker"),
      annotation_text: optionalString("Annotation text"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      const annotation =
        typeof args.annotation_marker === "string" && typeof args.annotation_text === "string"
          ? { marker: args.annotation_marker, text: args.annotation_text }
          : undefined

      return runPythonTool(
        "common.tools.plan_complete_step",
        {
          plan_name: args.plan_name,
          step_id: args.step_id,
          annotation,
        },
        context,
      )
    },
  }),

  plan_archive: tool({
    description: "Archive a completed task plan from pending to completed.",
    args: {
      plan_name: requiredString("Plan name"),
      ignore_blocked: optionalBoolean("Archive despite Blocked annotations"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.plan_archive", args, context)
    },
  }),

  log_write: tool({
    description: "Append an entry to an agent's JSONL log file.",
    args: {
      agent: requiredString("Agent name"),
      title: requiredString("Entry title"),
      category: requiredString("Category"),
      body: optionalString("Body"),
      tags: optionalStringArray("Tags"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.log_write", args, context)
    },
  }),

  log_read: tool({
    description: "Read an agent's log entries, newest-first, with optional filters.",
    args: {
      agent: requiredString("Agent name. Use '*' for all agents."),
      category: optionalString("Filter by category"),
      tag: optionalString("Filter by tag"),
      title_query: optionalString("Filter by title substring"),
      since: optionalString("Entries at or after"),
      until: optionalString("Entries at or before"),
      limit: optionalNumber("Max entries, capped at 50"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.log_read", args, context)
    },
  }),

  log_archive: tool({
    description: "Move matching log entries to an archive file.",
    args: {
      agent: requiredString("Agent name"),
      ids: optionalStringArray("Entry IDs to archive"),
      tag: optionalString("Archive entries with this tag"),
      category: optionalString("Archive entries with this category"),
      title_query: optionalString("Archive entries with this title substring"),
      before: optionalString("Entries before this time"),
      after: optionalString("Entries after this time"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.log_archive", args, context)
    },
  }),

  echo_test: tool({
    description: "Echo test",
    args: {
      text: tool.schema.string().describe("Text to echo"),
    },
    async execute(args) {
      return { output: args.text, title: "echo", metadata: {} }
    },
  })
}

export const ToolsPlugin: Plugin = async () => {
  return {
    dispose: async () => {
      console.log("[ToolsPlugin] Disposing")
    },
    tool: tools,
  }
}
