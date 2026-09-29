import crypto from "crypto"

type GrantRequest = {
  workspace: string
  slug: unknown
  semantic_node_id: unknown
  terminal_node_ids: unknown
  paths: unknown
  caller: unknown
  session: unknown
}

type Grant = {
  workspace: string
  slug: string
  semantic_node_id: string
  terminal_node_ids: string[]
  paths: string[]
  caller: string
  session?: string
}

const grants = new Map<string, Grant>()

function text(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) throw new Error(`scope_violation: invalid ${field}`)
  return value
}
function list(value: unknown, field: string): Set<string> {
  if (!Array.isArray(value) || value.length === 0 || value.some((item) => typeof item !== "string" || item.length === 0)) {
    throw new Error(`scope_violation: invalid ${field}`)
  }
  return new Set(value)
}
export function fixerCaller(context: Record<string, unknown>): string {
  return typeof context.agent === "string" ? context.agent : typeof context.agentName === "string" ? context.agentName : ""
}

export function createFixerCapabilityService() {
  return {
    issue(request: GrantRequest) {
      const caller = text(request.caller, "caller")
      if (caller !== "change-dag-author") throw new Error("scope_violation: only the Change-DAG-Author may issue repair grants")
      const session = request.session === undefined ? undefined : text(request.session, "session")
      const ref = crypto.randomBytes(24).toString("base64url")
      grants.set(ref, {
        workspace: text(request.workspace, "workspace"),
        slug: text(request.slug, "slug"),
        semantic_node_id: text(request.semantic_node_id, "semantic_node_id"),
        terminal_node_ids: [...list(request.terminal_node_ids, "terminal_node_ids")],
        paths: [...list(request.paths, "paths")],
        caller,
        session,
      })
      return { repair_ref: ref }
    },
    authorize(request: GrantRequest & { repair_ref: unknown; node_id: unknown; operation: unknown; path?: unknown }) {
      const ref = text(request.repair_ref, "repair_ref")
      const grant = grants.get(ref)
      if (!grant) throw new Error("unbound: unknown repair_ref")
      if (text(request.caller, "caller") !== "change-dag-fixer") throw new Error("scope_violation: fixer-only capability")
      const session = text(request.session, "session")
      if (grant.session !== undefined && session !== grant.session) throw new Error("scope_violation: repair_ref is bound to another session")
      grant.session ??= session
      if (text(request.workspace, "workspace") !== grant.workspace || text(request.slug, "slug") !== grant.slug) throw new Error("scope_violation: workspace or slug is outside grant")
      if (text(request.semantic_node_id, "semantic_node_id") !== grant.semantic_node_id) throw new Error("scope_violation: semantic boundary is outside grant")
      const node = text(request.node_id, "node_id")
      if (!grant.terminal_node_ids.includes(node)) throw new Error("scope_violation: terminal node is outside grant")
      if (request.path !== undefined && !grant.paths.includes(text(request.path, "path"))) throw new Error("scope_violation: path is outside grant")
      if (request.operation !== "update" && request.operation !== "remove") throw new Error("scope_violation: only terminal update/remove are allowed")
      return grant
    },
  }
}
