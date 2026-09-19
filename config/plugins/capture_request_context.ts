import { tool, type PluginInput, type ToolContext } from "@opencode-ai/plugin"
import { randomInt } from "node:crypto"
import { mkdir, open } from "node:fs/promises"
import path from "node:path"

export type CaptureArgs = { from: string }

type SessionMessage = {
  info: Record<string, unknown>
  parts: unknown[]
}

type VisibleMessage = {
  id: string
  role: "user" | "assistant"
  text: string
  completed: boolean
}

export type TranscriptProjection = {
  sessionId: string
  anchorMessageId: string
  boundaryMessageId: string
  messages: Array<{ role: "user" | "assistant"; text: string; id: string }>
}

const KNOWN_NON_TEXT_PARTS = new Set([
  "tool",
  "reasoning",
  "subtask",
  "compaction",
  "step-start",
  "step-finish",
  "file",
  "patch",
  "snapshot",
  "agent",
  "retry",
])

/** Normalize only ECMAScript Unicode White_Space runs for anchor equality. */
export function normalizeForAnchor(value: string): string {
  return value.replace(/\p{White_Space}+/gu, " ").trim()
}

function fail(code: string, message: string): never {
  throw new Error(`${code}: ${message}`)
}

function requiredString(value: unknown, name: string): string {
  if (typeof value !== "string" || value.length === 0) {
    fail("history_ambiguous", `${name} is missing or malformed`)
  }
  return value
}

function sessionIdFromInfo(info: Record<string, unknown>): string {
  const sessionId = info.sessionID ?? info.sessionId
  return requiredString(sessionId, "message session id")
}

function messageIdFromInfo(info: Record<string, unknown>): string {
  return requiredString(info.id ?? info.messageID ?? info.messageId, "message id")
}

function roleFromInfo(info: Record<string, unknown>): "user" | "assistant" | "excluded" {
  if (info.role === "user" || info.role === "assistant") return info.role
  if (info.role === "system" || info.role === "developer" || info.role === "internal") return "excluded"
  fail("history_ambiguous", "unknown message role")
}

function isCompleted(info: Record<string, unknown>, role: "user" | "assistant"): boolean {
  if (role === "user") return true
  const time = info.time
  if (typeof time !== "object" || time === null) return false
  const completed = (time as Record<string, unknown>).completed
  return typeof completed === "number" && Number.isFinite(completed)
}

function visibleText(parts: unknown[]): string {
  let text = ""
  for (const rawPart of parts) {
    if (typeof rawPart !== "object" || rawPart === null) {
      fail("history_ambiguous", "malformed message part")
    }
    const part = rawPart as Record<string, unknown>
    const type = part.type
    if (type === "text") {
      if (typeof part.text !== "string") fail("history_ambiguous", "malformed text part")
      if (part.synthetic === true || part.ignored === true) {
        continue
      }
      if (part.synthetic !== undefined && part.synthetic !== false) {
        fail("history_ambiguous", "ambiguous text visibility")
      }
      if (part.ignored !== undefined && part.ignored !== false) {
        fail("history_ambiguous", "ambiguous text visibility")
      }
      text += part.text
      continue
    }
    if (typeof type !== "string") fail("history_ambiguous", "unknown message part")
    if (!KNOWN_NON_TEXT_PARTS.has(type)) fail("history_ambiguous", "unknown message part")
  }
  return text
}

function parseResponse(value: unknown): SessionMessage[] {
  if (!Array.isArray(value) || value.length === 0) fail("history_unavailable", "history is unavailable")
  return value.map((entry) => {
    if (typeof entry !== "object" || entry === null) {
      fail("history_ambiguous", "malformed history record")
    }
    const record = entry as Record<string, unknown>
    if (typeof record.info !== "object" || record.info === null || !Array.isArray(record.parts)) {
      fail("history_ambiguous", "malformed history record")
    }
    return { info: record.info as Record<string, unknown>, parts: record.parts }
  })
}

function historyData(response: unknown): unknown {
  if (typeof response !== "object" || response === null) fail("history_unavailable", "history response is unavailable")
  const envelope = response as Record<string, unknown>
  if ("error" in envelope && envelope.error !== undefined) fail("history_unavailable", "history API returned an error")
  if (!("data" in envelope)) fail("history_unavailable", "history response has no data")
  return envelope.data
}

/** Project one supported session.messages response into the exact visible transcript. */
export function projectHistory(
  response: unknown,
  args: CaptureArgs,
  sessionId: string,
  invocationMessageId: string,
): TranscriptProjection {
  if (typeof args !== "object" || args === null || typeof args.from !== "string") {
    fail("invalid_input", "from must be a string")
  }
  const normalizedFrom = normalizeForAnchor(args.from)
  if (!normalizedFrom) fail("invalid_input", "from must not be empty")
  const records = parseResponse(historyData(response))
  const messages: VisibleMessage[] = []

  for (const record of records) {
    const id = messageIdFromInfo(record.info)
    if (sessionIdFromInfo(record.info) !== sessionId) fail("history_ambiguous", "wrong session ownership")
    const role = roleFromInfo(record.info)
    const text = visibleText(record.parts)
    if (role === "excluded") continue
    if (!text) continue
    messages.push({ id, role, text, completed: isCompleted(record.info, role) })
  }

  const invocationIndex = messages.findIndex((message) => message.id === invocationMessageId)
  if (invocationIndex < 0) fail("history_ambiguous", "invocation boundary is unavailable")
  if (messages[invocationIndex].role !== "user") fail("history_ambiguous", "invocation boundary is not a user message")
  const beforeInvocation = messages.slice(0, invocationIndex + 1)
  if (beforeInvocation.some((message) => !message.completed)) {
    fail("history_ambiguous", "pre-invocation completion boundary is unavailable")
  }

  const anchors = beforeInvocation.filter(
    (message) => message.role === "user" && normalizeForAnchor(message.text) === normalizedFrom,
  )
  if (anchors.length !== 1) fail("history_ambiguous", "anchor is absent or ambiguous")
  const anchorIndex = beforeInvocation.findIndex((message) => message.id === anchors[0].id)
  const selected = beforeInvocation.slice(anchorIndex)
  const boundary = selected[selected.length - 1]
  return {
    sessionId,
    anchorMessageId: anchors[0].id,
    boundaryMessageId: boundary.id,
    messages: selected.map(({ id, role, text }) => ({ id, role, text })),
  }
}

