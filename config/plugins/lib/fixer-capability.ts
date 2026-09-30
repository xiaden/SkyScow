import crypto from "crypto"

type GrantRequest = {
  workspace: string
  slug: unknown
  semantic_node_id: unknown
  terminal_node_ids: unknown
  paths: unknown
  caller: unknown
  session?: unknown
  parent_session?: unknown
  checkpoint_identity: unknown
  intended_child_session?: unknown
}

type Grant = {
  workspace: string
  slug: string
  semantic_node_id: string
  terminal_node_ids: string[]
  paths: string[]
  caller: string
  session?: string
  parent_session: string
  checkpoint_identity: string
  intended_child_session?: string
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
      if (caller !== "nyx") throw new Error("scope_violation: only Nyx may issue repair grants")
      const session = request.session === undefined ? undefined : text(request.session, "session")
      const intendedChildSession = request.intended_child_session === undefined ? undefined : text(request.intended_child_session, "intended_child_session")
      const ref = crypto.randomBytes(24).toString("base64url")
      grants.set(ref, {
        workspace: text(request.workspace, "workspace"),
        slug: text(request.slug, "slug"),
        semantic_node_id: text(request.semantic_node_id, "semantic_node_id"),
        terminal_node_ids: [...list(request.terminal_node_ids, "terminal_node_ids")],
        paths: [...list(request.paths, "paths")],
        caller,
        session,
        parent_session: text(request.parent_session, "parent_session"),
        checkpoint_identity: text(request.checkpoint_identity, "checkpoint_identity"),
        ...(intendedChildSession === undefined ? {} : { intended_child_session: intendedChildSession }),
      })
      return { repair_ref: ref }
    },
    authorize(request: GrantRequest & { repair_ref: unknown; node_id: unknown; operation: unknown; path?: unknown }) {
      const ref = text(request.repair_ref, "repair_ref")
      const grant = grants.get(ref)
      if (!grant) throw new Error("unbound: unknown repair_ref")
      if (text(request.caller, "caller") !== "change-dag-fixer") throw new Error("scope_violation: fixer-only capability")
      const session = text(request.session, "session")
      if (grant.intended_child_session !== undefined && grant.intended_child_session !== session) throw new Error("scope_violation: repair_ref is not intended for this child session")
      if (grant.session !== undefined && grant.session !== session) throw new Error("scope_violation: repair_ref is bound to another session")
      if (text(request.checkpoint_identity, "checkpoint_identity") !== grant.checkpoint_identity) throw new Error("scope_violation: repair_ref is outside its controller checkpoint")
      if (text(request.workspace, "workspace") !== grant.workspace || text(request.slug, "slug") !== grant.slug) throw new Error("scope_violation: workspace or slug is outside grant")
      if (text(request.semantic_node_id, "semantic_node_id") !== grant.semantic_node_id) throw new Error("scope_violation: semantic boundary is outside grant")
      const node = text(request.node_id, "node_id")
      if (!grant.terminal_node_ids.includes(node)) throw new Error("scope_violation: terminal node is outside grant")
      if (request.path !== undefined && !grant.paths.includes(text(request.path, "path"))) throw new Error("scope_violation: path is outside grant")
      if (request.operation !== "update" && request.operation !== "remove") throw new Error("scope_violation: only terminal update/remove are allowed")
      grant.session = session
      grants.delete(ref)
      return grant
    },
  }
}
