import { afterEach, describe, expect, test } from "bun:test"
import { mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { ToolsPlugin } from "../config/plugins/tools"

const roots: string[] = []
const previousToolsDir = process.env.SKYSCOW_TOOLS_DIR

async function root(): Promise<string> {
  const value = await mkdtemp(path.join(os.tmpdir(), "skyscow-capability-lifetime-"))
  roots.push(value)
  await symlink(path.resolve("config/tools"), path.join(value, "tools"))
  return value
}

function context(directory: string, sessionID: string, agent: string) {
  return { directory, sessionID, messageID: `${sessionID}-message`, agent } as never
}

async function invoke(plugin: any, name: string, args: Record<string, unknown>, ctx: any): Promise<any> {
  const value = await plugin.tool[name].execute(args, ctx)
  return JSON.parse(value.output)
}

afterEach(async () => {
  if (previousToolsDir === undefined) delete process.env.SKYSCOW_TOOLS_DIR
  else process.env.SKYSCOW_TOOLS_DIR = previousToolsDir
  await Promise.all(roots.splice(0).map((value) => rm(value, { recursive: true, force: true })))
})

describe("plugin capability lifetime", () => {
  test("carries worker and fixer capabilities across fresh Python subprocesses", async () => {
    const workspace = await root()
    process.env.SKYSCOW_TOOLS_DIR = path.join(workspace, "tools")
    await writeFile(path.join(workspace, "source.txt"), "before\n")
    const plugin = await ToolsPlugin({ client: {} } as never)
    const author = context(workspace, "author-session", "change-dag-author")
    const manager = context(workspace, "manager-session", "change-dag-author")
    const worker = context(workspace, "worker-session", "change-dag-worker")

    const created = await invoke(plugin, "dag_create", {
      slug: "lifetime",
      semantic_graph: { root: "root", nodes: { root: { requirement: "root", requires: ["leaf"] }, leaf: { requirement: "leaf" } } },
    }, author)
    expect(created.root_node_id).toBe("N1")

    const frontier = await invoke(plugin, "dag_decomposition_frontier", { slug: "lifetime" }, manager)
    const branchRef = frontier.frontier.branches[0].branch_ref
    expect(branchRef).toBeString()
    expect(typeof branchRef).toBe("string")

    const resolved = await invoke(plugin, "dag_worker_resolve", { slug: "lifetime", branch_ref: branchRef }, worker)
    expect(resolved.node_id).toBe("N2")

    const scoped = await invoke(plugin, "dag_semantic_context", { slug: "lifetime", node_ids: ["N2"] }, worker)
    expect(scoped.semantic_context ?? scoped).toBeTruthy()

    const added = await invoke(plugin, "dag_add_create", {
      slug: "lifetime", parent_ids: ["N2"], path: "generated.txt", content: "after\n",
    }, worker)
    expect(added.node_id).toBe("N3")
    const boundRead = await invoke(plugin, "dag_read", { slug: "lifetime", node_id: "N2", path: "source.txt", start_line: 1, end_line: 1 }, worker)
    expect(boundRead.node_id).toBe("N2")

    const otherWorker = context(workspace, "other-worker", "change-dag-worker")
    await expect(invoke(plugin, "dag_read", { slug: "lifetime", node_id: "N2", path: "source.txt", start_line: 1, end_line: 1 }, otherWorker)).rejects.toThrow("session_unbound")
    await expect(invoke(plugin, "dag_read", { slug: "lifetime", node_id: "N1", path: "source.txt", start_line: 1, end_line: 1 }, worker)).rejects.toThrow("worker_scope_mismatch")
    await expect(invoke(plugin, "dag_worker_resolve", { slug: "lifetime", branch_ref: branchRef }, worker)).rejects.toThrow("invalid_branch_ref")

    const grant = await plugin.tool.dag_issue_repair_grant.execute({ slug: "lifetime", semantic_node_id: "N2", terminal_node_ids: ["N3"], paths: ["generated.txt"] }, author)
    expect(grant.repair_ref).toBeString()
    const fixer = context(workspace, "fixer-session", "change-dag-fixer")
    await expect(plugin.tool.dag_fixer_mutate.execute({
      repair_ref: grant.repair_ref, slug: "lifetime", semantic_node_id: "N2", operation: "update", node_id: "N3",
      path: "generated.txt", content: "fixed\n",
    }, context(workspace, "wrong-session", "change-dag-worker"))).rejects.toThrow("fixer-only capability")
    const fixed = await invoke(plugin, "dag_fixer_mutate", {
      repair_ref: grant.repair_ref, slug: "lifetime", semantic_node_id: "N2", operation: "update", node_id: "N3",
      path: "generated.txt", content: "fixed\n",
    }, fixer)
    expect(fixed.node_id).toBe("N3")
  })
})