function jsonValue(value: string): string {
  return JSON.stringify(value)
}

/** Serialize the complete artifact in memory; this function does not publish it. */
export function serializeTranscript(projection: TranscriptProjection): Uint8Array {
  const lines = [
    "# Request Context",
    "",
    "## Provenance",
    "",
    '- artifact_kind: "request_context"',
    `- session_id: ${jsonValue(projection.sessionId)}`,
    `- anchor_message_id: ${jsonValue(projection.anchorMessageId)}`,
    `- boundary_message_id: ${jsonValue(projection.boundaryMessageId)}`,
    "",
    "## Transcript",
    "",
  ]
  for (const message of projection.messages) {
    const label = message.role.toUpperCase()
    const byteLength = new TextEncoder().encode(message.text).byteLength
    lines.push(`### ${label}`, "", `- text_bytes_utf8: ${byteLength}`, "- text:", message.text, "---", "")
  }
  return new TextEncoder().encode(lines.join("\n"))
}

/** Read the supported current-session history exactly once and project it. */
export async function captureRequestContext(
  input: PluginInput,
  args: CaptureArgs,
  context: ToolContext,
): Promise<{ projection: TranscriptProjection; bytes: Uint8Array }> {
  if (typeof context.sessionID !== "string" || !context.sessionID) {
    fail("invalid_input", "official session context is unavailable")
  }
  if (typeof context.messageID !== "string" || !context.messageID) {
    fail("invalid_input", "official invocation boundary is unavailable")
  }
  // Official PluginInput.client.session.messages accepts the current session path
  // and invocation directory; no private storage or fallback reader is used.
  if (!input.client?.session?.messages) fail("history_unavailable", "session history API is unavailable")
  let response: unknown
  try {
    response = await input.client.session.messages({
      path: { id: context.sessionID },
      query: { directory: context.directory },
    })
  } catch (error) {
    fail("history_unavailable", error instanceof Error ? error.message : "history read failed")
  }
  const projection = projectHistory(response, args, context.sessionID, context.messageID)
  return { projection, bytes: serializeTranscript(projection) }
}

const MAX_CREATE_ATTEMPTS = 5
const ADJECTIVES = ["amber", "brisk", "calm", "clear", "eager", "gentle", "quiet", "steady"]
const NOUNS = ["beacon", "bridge", "canyon", "garden", "harbor", "meadow", "summit", "window"]

type FileSystemError = { code?: unknown }

/** Generate a filesystem-safe adjective+noun slug without using request content. */
export function generateContextSlug(): string {
  return `${ADJECTIVES[randomInt(ADJECTIVES.length)]}-${NOUNS[randomInt(NOUNS.length)]}`
}

function isCollision(error: unknown): boolean {
  return error instanceof Error && (error as FileSystemError).code === "EEXIST"
}

/** Publish already-serialized bytes through one bounded exclusive final create. */
export async function publishContextArtifact(bytes: Uint8Array, directory: string): Promise<string> {
  if (!directory) throw new Error("invalid_input: workspace directory is unavailable")
  const requestDirectory = path.join(directory, "artifacts", "requests")
  try {
    await mkdir(requestDirectory, { recursive: true })
  } catch (error) {
    throw new Error(`write_failed: unable to create artifact directory: ${error instanceof Error ? error.message : String(error)}`)
  }

  for (let attempt = 0; attempt < MAX_CREATE_ATTEMPTS; attempt += 1) {
    const artifactPath = path.join(requestDirectory, `CTX_${generateContextSlug()}.md`)
    let handle: Awaited<ReturnType<typeof open>>
    try {
      handle = await open(artifactPath, "wx")
    } catch (error) {
      if (isCollision(error)) continue
      throw new Error(`write_failed: unable to create artifact: ${error instanceof Error ? error.message : String(error)}`)
    }

    try {
      const result = await handle.write(bytes)
      if (result.bytesWritten !== bytes.byteLength) {
        throw new Error(`short write (${result.bytesWritten}/${bytes.byteLength} bytes)`)
      }
      await handle.close()
      return artifactPath
    } catch (error) {
      try {
        await handle.close()
      } catch {
        // The original write/close failure is the authoritative failure.
      }
      throw new Error(`write_failed: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  throw new Error("write_collision_exhausted: artifact destination collisions exceeded retry limit")
}

/** Native tool factory closed over the official plugin client. */
export function createCaptureRequestContextTool(input: PluginInput) {
  return tool({
    description: "Capture the visible current-session request context into a fresh artifact.",
    args: {
      from: tool.schema.string().describe("Exact visible user message anchor"),
    },
    async execute(args: CaptureArgs, context: ToolContext) {
      const { bytes } = await captureRequestContext(input, args, context)
      return publishContextArtifact(bytes, context.directory)
    },
  })
}
