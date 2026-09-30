import crypto from "node:crypto"
import {
  projectConstructionContext,
  serializeConstructionContext,
  type ConstructionContextProjection,
  type ConstructionProjectionInput,
} from "./construction-context-projection"

export type NativeSession = { id: string }

export type NativeSessionClient = {
  session: {
    create(options: { body: { parentID: string; title: string }; query?: { directory?: string } }): Promise<{ data?: NativeSession; error?: unknown } | NativeSession>
    prompt(options: {
      path: { id: string }
      query?: { directory?: string }
      body: { agent: string; parts: Array<{ type: "text"; text: string }>; noReply?: boolean }
    }): Promise<unknown>
  }
  /** OpenCode v1 exposes no native session abort/delete/close operation to this adapter. */
  teardown?: (options: { id: string; directory: string }) => Promise<void>
}

type Capability = {
  slug: string
  branchRef: string
  parentSession: string
  checkpointIdentity: string
  childSession?: string
}

type SemanticRepairCapability = {
  slug: string
  checkpointIdentity: string
  parentSession: string
  childSession?: string
}

function required(value: unknown, name: string): string {
  if (typeof value !== "string" || value.length === 0) throw new Error(`construction_invalid: ${name} is required`)
  return value
}

async function bestEffortTeardown(client: NativeSessionClient, id: string, directory: string): Promise<void> {
  if (!client.teardown) return
  try {
    await client.teardown({ id, directory })
  } catch {
    // Prompt failure remains the primary error; teardown is deliberately best-effort.
  }
}

function createdSession(value: { data?: NativeSession } | NativeSession): NativeSession {
  const candidate = "data" in value ? value.data : value
  if (!candidate || typeof candidate.id !== "string" || candidate.id.length === 0) {
    throw new Error("construction_unavailable: session.create returned no session identity")
  }
  return candidate
}

function assertPromptSucceeded(value: unknown): void {
  if (!value || typeof value !== "object" || !("error" in value)) return
  const error = (value as { error?: unknown }).error
  if (error === undefined) return
  throw new Error(`construction_child_failed: ${typeof error === "string" ? error : JSON.stringify(error)}`)
}

export function createConstructionCapabilityService() {
  const capabilities = new Map<string, Capability>()

  return {
    issue(request: { slug: unknown; branchRef: unknown; checkpointIdentity: unknown; parentSession: unknown; childSession?: unknown }) {
      const capability: Capability = {
        slug: required(request.slug, "slug"),
        branchRef: required(request.branchRef, "branch_ref"),
        checkpointIdentity: required(request.checkpointIdentity, "checkpoint_identity"),
        parentSession: required(request.parentSession, "parent_session"),
        ...(request.childSession === undefined ? {} : { childSession: required(request.childSession, "child_session") }),
      }
      const ref = crypto.randomBytes(24).toString("base64url")
      capabilities.set(ref, capability)
      return { construction_ref: ref, ...capability }
    },

    consume(request: { constructionRef: unknown; slug: unknown; branchRef: unknown; checkpointIdentity: unknown; session: unknown }) {
      const ref = required(request.constructionRef, "construction_ref")
      const capability = capabilities.get(ref)
      if (!capability) throw new Error("construction_unbound: unknown, stale, or already consumed capability")
      if (
        required(request.slug, "slug") !== capability.slug ||
        required(request.branchRef, "branch_ref") !== capability.branchRef ||
         required(request.checkpointIdentity, "checkpoint_identity") !== capability.checkpointIdentity
       ) throw new Error("construction_scope_violation: capability does not match branch or checkpoint")
      const session = required(request.session, "session")
      if (capability.childSession !== undefined && session !== capability.childSession) throw new Error("construction_scope_violation: capability does not match the authenticated consumer session")
      capabilities.delete(ref)
      return { ...capability, childSession: capability.childSession ?? session }
    },

    revoke(constructionRef: unknown) {
      if (typeof constructionRef === "string") capabilities.delete(constructionRef)
    },

    bindCount() {
      return capabilities.size
    },
  }
}

export type ConstructionReviewOutcomeKind =
  | "PASS"
  | "EXACT_WORK_DEFECT"
  | "SEMANTIC_DEFECT"
  | "GRAPH_DEFECT"
  | "AUTHORITY_ISSUE"
  | "BLOCKED"

