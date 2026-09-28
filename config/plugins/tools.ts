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

function requiredBoolean(description: string) {
  return tool.schema.boolean().describe(description)
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

const replacementSchema = tool.schema.object({
  old: tool.schema.string().describe("Exact existing text that must occur exactly once in the applicable source"),
  new: tool.schema.string().describe("Replacement text; an empty string deletes the matched text"),
})

function replacementArray(description: string) {
  return tool.schema.array(replacementSchema).describe(description)
}

function optionalReplacementArray(description: string) {
  return tool.schema.array(replacementSchema).optional().describe(description)
}

const semanticNodeSchema = tool.schema.object({
  requirement: tool.schema.string().describe("Requirement statement that must be satisfied"),
  requires: tool.schema
    .array(tool.schema.string())
    .optional()
    .describe("Handles of nodes that must become true for this requirement to be fulfilled (ALL-of); omit when the requirement has no authored children yet"),
})

const semanticGraphSchema = tool.schema.object({
  root: tool.schema.string().describe("Handle of the root semantic node"),
  nodes: tool.schema
    .record(tool.schema.string(), semanticNodeSchema)
    .describe("Handle -> semantic node ({requirement, requires?})"),
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
    description: "Create a new ASR in the workspace-local system-requirements skill, under the directory for its status.",
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

  governance_migrate: tool({
    description:
      "Migrate a legacy artifacts/decisions + artifacts/requirements ADR/ASR corpus into the canonical workspace-local governance skills and regenerate both SKILL.md indexes. Explicit and all-or-nothing: any failure leaves the legacy source corpus intact.",
    args: {
      dry_run: optionalBoolean("Report the migration plan without mutating anything"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.governance_migrate", args, context)
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
    description: "Archive a pending DD bundle by updating DD.md to Completed and moving pending/{slug}/ to completed/{slug}/ after its linked Change DAG bundle in artifacts/change-dags/ is completed (artifact lifecycle). Refuses an occupied destination unless force is true.",
    args: {
      name: requiredString("DD name"),
      force: optionalBoolean("Replace an existing completed bundle"),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.dd_archive", args, context)
    },
  }),

  // ── Change DAG ────────────────────────────────────────────────────────────

  dag_create: tool({
    description: "Create and persist a validated Change DAG from a semantic requirement graph; returns canonical node IDs.",
    args: {
      slug: requiredString("Change DAG slug"),
      semantic_graph: semanticGraphSchema,
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_create", args, context) },
  }),
  dag_show: tool({
    description: "Show the whole Change DAG or a bounded centered view around one node.",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: optionalString("Center the view on this node ID"),
      include_ancestors: optionalBoolean("Include ancestors of the centered node"),
      include_descendants: optionalBoolean("Include descendants of the centered node"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_show", args, context) },
  }),
  dag_add_requirement: tool({
    description: "Add a semantic requirement, either as an open leaf or inserted between parents and selected children.",
    args: {
      slug: requiredString("Change DAG slug"),
      requirement: requiredString("Requirement statement"),
      parent_ids: stringArray("Semantic parent node IDs"),
      child_ids: optionalStringArray("Current direct children to move beneath the new requirement"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_add_requirement", args, context) },
  }),
  dag_add_create: tool({
    description: "Attach a create node under the given parents.",
    args: {
      slug: requiredString("Change DAG slug"),
      parent_ids: stringArray("Semantic parent node IDs"),
      path: requiredString("Workspace-relative path to create"),
      content: requiredString("Full file content"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_add_create", args, context) },
  }),
  dag_add_edit: tool({
    description: "Attach an edit node under the given parents.",
    args: {
      slug: requiredString("Change DAG slug"),
      parent_ids: stringArray("Semantic parent node IDs"),
      path: requiredString("Workspace-relative path to edit"),
      replacements: replacementArray("Ordered exact replacements applied sequentially against the accepted base"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_add_edit", args, context) },
  }),
  dag_add_remove: tool({
    description: "Attach a remove node under the given parents.",
    args: {
      slug: requiredString("Change DAG slug"),
      parent_ids: stringArray("Semantic parent node IDs"),
      path: requiredString("Workspace-relative path to remove"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_add_remove", args, context) },
  }),
  dag_add_move: tool({
    description: "Attach a move node under the given parents.",
    args: {
      slug: requiredString("Change DAG slug"),
      parent_ids: stringArray("Semantic parent node IDs"),
      from_path: requiredString("Workspace-relative source path"),
      to_path: requiredString("Workspace-relative destination path"),
      overwrite: optionalBoolean("Replace an existing destination (default false)"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_add_move", args, context) },
  }),
  dag_add_run: tool({
    description: "Attach a bounded verification run node under the given parents.",
    args: {
      slug: requiredString("Change DAG slug"),
      parent_ids: stringArray("Semantic parent node IDs"),
      command: stringArray("Command argv (no shell)"),
      exclusive: optionalBoolean("Require exclusive execution"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_add_run", args, context) },
  }),
  dag_update_requirement: tool({
    description: "Update the requirement text of a mutable semantic node.",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Node ID"),
      requirement: requiredString("Replacement requirement statement"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_update_requirement", args, context) },
  }),
  dag_update_create: tool({
    description: "Update a mutable create node (at least one field).",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Node ID"),
      path: optionalString("Replacement path"),
      content: optionalString("Replacement content"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_update_create", args, context) },
  }),
  dag_update_edit: tool({
    description: "Update a mutable edit node (at least one field).",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Node ID"),
      path: optionalString("Replacement path"),
      replacements: optionalReplacementArray("Exact replacements reinterpreted against the node's current self-view"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_update_edit", args, context) },
  }),
  dag_update_remove: tool({
    description: "Update a mutable remove node (at least one field).",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Node ID"),
      path: optionalString("Replacement path"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_update_remove", args, context) },
  }),
  dag_update_move: tool({
    description: "Update a mutable move node (at least one field).",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Node ID"),
      from_path: optionalString("Replacement source path"),
      to_path: optionalString("Replacement destination path"),
      overwrite: optionalBoolean("Replacement overwrite flag"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_update_move", args, context) },
  }),
  dag_update_run: tool({
    description: "Update a mutable run node (at least one field).",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Node ID"),
      command: optionalStringArray("Replacement command argv"),
      exclusive: optionalBoolean("Replacement exclusivity flag"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_update_run", args, context) },
  }),
  dag_set_decomposition_only: tool({
    description:
      "Declare or reopen whether a mutable semantic node intentionally owns no direct terminal work because its obligation is fully decomposed into the semantic requirements it directly requires. Semantic nodes only.",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Semantic node ID"),
      value: requiredBoolean("true to declare fully decomposed into semantic children; false to reopen the judgment"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_set_decomposition_only", args, context) },
  }),
  dag_remove: tool({
    description: "Remove a mutable node, preserving shared descendants and garbage-collecting mutable unreachable work.",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Node ID to remove"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_remove", args, context) },
  }),
  dag_preview: tool({
    description:
      "Preview a Change DAG without executing. No args: whole-DAG inspection (all specified work simulated across run barriers). " +
      "path only: one file's eventual compiled layers. node_id only: one node's reachable subgraph. " +
      "path + node_id (semantic): frontier-bounded AUTHORING CONTEXT - live source plus accepted lower work strictly deeper than that semantic boundary, " +
      "excluding same-frontier peers and shallower/future work.",
    args: {
      slug: requiredString("Change DAG slug"),
      path: optionalString("Workspace-relative path; with node_id selects the authoring-context file"),
      node_id: optionalString("Node ID; with path must be a semantic authoring boundary, alone limits to its reachable subgraph"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_preview", args, context) },
  }),
  dag_validate: tool({
    description: "Report derived schema validity, executability, and resolution for a Change DAG.",
    args: {
      slug: requiredString("Change DAG slug"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_validate", args, context) },
  }),
  dag_decomposition_frontier: tool({
    description:
      "Return the deepest unresolved semantic frontier of a Change DAG — the canonical semantic node identities currently ready for bounded Worker authoring. " +
      "Derived from the existing graph depth and resolution semantics; never infers dependencies. Read-only.",
    args: {
      slug: requiredString("Change DAG slug"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_decomposition_frontier", args, context) },
  }),
  dag_decomposition_scope: tool({
    description:
      "Return the bounded graph-local decomposition context for one assigned semantic node: the target node, all immediate semantic parents, the deduplicated sibling union " +
      "(the other direct children of those parents), and the target's direct children. " +
      "Derived from the existing graph and resolution semantics; read-only; never performs repository discovery or compiles patches.",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Assigned semantic node ID"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_decomposition_scope", args, context) },
  }),
  dag_read: tool({
    description:
      "Read a file from live repository state plus accepted lower Change DAG work strictly deeper than a semantic authoring boundary. Excludes same-frontier peers, the boundary node's own work, and shallower/future work; returns only the requested range.",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Semantic authoring boundary node ID"),
      path: requiredString("Workspace-relative projected file path"),
      start_line: optionalNumber("1-indexed inclusive start line"),
      end_line: optionalNumber("1-indexed inclusive end line"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_read", args, context) },
  }),
  dag_grep: tool({
    description:
      "Find matching lines in live repository state plus accepted lower Change DAG work strictly deeper than a semantic authoring boundary. Excludes same-frontier peers, the boundary node's own work, and shallower/future work; returns deterministic path/line matches without snippets.",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Semantic authoring boundary node ID"),
      pattern: requiredString("Regular expression to match"),
      path: optionalString("Optional workspace-relative projected file path"),
      ignore_case: optionalBoolean("Case-insensitive matching"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_grep", args, context) },
  }),
  dag_search: tool({
    description:
      "Rank projected source files using deterministic textual scoring over live state plus accepted lower work strictly deeper than a semantic authoring boundary. No semantic/vector retrieval; excludes same-frontier peers, the boundary node's own work, and shallower/future work.",
    args: {
      slug: requiredString("Change DAG slug"),
      node_id: requiredString("Semantic authoring boundary node ID"),
      query: requiredString("Text query"),
      path: optionalString("Optional workspace-relative projected file path"),
      limit: optionalNumber("Maximum result count"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_search", args, context) },
  }),
  dag_start: tool({
    description: "Execute a Change DAG, optionally retrying previously failed nodes.",
    args: {
      slug: requiredString("Change DAG slug"),
      retry: optionalBoolean("Retry failed nodes"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_start", args, context) },
  }),
  dag_stop: tool({
    description: "Stop an executing Change DAG so it can be repaired.",
    args: {
      slug: requiredString("Change DAG slug"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_stop", args, context) },
  }),
  dag_status: tool({
    description: "Report Change DAG execution status, optionally for one slug.",
    args: {
      slug: optionalString("Change DAG slug; omit to report the active DAG and all queued DAGs"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_status", args, context) },
  }),
  dag_archive: tool({
    description: "Retire a Change DAG from the pending working set, recording why it left and the state it was in. Archival is lifecycle cleanup: it does not certify resolution, executability, successful execution, or QA.",
    args: {
      slug: requiredString("Change DAG slug"),
      reason: requiredString("Why this DAG is leaving the pending working set (for example: execution completed and artifact retired)"),
    },
    async execute(args, context) { return runPythonTool("common.tools.dag_archive", args, context) },
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
      "Measure generic file context plus optional Change DAG worker-node and manager-review packets using the shipped orchestration policy (config/agent-context-budgets.yaml).",
    args: {
      files: tool.schema.array(fileRangeSchema).optional().describe("Files or line ranges to measure; omit when using an ephemeral DAG packet"),
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
      "Write a validated terminal QA round record under artifacts/logs/qa-rounds. Records are writer-isolated for qa-test-generator, qa-docs-generator, or the retained exec-fixer identity for continuity/historical records (not an active agent contract); generator decisions are REPAIRED, UNNECESSARY, BLOCKED, or ESCALATED, while exec-fixer may write only REPAIRED. A repeated stable record identity (dag_slug or legacy task_family, round, writer, subject) is rejected fail-closed.",
    args: {
      record: tool.schema
        .object({})
        .describe(
          "Terminal record with dag_slug (or legacy task_family), positive round, writer, agent, stable subject (string, or object with kind plus at least one identifying key), decision, repository-derived evidence, actual verification, changed_files, changed_symbols, and explicit provenance (source_kind: analyzer-finding for generators / fixer-issue for exec-fixer; source_ref), plus repair text for exec-fixer records. Progress, chain-of-thought, and speculation are rejected.",
        ),
    },
    async execute(args: ToolArgs, context: ToolContext) {
      return runPythonTool("common.tools.qa_record_write", args, context)
    },
  }),

  qa_record_read: tool({
    description:
      "Read validated terminal QA round records for an existing dag_slug or legacy task_family, optionally filtered by round, writer, subject substring, decision, or provenance. Missing history is empty; malformed or cross-family history fails closed.",
    args: {
      task_family: optionalString("Legacy existing task-family identity (publication/compatibility records)"),
      dag_slug: optionalString("Change DAG slug for DAG execution records"),
      round: optionalNumber("Positive QA round number"),
      writer: optionalString("Writer: qa-test-generator, qa-docs-generator, or retained exec-fixer identity (historical continuity; not an active agent contract)"),
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
