import { describe, expect, test } from "bun:test"
import {
  createConstructionCapabilityService,
  createConstructionControllerAdapter,
  createConstructionReviewAdapter,
  createConstructionContextProjectionAdapter,
  createSemanticRepairAdapter,
} from "../config/plugins/lib/construction-controller"

type Deferred = { promise: Promise<void>; resolve: () => void }
function deferred(): Deferred {
  let resolve!: () => void
  const promise = new Promise<void>((done) => { resolve = done })
  return { promise, resolve }
}

  function fakeClient(gate: Deferred) {
  const calls: string[] = []
  return {
    calls,
    session: {
      async create() {
        calls.push("create")
        return { data: { id: "child-session" } }
      },
      async prompt(options: { path: { id: string } }) {
        calls.push(`prompt:${options.path.id}`)
        await gate.promise
      },
    },
  }
}

describe("construction controller plugin adapter", () => {
  test("projects only bounded meaningful construction context and preserves opaque values", () => {
    const adapter = createConstructionContextProjectionAdapter()
    const input = {
      checkpointIdentity: "checkpoint",
      frontierIdentity: "frontier",
      nextAction: "admit_worker",
      opaqueCapabilities: { construction_ref: "opaque-ref" },
      events: [
        { id: "routine", kind: "routine" as const, checkpointIdentity: "checkpoint", content: "transport", order: 2 },
        { id: "review", kind: "reviewer_finding" as const, checkpointIdentity: "checkpoint", content: "unresolved finding", order: 1 },
        { id: "semantic", kind: "semantic_delta" as const, checkpointIdentity: "checkpoint", content: "semantic delta", order: 0 },
      ],
    }
    const projected = adapter.project(input)
    expect(projected.semanticDeltas).toEqual([{ id: "semantic", content: "semantic delta", opaque: {} }])
    expect(projected.reviewerFindings).toEqual([{ id: "review", content: "unresolved finding", opaque: {} }])
    expect(JSON.stringify(projected)).not.toContain("transport")
    expect(adapter.serialize(projected)).toBe(JSON.stringify(projected))
    expect(adapter.project(input)).toEqual(projected)
  })

  test("rejects stale checkpoints, malformed events, and unbounded output without writes", () => {
    const adapter = createConstructionContextProjectionAdapter()
    const base = { checkpointIdentity: "checkpoint", frontierIdentity: "frontier", nextAction: "review" }
    expect(() => adapter.project({ ...base, events: [{ id: "stale", kind: "repair_finding", checkpointIdentity: "other", content: "finding", order: 0 }] })).toThrow("construction_context_stale")
    expect(() => adapter.project({ ...base, events: [{ id: "bad", kind: "routine", checkpointIdentity: "checkpoint", order: 0 } as never] })).toThrow("construction_context_invalid")
    expect(() => adapter.project({ ...base, events: Array.from({ length: 9 }, (_, order) => ({ id: String(order), kind: "routine" as const, checkpointIdentity: "checkpoint", content: "x", order })) })).toThrow("construction_context_invalid")
  })

  test("semantic repair is an opaque typed callback boundary and rejects stale identity", async () => {
    const adapter = createSemanticRepairAdapter(async (request) => ({
      checkpointIdentity: request.checkpointIdentity,
      childSession: "repair-child",
    }))
    await expect(adapter.invoke({
      directory: "/workspace",
      slug: "demo",
      checkpointIdentity: "checkpoint",
      parentSession: "parent",
      opaqueFinding: "opaque finding",
    })).resolves.toEqual({ checkpointIdentity: "checkpoint", childSession: "repair-child" })

    const stale = createSemanticRepairAdapter(async () => ({ checkpointIdentity: "other", childSession: "repair-child" }))
    await expect(stale.invoke({
      directory: "/workspace",
      slug: "demo",
      checkpointIdentity: "checkpoint",
      parentSession: "parent",
      opaqueFinding: "opaque finding",
    })).rejects.toThrow("semantic_repair_stale")
  })
  test("capability is opaque, single-use, and child-session bound", () => {
    const service = createConstructionCapabilityService()
    const issued = service.issue({ slug: "demo", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent" })
    expect(issued.construction_ref).toMatch(/^[A-Za-z0-9_-]{32}$/)
     expect(service.consume({ constructionRef: issued.construction_ref, slug: "demo", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent", session: "other" }).childSession).toBe("other")
     expect(() => service.consume({ constructionRef: issued.construction_ref, slug: "demo", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent", session: "actual-worker-session" })).toThrow("construction_unbound")
     expect(() => service.consume({ constructionRef: issued.construction_ref, slug: "demo", branchRef: "branch", session: "child" })).toThrow("construction_unbound")
  })

  test("review adapter accepts only typed outcomes for the exact checkpoint", async () => {
    const adapter = createConstructionReviewAdapter(async () => ({
      kind: "PASS",
      checkpointIdentity: "checkpoint",
    }))
    await expect(adapter.review({
      directory: "/workspace",
      slug: "demo",
      checkpointIdentity: "checkpoint",
      parentSession: "parent",
    })).resolves.toMatchObject({ kind: "PASS", checkpointIdentity: "checkpoint" })

    const stale = createConstructionReviewAdapter(async () => ({
      kind: "PASS",
      checkpointIdentity: "other",
    }))
    await expect(stale.review({
      directory: "/workspace",
      slug: "demo",
      checkpointIdentity: "checkpoint",
      parentSession: "parent",
    })).rejects.toThrow("construction_review_stale")
  })

  test("revokes child capability and tears down a child when native prompt resolves an error envelope", async () => {
    const calls: string[] = []
    const client = {
      session: {
        async create() { calls.push("create"); return { data: { id: "child-session" } } },
        async prompt() { calls.push("prompt"); return { error: { message: "prompt failed" } } },
      },
      async teardown(options: { id: string; directory: string }) { calls.push(`teardown:${options.id}`) },
    }
    const adapter = createConstructionControllerAdapter(client)
    await expect(adapter.start({ directory: "/workspace", slug: "envelope", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent" })).rejects.toThrow("construction_child_failed")
    expect(adapter.capabilities.bindCount()).toBe(0)
    expect(calls).toEqual(["create", "prompt", "teardown:child-session"])
  })

  test("revokes child capability and tears down a child when native prompt rejects", async () => {
    const calls: string[] = []
    const client = {
      session: {
        async create() { calls.push("create"); return { data: { id: "child-session" } } },
        async prompt() { calls.push("prompt"); throw new Error("prompt rejected") },
      },
      async teardown(options: { id: string; directory: string }) { calls.push(`teardown:${options.id}`) },
    }
    const adapter = createConstructionControllerAdapter(client)
    await expect(adapter.start({ directory: "/workspace", slug: "demo", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent" })).rejects.toThrow("prompt rejected")
    expect(adapter.capabilities.bindCount()).toBe(0)
    expect(calls).toEqual(["create", "prompt", "teardown:child-session"])
  })

  test("allows a retry after rejected child startup without retaining the old capability", async () => {
    let attempts = 0
    const client = {
      session: {
        async create() { return { data: { id: `child-${++attempts}` } } },
        async prompt() { if (attempts === 1) throw new Error("first prompt rejected") },
      },
    }
    const adapter = createConstructionControllerAdapter(client)
    const request = { directory: "/workspace", slug: "demo", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent" }
    await expect(adapter.start(request)).rejects.toThrow("first prompt rejected")
    expect(adapter.capabilities.bindCount()).toBe(0)
    const retry = await adapter.start(request)
    expect(retry.child_session).toBe("child-2")
    expect(adapter.capabilities.bindCount()).toBe(1)
  })

  test("semantic repair treats a resolved SDK error envelope as child-start failure", async () => {
    const client = {
      session: {
        async create() { return { data: { id: "repair-child" } } },
        async prompt() { return { error: "repair prompt failed" } },
      },
    }
    const adapter = createConstructionControllerAdapter(client)
    const capabilities = (await import("../config/plugins/lib/construction-controller")).createSemanticRepairCapabilityService()
    await expect(adapter.startSemanticRepair({ directory: "/workspace", slug: "semantic-envelope", checkpointIdentity: "checkpoint", parentSession: "parent", opaqueFinding: "finding" }, capabilities)).rejects.toThrow("construction_child_failed")
    expect(capabilities.bindCount()).toBe(0)
    const retryClient = {
      session: {
        async create() { return { data: { id: "retry-child" } } },
        async prompt() { return undefined },
      },
    }
    const retryAdapter = createConstructionControllerAdapter(retryClient)
    await expect(retryAdapter.startSemanticRepair({ directory: "/workspace", slug: "semantic-envelope", checkpointIdentity: "checkpoint", parentSession: "parent", opaqueFinding: "finding" }, capabilities)).resolves.toMatchObject({ child_session: "retry-child" })
  })

  test("preserves prompt failure when optional teardown also rejects", async () => {
    const client = {
      session: {
        async create() { return { data: { id: "child-session" } } },
        async prompt() { throw new Error("prompt rejected") },
      },
      async teardown() { throw new Error("teardown rejected") },
    }
    const adapter = createConstructionControllerAdapter(client)
    await expect(adapter.start({ directory: "/workspace", slug: "demo", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent" })).rejects.toThrow("prompt rejected")
    expect(adapter.capabilities.bindCount()).toBe(0)
  })

  test("holds one active child admission until awaited native prompt settles", async () => {
    const gate = deferred()
    const client = fakeClient(gate)
    const adapter = createConstructionControllerAdapter(client)
    const first = adapter.start({ directory: "/workspace", slug: "demo", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent" })
    await Promise.resolve()
    await expect(adapter.start({ directory: "/workspace", slug: "demo", branchRef: "branch-2", checkpointIdentity: "checkpoint", parentSession: "parent" })).rejects.toThrow("construction_busy")
    expect(adapter.isActive("demo")).toBe(true)
    gate.resolve()
    const result = await first
    expect(result.child_session).toBe("child-session")
    expect(adapter.isActive("demo")).toBe(false)
    expect(client.calls).toEqual(["create", "prompt:child-session"])
  })

  test("native child construction capability rejects a distinct session", async () => {
    const gate = deferred()
    const client = fakeClient(gate)
    const adapter = createConstructionControllerAdapter(client)
    const started = adapter.start({ directory: "/workspace", slug: "bound", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent" })
    await Promise.resolve()
    gate.resolve()
    const result = await started
    expect(result.child_session).toBe("child-session")
    expect(() => adapter.capabilities.consume({ constructionRef: result.construction_ref, slug: "bound", branchRef: "branch", checkpointIdentity: "checkpoint", session: "other" })).toThrow("construction_scope_violation")
    expect(adapter.capabilities.consume({ constructionRef: result.construction_ref, slug: "bound", branchRef: "branch", checkpointIdentity: "checkpoint", session: "child-session" }).childSession).toBe("child-session")
  })

  test("semantic repair prompt fields use actual newlines", async () => {
    const gate = deferred()
    let promptText = ""
    const client = {
      session: {
        async create() { return { data: { id: "child-session" } } },
        async prompt(options: any) { promptText = options.body.parts[0].text; await gate.promise; return { data: {}, error: undefined } }
      },
    }
    const adapter = createConstructionControllerAdapter(client)
    const capabilities = (await import("../config/plugins/lib/construction-controller")).createSemanticRepairCapabilityService()
    const started = adapter.startSemanticRepair({ directory: "/workspace", slug: "demo", checkpointIdentity: "checkpoint", parentSession: "parent", opaqueFinding: "finding" }, capabilities)
    await Promise.resolve()
    expect(promptText).toContain("slug=demo\nsemantic_repair_ref=")
    expect(promptText).not.toContain("\\n")
    gate.resolve()
    await started
  })

  test("adapter uses native v1 child session and awaited prompt boundary", async () => {
    const gate = deferred()
    const client = fakeClient(gate)
    const adapter = createConstructionControllerAdapter(client)
    const started = adapter.start({ directory: "/workspace", slug: "demo", branchRef: "branch", checkpointIdentity: "checkpoint", parentSession: "parent" })
    await Promise.resolve()
    expect(client.calls).toEqual(["create", "prompt:child-session"])
    expect(adapter.capabilities.bindCount()).toBe(1)
    gate.resolve()
    const result = await started
    expect(result.parentSession).toBe("parent")
    expect(adapter.capabilities.bindCount()).toBe(1)
  })
})
