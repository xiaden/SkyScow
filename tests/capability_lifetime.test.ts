import { afterEach, describe, expect, test } from "bun:test"
import { mkdtemp, rm, symlink, writeFile } from "node:fs/promises"
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
async function harness() {
  const workspace = await root()
  process.env.SKYSCOW_TOOLS_DIR = path.join(workspace, "tools")
  const prompts: any[] = []
  const plugin = await ToolsPlugin({ client: { session: {
    async create() { return { data: { id: "child-session" } } },
    async prompt(options: any) { prompts.push(options) },
  } } } as never)
  return { workspace, prompts, plugin }
}
const graph = { root: "root", nodes: { root: { requirement: "root", requires: ["leaf"] }, leaf: { requirement: "leaf" } } }
afterEach(async () => {
  if (previousToolsDir === undefined) delete process.env.SKYSCOW_TOOLS_DIR
  else process.env.SKYSCOW_TOOLS_DIR = previousToolsDir
  await Promise.all(roots.splice(0).map((value) => rm(value, { recursive: true, force: true })))
})

describe("plugin capability lifetime", () => {
  test("controller derives review, admission, and worker capability requirements", async () => {
    const workspace = await root()
    process.env.SKYSCOW_TOOLS_DIR = path.join(workspace, "tools")
    await writeFile(path.join(workspace, "source.txt"), "before\n")
    const prompts: any[] = []
    const plugin = await ToolsPlugin({ client: { session: {
      async create() { return { data: { id: "child-session" } } },
      async prompt(options: any) { prompts.push(options) },
    } } } as never)
    const author = context(workspace, "author-session", "change-dag-author")
    const controller = context(workspace, "controller-session", "nyx")
    const worker = context(workspace, "child-session", "change-dag-worker")
    const created = await invoke(plugin, "dag_create", {
      slug: "lifetime",
      semantic_graph: { root: "root", nodes: { root: { requirement: "root", requires: ["leaf"] }, leaf: { requirement: "leaf" } } },
    }, author)
    expect(created.root_node_id).toBe("N1")
    const challenged = await invoke(plugin, "dag_construction_state", { slug: "lifetime" }, controller)
    expect(challenged.decision.kind).toBe("review_required")
    const reviewed = await invoke(plugin, "dag_construction_review", {
      slug: "lifetime", checkpoint_identity: challenged.decision.checkpoint_identity, outcome: "PASS",
    }, controller)
    expect(reviewed.outcome).toBe("PASS")
    const started = await invoke(plugin, "dag_construction_start", {
      directory: workspace, slug: "lifetime", parent_session: "controller-session",
    }, controller)
    expect(started.child_session).toBe("child-session")
    expect(prompts).toHaveLength(1)
    const prompt = prompts[0].body.parts[0].text as string
    const branchRef = prompt.match(/branch_ref=([^\n]+)/)?.[1]
    const constructionRef = prompt.match(/construction_ref=([^\n]+)/)?.[1]
    expect(branchRef).toBeString()
    expect(constructionRef).toBeString()
    await expect(invoke(plugin, "dag_worker_resolve", { slug: "lifetime", branch_ref: branchRef, construction_ref: "wrong-construction-ref", checkpoint_identity: "wrong", parent_session: "controller-session" }, worker)).rejects.toThrow("construction_unbound")
    const resolved = await invoke(plugin, "dag_worker_resolve", { slug: "lifetime", branch_ref: branchRef, construction_ref: constructionRef, checkpoint_identity: challenged.decision.checkpoint_identity, parent_session: "controller-session" }, worker)
    expect(resolved.node_id).toBe("N2")
  })

  test("routes a semantic defect to a single-use repair capability consumed by the repair child", async () => {
    const { workspace, prompts, plugin } = await harness()
    const author = context(workspace, "author-session", "change-dag-author")
    const controller = context(workspace, "controller-session", "nyx")
    await invoke(plugin, "dag_create", { slug: "repair", semantic_graph: graph }, author)
    const challenged = await invoke(plugin, "dag_construction_state", { slug: "repair" }, controller)
    const checkpoint = challenged.decision.checkpoint_identity as string
    expect(checkpoint).toBeString()
    const reviewed = await invoke(plugin, "dag_construction_review", {
      slug: "repair", checkpoint_identity: checkpoint, outcome: "SEMANTIC_DEFECT",
    }, controller)
    expect(reviewed.route).toBe("semantic_repair")
    const started = await invoke(plugin, "dag_semantic_repair_start", {
      directory: workspace, slug: "repair", parent_session: "controller-session", checkpoint_identity: checkpoint, opaque_finding: "finding-1",
    }, controller)
    expect(started.childSession).toBe("child-session")
    expect(prompts).toHaveLength(1)
    expect(prompts[0].body.agent).toBe("change-dag-semantic-repairer")
    const prompt = prompts[0].body.parts[0].text as string
    expect(prompt).toContain("semantic_repair_ref=")
    expect(prompt).toContain(`checkpoint_identity=${checkpoint}`)
    expect(prompt).not.toContain(String.raw`\n`)
    const repairRef = prompt.match(/semantic_repair_ref=([^\n]+)/)?.[1]
    expect(repairRef).toBeString()
    const repairer = context(workspace, "child-session", "change-dag-semantic-repairer")
    const wrongRepairer = context(workspace, "actual-repair-session", "change-dag-semantic-repairer")
    await expect(invoke(plugin, "dag_semantic_repair_resolve", { semantic_repair_ref: repairRef, slug: "repair", checkpoint_identity: checkpoint, parent_session: "controller-session" }, wrongRepairer)).rejects.toThrow("semantic_repair_scope_violation")
    const resolved = await invoke(plugin, "dag_semantic_repair_resolve", { semantic_repair_ref: repairRef, slug: "repair", checkpoint_identity: checkpoint, parent_session: "controller-session" }, repairer)
    expect(resolved.slug).toBe("repair")
    expect(resolved.checkpoint_identity).toBe(checkpoint)
    await expect(invoke(plugin, "dag_semantic_repair_resolve", { semantic_repair_ref: repairRef, slug: "repair", checkpoint_identity: checkpoint, parent_session: "controller-session" }, context(workspace, "other-session", "change-dag-semantic-repairer"))).rejects.toThrow("semantic_repair_unbound")
  })

  test("repair child advances its checkpoint across two semantic mutations and rejects external drift", async () => {
    const { workspace, prompts, plugin } = await harness()
    const author = context(workspace, "author-session", "change-dag-author")
    const controller = context(workspace, "controller-session", "nyx")
    const repairer = context(workspace, "child-session", "change-dag-semantic-repairer")
    await invoke(plugin, "dag_create", {
      slug: "repair-chain",
      semantic_graph: { root: "root", nodes: {
        root: { requirement: "root", requires: ["parent", "other", "external"] },
        parent: { requirement: "parent", requires: ["leaf"] },
        other: { requirement: "other", requires: ["leaf", "external"] },
        leaf: { requirement: "leaf" },
        external: { requirement: "external" },
      } },
    }, author)
    const challenged = await invoke(plugin, "dag_construction_state", { slug: "repair-chain" }, controller)
    const checkpoint = challenged.decision.checkpoint_identity as string
    await invoke(plugin, "dag_construction_review", { slug: "repair-chain", checkpoint_identity: checkpoint, outcome: "SEMANTIC_DEFECT" }, controller)
    await invoke(plugin, "dag_semantic_repair_start", {
      directory: workspace, slug: "repair-chain", parent_session: "controller-session", checkpoint_identity: checkpoint, opaque_finding: "finding-1",
    }, controller)
    const prompt = prompts[0].body.parts[0].text as string
    const repairRef = prompt.match(/semantic_repair_ref=([^\n]+)/)?.[1]
    await invoke(plugin, "dag_semantic_repair_resolve", { semantic_repair_ref: repairRef, slug: "repair-chain", checkpoint_identity: checkpoint, parent_session: "controller-session" }, repairer)

    const unlinked = await invoke(plugin, "dag_unlink_requirement", { slug: "repair-chain", parent_id: "N4", child_id: "N5" }, repairer)
    expect(unlinked.parent_id).toBe("N4")
    const linked = await invoke(plugin, "dag_link_requirement", { slug: "repair-chain", parent_id: "N1", child_id: "N5" }, repairer)
    expect(linked.parent_id).toBe("N1")

    const external = context(workspace, "external-session", "change-dag-author")
    await invoke(plugin, "dag_unlink_requirement", { slug: "repair-chain", parent_id: "N1", child_id: "N2" }, external)
    await expect(invoke(plugin, "dag_link_requirement", { slug: "repair-chain", parent_id: "N1", child_id: "N2" }, repairer)).rejects.toThrow("semantic_repair_scope_violation")
  })

  test("Nyx grants one exact terminal repair to a distinct fixer child", async () => {
    const { workspace, plugin } = await harness()
    const author = context(workspace, "author-session", "change-dag-author")
    const controller = context(workspace, "controller-session", "nyx")
    const fixer = context(workspace, "fixer-session", "change-dag-fixer")
    await invoke(plugin, "dag_create", { slug: "fixer", semantic_graph: graph }, author)
    const added = await invoke(plugin, "dag_add_create", { slug: "fixer", parent_ids: ["N2"], path: "repair.txt", content: "before\\n" }, author)
    const grant = await invoke(plugin, "dag_issue_repair_grant", {
      slug: "fixer", semantic_node_id: "N2", terminal_node_ids: [added.node_id], paths: ["repair.txt"], checkpoint_identity: "checkpoint-1", intended_child_session: "fixer-session",
    }, controller)
    await expect(invoke(plugin, "dag_fixer_mutate", {
      repair_ref: grant.repair_ref, slug: "fixer", semantic_node_id: "N2", checkpoint_identity: "wrong", operation: "update", node_id: added.node_id, path: "repair.txt", content: "wrong\\n",
    }, fixer)).rejects.toThrow("scope_violation")
    const updated = await invoke(plugin, "dag_fixer_mutate", {
      repair_ref: grant.repair_ref, slug: "fixer", semantic_node_id: "N2", checkpoint_identity: "checkpoint-1", operation: "update", node_id: added.node_id, path: "repair.txt", content: "fixed\\n",
    }, fixer)
    expect(updated.node_id).toBe(added.node_id)
    const secondGrant = await invoke(plugin, "dag_issue_repair_grant", {
      slug: "fixer", semantic_node_id: "N2", terminal_node_ids: [added.node_id], paths: ["repair.txt"], checkpoint_identity: "checkpoint-1", intended_child_session: "fixer-session",
    }, controller)
    await expect(invoke(plugin, "dag_fixer_mutate", {
      repair_ref: secondGrant.repair_ref, slug: "fixer", semantic_node_id: "N2", checkpoint_identity: "checkpoint-1", operation: "remove", node_id: added.node_id, path: "repair.txt",
    }, context(workspace, "other-fixer-session", "change-dag-fixer"))).rejects.toThrow("scope_violation")
    await expect(invoke(plugin, "dag_fixer_mutate", {
      repair_ref: secondGrant.repair_ref, slug: "fixer", semantic_node_id: "N2", checkpoint_identity: "checkpoint-1", operation: "update", node_id: added.node_id, path: "wrong.txt", content: "wrong\\n",
    }, fixer)).rejects.toThrow("scope_violation")
    await expect(invoke(plugin, "dag_fixer_mutate", {
      repair_ref: secondGrant.repair_ref, slug: "fixer", semantic_node_id: "N2", checkpoint_identity: "checkpoint-1", operation: "add", node_id: added.node_id, path: "repair.txt",
    }, fixer)).rejects.toThrow("scope_violation")
    const removed = await invoke(plugin, "dag_fixer_mutate", {
      repair_ref: secondGrant.repair_ref, slug: "fixer", semantic_node_id: "N2", checkpoint_identity: "checkpoint-1", operation: "remove", node_id: added.node_id, path: "repair.txt",
    }, fixer)
    expect(removed.removed).toContain(added.node_id)
    await expect(invoke(plugin, "dag_fixer_mutate", {
      repair_ref: secondGrant.repair_ref, slug: "fixer", semantic_node_id: "N2", checkpoint_identity: "checkpoint-1", operation: "remove", node_id: added.node_id, path: "repair.txt",
    }, fixer)).rejects.toThrow("unbound")
  })

  test("blocks construction start until an independent PASS review is recorded", async () => {
    const { workspace, plugin } = await harness()
    const author = context(workspace, "author-session", "change-dag-author")
    const controller = context(workspace, "controller-session", "nyx")
    await invoke(plugin, "dag_create", { slug: "gate", semantic_graph: graph }, author)
    await expect(invoke(plugin, "dag_construction_start", {
      directory: workspace, slug: "gate", parent_session: "controller-session",
    }, controller)).rejects.toThrow("construction_blocked")
  })

  test("worker semantic refinement and terminal lowering stay bound to the resolved node", async () => {
    const { workspace, prompts, plugin } = await harness()
    const author = context(workspace, "author-session", "change-dag-author")
    const controller = context(workspace, "controller-session", "nyx")
    const worker = context(workspace, "child-session", "change-dag-worker")
    await invoke(plugin, "dag_create", { slug: "refine", semantic_graph: { root: "root", nodes: { root: { requirement: "root", requires: ["leaf", "sibling"] }, leaf: { requirement: "leaf" }, sibling: { requirement: "sibling" } } } }, author)
    const challenged = await invoke(plugin, "dag_construction_state", { slug: "refine" }, controller)
    await invoke(plugin, "dag_construction_review", { slug: "refine", checkpoint_identity: challenged.decision.checkpoint_identity, outcome: "PASS" }, controller)
    await invoke(plugin, "dag_construction_start", { directory: workspace, slug: "refine", parent_session: "controller-session" }, controller)
    const prompt = prompts[0].body.parts[0].text as string
    const branchRef = prompt.match(/branch_ref=([^\n]+)/)?.[1]
    const constructionRef = prompt.match(/construction_ref=([^\n]+)/)?.[1]
    await invoke(plugin, "dag_worker_resolve", { slug: "refine", branch_ref: branchRef, construction_ref: constructionRef, checkpoint_identity: challenged.decision.checkpoint_identity, parent_session: "controller-session" }, worker)
    const refined = await invoke(plugin, "dag_add_requirement", { slug: "refine", requirement: "leaf details", parent_ids: ["N2"] }, worker)
    expect(refined.node_id).toBe("N4")
    await expect(invoke(plugin, "dag_add_requirement", { slug: "refine", requirement: "outside", parent_ids: ["N1"], child_ids: ["N3"] }, worker)).rejects.toThrow("worker_scope_mismatch")
    const updated = await invoke(plugin, "dag_update_requirement", { slug: "refine", node_id: "N1", requirement: "bound refinement" }, worker)
    expect(updated.node_id).toBe("N2")
    const decomposed = await invoke(plugin, "dag_set_decomposition_only", { slug: "refine", node_id: "N1", value: true }, worker)
    expect(decomposed.node_id).toBe("N2")
    const reopened = await invoke(plugin, "dag_set_decomposition_only", { slug: "refine", node_id: "N1", value: false }, worker)
    expect(reopened.node_id).toBe("N2")
    const lowered = await invoke(plugin, "dag_add_create", { slug: "refine", parent_ids: ["N1"], path: "worker.txt", content: "worker\\n" }, worker)
    expect(lowered.kind).toBe("create")
    expect(lowered.parents).toEqual(["N2"])
  })

  test("reports typed construction completion after the final PASS review", async () => {
    const { workspace, prompts, plugin } = await harness()
    const author = context(workspace, "author-session", "change-dag-author")
    const controller = context(workspace, "controller-session", "nyx")
    await invoke(plugin, "dag_create", { slug: "complete", semantic_graph: { root: "root", nodes: { root: { requirement: "root", requires: ["leaf"] }, leaf: { requirement: "leaf" } } } }, author)
    const first = await invoke(plugin, "dag_construction_state", { slug: "complete" }, controller)
    await invoke(plugin, "dag_construction_review", { slug: "complete", checkpoint_identity: first.decision.checkpoint_identity, outcome: "PASS" }, controller)
    const started = await invoke(plugin, "dag_construction_start", { directory: workspace, slug: "complete", parent_session: "controller-session" }, controller)
    const prompt = prompts[0].body.parts[0].text as string
    const branchRef = prompt.match(/branch_ref=([^\n]+)/)?.[1]
    const constructionRef = prompt.match(/construction_ref=([^\n]+)/)?.[1]
    await invoke(plugin, "dag_worker_resolve", { slug: "complete", branch_ref: branchRef, construction_ref: constructionRef, checkpoint_identity: first.decision.checkpoint_identity, parent_session: "controller-session" }, context(workspace, "child-session", "change-dag-worker"))
    await invoke(plugin, "dag_add_create", { slug: "complete", parent_ids: ["N2"], path: "done.txt", content: "done\n" }, context(workspace, "child-session", "change-dag-worker"))
    const finalState = await invoke(plugin, "dag_construction_state", { slug: "complete" }, controller)
    await invoke(plugin, "dag_construction_review", { slug: "complete", checkpoint_identity: finalState.decision.checkpoint_identity, outcome: "PASS" }, controller)
    const completed = await invoke(plugin, "dag_construction_start", { directory: workspace, slug: "complete", parent_session: "controller-session" }, controller)
    expect(completed.completed).toBe(true)
    expect(completed.status).toBe("complete")
  })

  test("requires construction_ref when a controller-admitted worker resolves its branch", async () => {
    const { workspace, prompts, plugin } = await harness()
    const author = context(workspace, "author-session", "change-dag-author")
    const controller = context(workspace, "controller-session", "nyx")
    const worker = context(workspace, "child-session", "change-dag-worker")
    await invoke(plugin, "dag_create", { slug: "worker", semantic_graph: graph }, author)
    const challenged = await invoke(plugin, "dag_construction_state", { slug: "worker" }, controller)
    await invoke(plugin, "dag_construction_review", {
      slug: "worker", checkpoint_identity: challenged.decision.checkpoint_identity, outcome: "PASS",
    }, controller)
    await invoke(plugin, "dag_construction_start", {
      directory: workspace, slug: "worker", parent_session: "controller-session",
    }, controller)
    const branchRef = (prompts[0].body.parts[0].text as string).match(/branch_ref=([^\n]+)/)?.[1]
    expect(branchRef).toBeString()
    await expect(invoke(plugin, "dag_worker_resolve", { slug: "worker", branch_ref: branchRef }, worker)).rejects.toThrow("construction_scope_violation")
  })
})
