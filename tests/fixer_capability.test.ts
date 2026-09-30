import { describe, expect, test } from "bun:test"
import { createFixerCapabilityService } from "../config/plugins/lib/fixer-capability"

describe("Fixer capability binding", () => {
  const request = {
    workspace: "/workspace",
    slug: "repair-dag",
    semantic_node_id: "N1",
    terminal_node_ids: ["N2"],
    paths: ["src/a.ts"],
  caller: "nyx",
  parent_session: "controller-session",
  checkpoint_identity: "checkpoint",
  }

  test("binds an opaque Nyx grant once to a distinct dispatched fixer child", () => {
    const service = createFixerCapabilityService()
    const { repair_ref } = service.issue(request)
    expect(repair_ref).toMatch(/^[A-Za-z0-9_-]{32}$/)
    expect(() => service.issue({ ...request, caller: "change-dag-author" })).toThrow("scope_violation")
    const intended = service.issue({ ...request, intended_child_session: "intended-fixer" })
    const grant = service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "fixer-session", checkpoint_identity: "checkpoint", operation: "update", node_id: "N2", path: "src/a.ts" })
    expect(grant.parent_session).toBe("controller-session")
    expect(() => service.authorize({ repair_ref: intended.repair_ref, ...request, caller: "change-dag-fixer", session: "other-fixer", checkpoint_identity: "checkpoint", operation: "update", node_id: "N2", path: "src/a.ts" })).toThrow("scope_violation")
    expect(service.authorize({ repair_ref: intended.repair_ref, ...request, caller: "change-dag-fixer", session: "intended-fixer", checkpoint_identity: "checkpoint", operation: "update", node_id: "N2", path: "src/a.ts" })).toBeDefined()
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "fixer-session", checkpoint_identity: "checkpoint", operation: "update", node_id: "N2", path: "src/a.ts" })).toThrow("unbound")
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "other-session", checkpoint_identity: "checkpoint", operation: "update", node_id: "N2", path: "src/a.ts" })).toThrow("unbound")
  })

  test("rejects unknown, semantic, and out-of-scope mutations", () => {
    const service = createFixerCapabilityService()
    const { repair_ref } = service.issue(request)
    expect(() => service.authorize({ repair_ref: "unknown", ...request, caller: "change-dag-fixer", session: "fixer", checkpoint_identity: "checkpoint", operation: "remove", node_id: "N2" })).toThrow("unbound")
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "fixer", checkpoint_identity: "checkpoint", operation: "add", node_id: "N2" })).toThrow("scope_violation")
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "fixer", checkpoint_identity: "checkpoint", operation: "update", node_id: "N3", path: "src/a.ts" })).toThrow("scope_violation")
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "fixer", checkpoint_identity: "checkpoint", operation: "update", node_id: "N2", path: "src/b.ts" })).toThrow("scope_violation")
  })
})
