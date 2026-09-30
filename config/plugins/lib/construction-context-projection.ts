export type ConstructionContextKind =
  | "routine"
  | "semantic_delta"
  | "repair_finding"
  | "repair_result"
  | "reviewer_finding"
  | "authority_escalation"

export type ConstructionContextEvent = {
  id: string
  kind: ConstructionContextKind
  checkpointIdentity: string
  content?: string
  opaque?: Record<string, string>
  order: number
}

export type ConstructionProjectionInput = {
  checkpointIdentity: string
  frontierIdentity: string
  nextAction: string
  events?: readonly ConstructionContextEvent[]
  opaqueCapabilities?: Record<string, string>
}

export type ConstructionContextEntry = {
  id: string
  content: string
  opaque: Readonly<Record<string, string>>
}

export type ConstructionContextProjection = {
  checkpointIdentity: string
  frontierIdentity: string
  nextAction: string
  semanticDeltas: readonly ConstructionContextEntry[]
  repairFindings: readonly ConstructionContextEntry[]
  repairResults: readonly ConstructionContextEntry[]
  reviewerFindings: readonly ConstructionContextEntry[]
  authorityEscalations: readonly ConstructionContextEntry[]
  opaqueCapabilities: Readonly<Record<string, string>>
}

const MEANINGFUL_KINDS = new Set<ConstructionContextKind>([
  "semantic_delta",
  "repair_finding",
  "repair_result",
  "reviewer_finding",
  "authority_escalation",
])
const MAX_EVENTS = 8
const MAX_TEXT = 512
const MAX_CAPABILITIES = 8
const MAX_OUTPUT = 8192

function required(value: unknown, name: string): string {
  if (typeof value !== "string" || value.length === 0 || value.length > MAX_TEXT) {
    throw new Error(`construction_context_invalid: ${name} is malformed`)
  }
  return value
}

function validateOpaque(value: unknown, name: string): Record<string, string> {
  if (value === undefined) return {}
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`construction_context_invalid: ${name} is malformed`)
  }
  const entries = Object.entries(value)
  if (entries.length > MAX_CAPABILITIES) throw new Error(`construction_context_invalid: ${name} is unbounded`)
  const result: Record<string, string> = {}
  for (const [key, item] of entries.sort(([left], [right]) => left.localeCompare(right))) {
    result[required(key, `${name} key`)] = required(item, `${name}.${key}`)
  }
  return result
}

/**
 * Build the bounded controller-to-model context without consulting native history.
 * Routine transport chatter is discarded; meaningful records are checkpoint-bound.
 */
export function projectConstructionContext(input: ConstructionProjectionInput): ConstructionContextProjection {
  const checkpointIdentity = required(input?.checkpointIdentity, "checkpoint_identity")
  const frontierIdentity = required(input?.frontierIdentity, "frontier_identity")
  const nextAction = required(input?.nextAction, "next_action")
  const rawEvents = input?.events ?? []
  if (!Array.isArray(rawEvents) || rawEvents.length > MAX_EVENTS) {
    throw new Error("construction_context_invalid: events are malformed or unbounded")
  }

  const buckets: Record<Exclude<ConstructionContextKind, "routine">, ConstructionContextEntry[]> = {
    semantic_delta: [],
    repair_finding: [],
    repair_result: [],
    reviewer_finding: [],
    authority_escalation: [],
  }
  const events = [...rawEvents].sort((left, right) => {
    if (!left || typeof left !== "object" || !right || typeof right !== "object") return 0
    const leftEvent = left as ConstructionContextEvent
    const rightEvent = right as ConstructionContextEvent
    return leftEvent.order - rightEvent.order || leftEvent.id.localeCompare(rightEvent.id)
  })

  for (const event of events) {
    if (!event || typeof event !== "object" || typeof event.id !== "string" || !Number.isSafeInteger(event.order)) {
      throw new Error("construction_context_invalid: event identity is malformed")
    }
    if (event.kind !== "routine" && !MEANINGFUL_KINDS.has(event.kind)) {
      throw new Error("construction_context_invalid: event kind is malformed")
    }
    if (event.checkpointIdentity !== checkpointIdentity) {
      throw new Error("construction_context_stale: event checkpoint does not match current checkpoint")
    }
    const content = required(event.content, `event ${event.id} content`)
    const opaque = validateOpaque(event.opaque, `event ${event.id} opaque`)
    if (event.kind === "routine") continue
    buckets[event.kind].push({ id: event.id, content, opaque })
  }

  const projection: ConstructionContextProjection = {
    checkpointIdentity,
    frontierIdentity,
    nextAction,
    semanticDeltas: buckets.semantic_delta,
    repairFindings: buckets.repair_finding,
    repairResults: buckets.repair_result,
    reviewerFindings: buckets.reviewer_finding,
    authorityEscalations: buckets.authority_escalation,
    opaqueCapabilities: validateOpaque(input.opaqueCapabilities, "opaque_capabilities"),
  }
  if (JSON.stringify(projection).length > MAX_OUTPUT) {
    throw new Error("construction_context_invalid: projected context exceeds bound")
  }
  return projection
}

export function serializeConstructionContext(projection: ConstructionContextProjection): string {
  return JSON.stringify(projection)
}
