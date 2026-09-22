import { type Plugin, tool } from "@opencode-ai/plugin"
import path from "path"
import os from "os"
import { createCaptureRequestContextTool } from "./capture_request_context"

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

const fileRangeSchema = tool.schema.object({
  path: tool.schema.string().describe("Workspace-relative file path"),
  start_line: tool.schema.number().describe("1-indexed inclusive start line"),
  end_line: tool.schema.number().describe("1-indexed inclusive end line"),
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
    description: "Read and parse a Design Document bundle, preferring pending/{slug}/DD.md before completed/{slug}/DD.md.",
    args: {
      name: requiredString("DD name"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.dd_read", args, context)
    },
  }),

  dd_create: tool({
    description: "Create a new Design Document bundle in artifacts/designs/pending/{slug}/ with root-level DD.md.",
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
    description: "Archive a pending DD bundle by updating DD.md to Completed and moving pending/{slug}/ to completed/{slug}/ after linked plans are complete. Refuses an occupied destination unless force is true.",
    args: {
      name: requiredString("DD name"),
      force: optionalBoolean("Replace an existing completed bundle"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.dd_archive", args, context)
    },
  }),

  plan_read: tool({
    description: "Read a task plan and return structured JSON summary.",
    args: {
      plan_name: requiredString("Plan name"),
      phase: optionalNumber("Return only this phase by number"),
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

  plan_annotate_step: tool({
    description: "Add or edit an annotation on a plan step without changing its completion status. Use 'add' to append to existing annotations, 'edit' to replace them.",
    args: {
      plan_name: requiredString("Plan name"),
      step_id: requiredString("Step ID, for example P1-S3"),
      op: requiredString("'add' to append or 'edit' to replace"),
      annotation_marker: requiredString("Annotation marker (e.g. Notes, Blocked, Warning)"),
      annotation_text: requiredString("Annotation text"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.plan_annotate_step", args, context)
    },
  }),

  plan_unmark_step: tool({
    description: "Revert a step from complete back to pending. Prepends an [UNMARKED] notice to the step's annotations. Used by managers and QA to direct re-execution of prematurely-completed steps.",
    args: {
      plan_name: requiredString("Plan name"),
      step_id: requiredString("Step ID, for example P1-S3"),
      agent: requiredString("Agent performing the unmark (e.g. exec-manager, qa-reviewer)"),
      reason: optionalString("Why the step is being unmarked"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.plan_unmark_step", args, context)
    },
  }),

  plan_archive: tool({
    description: "Archive a completed task plan from pending to completed. Refuses an occupied destination unless force is true.",
    args: {
      plan_name: requiredString("Plan name"),
      ignore_blocked: optionalBoolean("Archive despite Blocked annotations"),
      force: optionalBoolean("Replace an existing completed plan"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.plan_archive", args, context)
    },
  }),

  impl_graph_create: tool({
    description: "Create a validated persistent implementation graph.",
    args: { graph: tool.schema.object({}) },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_create", args, context) },
  }),
  impl_graph_read: tool({
    description: "Read a bounded implementation graph view.",
    args: { graph_id: requiredString("Graph ID"), view: optionalString("View"), node_ids: optionalStringArray("Node IDs"), requirement_id: optionalString("Requirement ID"), contract_id: optionalString("Contract ID"), limit: optionalNumber("Result limit") },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_read", args, context) },
  }),
  impl_graph_validate: tool({
    description: "Validate an implementation graph.",
    args: { graph_id: requiredString("Graph ID") },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_validate", args, context) },
  }),
  impl_graph_amend: tool({
    description: "Amend pending implementation graph topology.",
    args: { graph_id: requiredString("Graph ID"), operations: tool.schema.array(tool.schema.object({})).optional().describe("Bounded amendment operations"), nodes: tool.schema.array(tool.schema.object({})).optional(), remove_node_ids: optionalStringArray("Node IDs to remove"), requirements: tool.schema.array(tool.schema.object({})).optional(), contracts: tool.schema.array(tool.schema.object({})).optional(), actor: requiredString("Planner actor"), reason: requiredString("Amendment reason") },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_amend", args, context) },
  }),
  impl_graph_claim: tool({
    description: "Claim derived-ready implementation nodes.",
    args: { graph_id: requiredString("Graph ID"), node_ids: stringArray("Node IDs"), claim_id: requiredString("Claim identity"), worker: optionalString("Worker identity"), manager_session: requiredString("Manager frontier session"), expected_structure_revision: requiredNumber("Expected structural revision"), expected_structure_digest: optionalString("Expected structural digest"), changed_files: optionalStringArray("Known changed files"), write_scopes: stringArray("Manager-established write scopes") },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_claim", args, context) },
  }),
  impl_graph_release: tool({
    description: "Release claimed implementation nodes.",
    args: { graph_id: requiredString("Graph ID"), node_ids: stringArray("Node IDs"), claim_id: requiredString("Claim identity") },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_release", args, context) },
  }),
  impl_graph_complete: tool({
    description: "Accept claimed implementation nodes.",
    args: { graph_id: requiredString("Graph ID"), node_ids: stringArray("Node IDs"), claim_id: requiredString("Claim identity"), results: tool.schema.array(tool.schema.object({})).describe("Exactly one distinct result per claimed node") },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_complete", args, context) },
  }),
  impl_graph_block: tool({
    description: "Block implementation nodes.",
    args: { graph_id: requiredString("Graph ID"), node_ids: stringArray("Node IDs"), reason: requiredString("Block reason"), claim_id: optionalString("Claim identity") },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_block", args, context) },
  }),
  impl_graph_record_qa: tool({
    description: "Record terminal graph QA.",
    args: { graph_id: requiredString("Graph ID"), status: requiredString("PASS or FAIL"), evidence: tool.schema.unknown() },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_record_qa", args, context) },
  }),
  impl_graph_archive: tool({
    description: "Archive a complete implementation graph after terminal QA.",
    args: { graph_id: requiredString("Graph ID") },
    async execute(args, context) { return runPythonTool("common.tools.impl_graph_archive", args, context) },
  }),

  context_tokens: tool({
    description:
      "Count o200k and DeepSeek V4 Flash 0731 tokens for workspace file subsections, including weighted context estimates.",
    args: {
      files: tool.schema
        .array(fileRangeSchema)
        .describe("File line ranges to assemble and count"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.context_tokens", args, context)
    },
  }),

  context_budget: tool({
    description:
      "Measure generic file context plus optional implementation-graph worker-node and manager-review packets using the shipped orchestration policy (config/agent-context-budgets.yaml). Legacy plan parsing is retained only for historical compatibility.",
    args: {
      files: tool.schema.array(fileRangeSchema).optional().describe("Files or line ranges to measure; omit when using an ephemeral graph packet"),
      graph_packet: tool.schema.object({}).optional().describe("Ephemeral worker-node or manager-review packet"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.context_budget", args, context)
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

  qa_record_write: tool({
    description:
      "Write a validated terminal QA round record under artifacts/logs/qa-rounds. Records are writer-isolated for qa-test-generator, qa-docs-generator, or exec-fixer; generator decisions are REPAIRED, UNNECESSARY, BLOCKED, or ESCALATED, while exec-fixer may write only REPAIRED. A repeated stable record identity (graph_id or legacy task_family, round, writer, subject) is rejected fail-closed.",
    args: {
      record: tool.schema
        .object({})
        .describe(
          "Terminal record with task_family, positive round, writer, agent, stable subject (string, or object with kind plus at least one identifying key), decision, repository-derived evidence, actual verification, changed_files, changed_symbols, and explicit provenance (source_kind: analyzer-finding for generators / fixer-issue for exec-fixer; source_ref), plus repair text for exec-fixer records. Progress, chain-of-thought, and speculation are rejected.",
        ),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.qa_record_write", args, context)
    },
  }),

  qa_record_read: tool({
    description:
      "Read validated terminal QA round records for an existing graph_id or legacy task_family, optionally filtered by round, writer, subject substring, decision, or provenance. Missing history is empty; malformed or cross-family history fails closed.",
    args: {
      task_family: optionalString("Legacy existing task-family identity (publication/compatibility records)"),
      graph_id: optionalString("Graph-native identity for graph execution records"),
      round: optionalNumber("Positive QA round number"),
      writer: optionalString("Writer: qa-test-generator, qa-docs-generator, or exec-fixer"),
      subject: optionalString("Subject substring filter"),
      decision: optionalString("Terminal decision: REPAIRED, UNNECESSARY, BLOCKED, or ESCALATED"),
      source_kind: optionalString("Provenance kind filter (exact): analyzer-finding or fixer-issue"),
      source_ref: optionalString("Provenance reference filter (substring)"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.qa_record_read", args, context)
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

/**
 * Registers SkyScow's custom tools, including the native request-context capture tool.
 *
 * The plugin preserves the existing tool set and adds `capture_request_context`,
 * whose public arguments are exactly `{ from: string }`.
 */
export const ToolsPlugin: Plugin = async (input) => {
  return {
    dispose: async () => {
      console.log("[ToolsPlugin] Disposing")
    },
    tool: {
      ...tools,
      capture_request_context: createCaptureRequestContextTool(input),
    },
  }
}