export type ConstructionReviewOutcome = {
  kind: ConstructionReviewOutcomeKind
  /** Backward-compatible public alias for the typed reviewer kind. */
  outcome?: ConstructionReviewOutcomeKind
  checkpointIdentity: string
  message?: string
  route?: string
  decision?: string
}

export type ConstructionReviewRequest = {
  directory: string
  slug: string
  checkpointIdentity: string
  parentSession: string
}

export type SemanticRepairRequest = ConstructionReviewRequest & {
  opaqueFinding: string
}

export type SemanticRepairOutcome = {
  checkpointIdentity: string
  childSession: string
  semanticRepairRef?: string
}

export function createSemanticRepairCapabilityService() {
  const capabilities = new Map<string, SemanticRepairCapability>()
  return {
    issue(request: { slug: unknown; checkpointIdentity: unknown; parentSession: unknown; childSession?: unknown }) {
      const capability: SemanticRepairCapability = {
        slug: required(request.slug, "slug"),
        checkpointIdentity: required(request.checkpointIdentity, "checkpoint_identity"),
        parentSession: required(request.parentSession, "parent_session"),
        ...(request.childSession === undefined ? {} : { childSession: required(request.childSession, "child_session") }),
      }
      const ref = crypto.randomBytes(24).toString("base64url")
      capabilities.set(ref, capability)
      return { semantic_repair_ref: ref }
    },
    consume(request: { repairRef: unknown; slug: unknown; checkpointIdentity: unknown; session: unknown }) {
      const ref = required(request.repairRef, "semantic_repair_ref")
      const capability = capabilities.get(ref)
      if (!capability) throw new Error("semantic_repair_unbound: unknown, stale, or already consumed capability")
      if (required(request.slug, "slug") !== capability.slug || required(request.checkpointIdentity, "checkpoint_identity") !== capability.checkpointIdentity) throw new Error("semantic_repair_scope_violation: capability does not match checkpoint")
      const session = required(request.session, "session")
      if (capability.childSession !== undefined && session !== capability.childSession) throw new Error("semantic_repair_scope_violation: capability does not match the authenticated consumer session")
      capabilities.delete(ref)
      return { ...capability, childSession: capability.childSession ?? session }
    },
    revoke(ref: unknown) { if (typeof ref === "string") capabilities.delete(ref) },
    bindCount() { return capabilities.size },
  }
}

export function createConstructionContextProjectionAdapter() {
  return {
    project(input: ConstructionProjectionInput): ConstructionContextProjection {
      return projectConstructionContext(input)
    },
    serialize(projection: ConstructionContextProjection): string {
      return serializeConstructionContext(projection)
    },
  }
}

export type ConstructionStartRequest = {
  directory: string
  slug: string
  branchRef: string
  checkpointIdentity: string
  parentSession: string
  constructionRef?: string
}

/**
 * Narrow v1 adapter: the SDK exposes native child sessions and an awaited prompt,
 * but no plugin-level Task lifecycle callback. The awaited prompt is therefore the
 * child lifetime and the adapter holds its per-slug admission until it settles.
 */
export function createConstructionReviewAdapter(
  invoke: (request: ConstructionReviewRequest) => Promise<ConstructionReviewOutcome>,
) {
  return {
    async review(request: ConstructionReviewRequest): Promise<ConstructionReviewOutcome> {
      const checkpointIdentity = required(request.checkpointIdentity, "checkpoint_identity")
      const outcome = await invoke(request)
      if (!outcome || typeof outcome !== "object" || outcome.checkpointIdentity !== checkpointIdentity) {
        throw new Error("construction_review_stale: reviewer outcome does not match the requested checkpoint")
      }
      const kinds: ConstructionReviewOutcomeKind[] = [
        "PASS", "EXACT_WORK_DEFECT", "SEMANTIC_DEFECT", "GRAPH_DEFECT", "AUTHORITY_ISSUE", "BLOCKED",
      ]
      if (!kinds.includes(outcome.kind)) throw new Error("construction_review_invalid: unknown reviewer outcome")
      return outcome
    },
  }
}

