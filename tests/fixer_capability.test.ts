import { describe, expect, test } from "bun:test"
import { createFixerCapabilityService } from "../config/plugins/lib/fixer-capability"

describe("Fixer capability binding", () => {
  const request = {
    workspace: "/workspace",
    slug: "repair-dag",
    semantic_node_id: "N1",
    terminal_node_ids: ["N2"],
    paths: ["src/a.ts"],
    caller: "change-dag-author",
    session: "author-session",
  }

  test("issues opaque grant only to Author and binds it to one session", () => {
    const service = createFixerCapabilityService()
    const { repair_ref } = service.issue(request)
    expect(repair_ref).toMatch(/^[A-Za-z0-9_-]{32}$/)
    expect(() => service.issue({ ...request, caller: "change-dag-fixer" })).toThrow("scope_violation")
    expect(service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", operation: "update", node_id: "N2", path: "src/a.ts" })).toBeDefined()
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "other-session", operation: "update", node_id: "N2", path: "src/a.ts" })).toThrow("scope_violation")
  })

  test("rejects unknown, semantic, and out-of-scope mutations", () => {
    const service = createFixerCapabilityService()
    const { repair_ref } = service.issue(request)
    expect(() => service.authorize({ repair_ref: "unknown", ...request, caller: "change-dag-fixer", session: "fixer", operation: "remove", node_id: "N2" })).toThrow("unbound")
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "fixer", operation: "add", node_id: "N2" })).toThrow("scope_violation")
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "fixer", operation: "update", node_id: "N3", path: "src/a.ts" })).toThrow("scope_violation")
    expect(() => service.authorize({ repair_ref, ...request, caller: "change-dag-fixer", session: "fixer", operation: "update", node_id: "N2", path: "src/b.ts" })).toThrow("scope_violation")
  })
})