export function createSemanticRepairAdapter(
  invoke: (request: SemanticRepairRequest) => Promise<SemanticRepairOutcome>,
) {
  return {
    async invoke(request: SemanticRepairRequest): Promise<SemanticRepairOutcome> {
      const checkpointIdentity = required(request.checkpointIdentity, "checkpoint_identity")
      required(request.opaqueFinding, "opaque_finding")
      const outcome = await invoke(request)
      if (!outcome || outcome.checkpointIdentity !== checkpointIdentity || typeof outcome.childSession !== "string" || outcome.childSession.length === 0) {
        throw new Error("semantic_repair_stale: repair outcome does not match the requested checkpoint or child identity")
      }
      return outcome
    },
  }
}

export function createConstructionControllerAdapter(client: NativeSessionClient, capabilityService = createConstructionCapabilityService()) {
  const active = new Set<string>()
  const capabilities = capabilityService

  return {
    capabilities,
    async start(request: ConstructionStartRequest) {
      const directory = required(request.directory, "directory")
      const slug = required(request.slug, "slug")
      const branchRef = required(request.branchRef, "branch_ref")
      required(request.checkpointIdentity, "checkpoint_identity")
      const parentSession = required(request.parentSession, "parent_session")
      if (active.has(slug)) throw new Error("construction_busy: one child is already active for this DAG")
      active.add(slug)
      try {
        const child = createdSession(await client.session.create({
          query: { directory },
          body: { parentID: parentSession, title: `Change-DAG Worker: ${slug}` },
        }))
        const issued = capabilities.issue({ slug, branchRef, checkpointIdentity: request.checkpointIdentity, parentSession, childSession: child.id })
        try {
          const promptResult = await client.session.prompt({
          query: { directory },
          path: { id: child.id },
          body: {
            agent: "change-dag-worker",
parts: [{
               type: "text",
               text: [
                `Resolve the supplied opaque branch_ref through dag_worker_resolve; do not choose a node.`,
                `slug=${slug}`,
                `branch_ref=${branchRef}`,
`construction_ref=${issued.construction_ref}`,
                 `checkpoint_identity=${request.checkpointIdentity}`,
               ].join("\n"),
             }],
          },
          })
          assertPromptSucceeded(promptResult)
          } catch (error) {
           capabilities.revoke(issued.construction_ref)
           await bestEffortTeardown(client, child.id, directory)
           throw error
         }
        return { ...issued, child_session: child.id }
      } finally {
        active.delete(slug)
      }
    },
    async startSemanticRepair(request: SemanticRepairRequest, repairCapabilities: ReturnType<typeof createSemanticRepairCapabilityService>) {
      const directory = required(request.directory, "directory")
      const slug = required(request.slug, "slug")
      const checkpointIdentity = required(request.checkpointIdentity, "checkpoint_identity")
      const parentSession = required(request.parentSession, "parent_session")
      const opaqueFinding = required(request.opaqueFinding, "opaque_finding")
      if (active.has(slug)) throw new Error("construction_busy: one child is already active for this DAG")
      active.add(slug)
      try {
        const child = createdSession(await client.session.create({ query: { directory }, body: { parentID: parentSession, title: `Change-DAG Semantic Repair: ${slug}` } }))
        const issued = repairCapabilities.issue({ slug, checkpointIdentity, parentSession, childSession: child.id })
        try {
          const promptResult = await client.session.prompt({ query: { directory }, path: { id: child.id }, body: {
            agent: "change-dag-semantic-repairer",
             parts: [{ type: "text", text: [`Resolve the opaque semantic_repair_ref through the controller boundary.`, `slug=${slug}`, `semantic_repair_ref=${issued.semantic_repair_ref}`, `checkpoint_identity=${checkpointIdentity}`, `finding=${opaqueFinding}`].join("\n") }],
          } })
          assertPromptSucceeded(promptResult)
          } catch (error) {
           repairCapabilities.revoke(issued.semantic_repair_ref)
           await bestEffortTeardown(client, child.id, directory)
           throw error
         }
        return { ...issued, child_session: child.id, checkpoint_identity: checkpointIdentity }
      } finally { active.delete(slug) }
    },
    isActive(slug: string) {
      return active.has(slug)
    },
  }
}
