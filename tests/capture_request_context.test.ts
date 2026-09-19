import { afterEach, describe, expect, test } from "bun:test"
import { mkdtemp, mkdir, readFile, rm, symlink, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { ToolsPlugin } from "../config/plugins/tools"
import {
  captureRequestContext,
  normalizeForAnchor,
  projectHistory,
  publishContextArtifact,
  serializeTranscript,
} from "../config/plugins/capture_request_context"

type RecordShape = {
  info: Record<string, unknown>
  parts: Array<Record<string, unknown>>
}

const SESSION = "ses_test"
const tempRoots: string[] = []

async function tempRoot(): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), "capture-request-context-"))
  tempRoots.push(root)
  return root
}

function message(
  id: string,
  role: "user" | "assistant" | "system" | "developer" | "internal",
  text: string,
  options: Record<string, unknown> = {},
): RecordShape {
  return {
    info: { id, sessionID: SESSION, role, ...(role === "assistant" ? { time: { completed: 1 } } : {}), ...options },
    parts: [{ type: "text", text }],
  }
}

function history(records: RecordShape[], error?: unknown) {
  return error === undefined ? { data: records } : { data: undefined, error }
}

function supportedHistory(anchor = "  Request\n\twith **Markdown**  ", invocation = "invoke") {
  return history([
    message("anchor", "user", anchor),
    message("assistant", "assistant", "answer\r\nwith Unicode: café 😀"),
    {
      info: { id: "excluded", sessionID: SESSION, role: "assistant", time: { completed: 1 } },
      parts: [
        { type: "tool", callID: "tool-1" },
        { type: "reasoning", text: "private reasoning" },
        { type: "text", text: "internal-looking text", synthetic: true },
      ],
    },
    message("invocation", "user", invocation),
  ])
}

function context(directory: string, messageID = "invocation") {
  return { sessionID: SESSION, messageID, directory } as never
}

const clients = (response: unknown, calls: { count: number } = { count: 0 }) => ({
  calls,
  client: {
    session: {
      messages: async () => {
        calls.count += 1
        return response
      },
    },
  },
})

afterEach(async () => {
  await Promise.all(tempRoots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
})

describe("capture_request_context", () => {
  test("registers exactly one native tool with only from and returns its artifact path", async () => {
    const root = await tempRoot()
    const calls = { count: 0 }
    const input = clients(supportedHistory(), calls)
    const plugin = await ToolsPlugin(input as never)
    const capture = plugin.tool.capture_request_context as { args: Record<string, unknown>; execute: Function }

    expect(Object.keys(plugin.tool).filter((name) => name === "capture_request_context")).toEqual(["capture_request_context"])
    expect(Object.keys(capture.args)).toEqual(["from"])
    const artifactPath = await capture.execute({ from: "Request with **Markdown**" }, context(root))

    expect(artifactPath).toMatch(new RegExp(`${root}/artifacts/requests/CTX_[a-z]+-[a-z]+\\.md$`))
    expect(calls.count).toBe(1)
    expect(await readFile(artifactPath, "utf8")).toContain("# Request Context")
  })

  test("validates input before the one history read", async () => {
    const calls = { count: 0 }
    const input = clients(supportedHistory(), calls)
    await expect(captureRequestContext(input as never, { from: " \t\n" }, context("/tmp"))).rejects.toThrow("invalid_input")
    expect(calls.count).toBe(0)
    await expect(captureRequestContext(input as never, { from: 4 } as never, context("/tmp"))).rejects.toThrow("invalid_input")
    expect(calls.count).toBe(0)
  })

  test("normalizes only White_Space for unique matching and preserves original text", () => {
    expect(normalizeForAnchor("\u00a0Request\u2003\nwith\ttext\uFEFF")).toBe("Request with text\uFEFF")
    const projection = projectHistory(supportedHistory(), { from: " Request with **Markdown** " }, SESSION, "invocation")
    expect(projection.anchorMessageId).toBe("anchor")
    expect(projection.messages[0]?.text).toBe("  Request\n\twith **Markdown**  ")
  })

  test("projects exact visible text in order and excludes known non-visible content", () => {
    const projection = projectHistory(supportedHistory(), { from: "Request with **Markdown**" }, SESSION, "invocation")
    expect(projection.messages.map(({ id, role }) => `${id}:${role}`)).toEqual([
      "anchor:user",
      "assistant:assistant",
      "invocation:user",
    ])
    expect(projection.messages[1]?.text).toContain("café 😀")
  })

  test("requires exact current-session ownership, ordering, completion, and one anchor", () => {
    const cases: Array<[string, unknown]> = [
      ["wrong session", history([message("anchor", "user", "Request"), message("invocation", "user", "invoke", { sessionID: "other" })])],
      ["missing invocation", history([message("anchor", "user", "Request")])],
      ["incomplete assistant", history([message("anchor", "user", "Request"), message("assistant", "assistant", "pending", { time: {} }), message("invocation", "user", "invoke")])],
      ["zero anchors", history([message("other", "user", "Other"), message("invocation", "user", "invoke")])],
      ["multiple anchors", history([message("a", "user", "Request"), message("b", "user", " Request "), message("invocation", "user", "invoke")])],
      ["excluded internal", history([message("a", "user", "Request"), message("x", "internal", "private"), message("invocation", "user", "invoke")])],
      ["unknown role", history([message("a", "user", "Request"), { info: { id: "x", sessionID: SESSION, role: "future-role", time: { completed: 1 } }, parts: [] }, message("invocation", "user", "invoke")])],
      ["unknown part", history([message("a", "user", "Request"), { info: { id: "x", sessionID: SESSION, role: "assistant", time: { completed: 1 } }, parts: [{ type: "future-part" }] }, message("invocation", "user", "invoke")])],
    ]
    for (const [label, response] of cases) {
      expect(() => projectHistory(response, { from: "Request" }, SESSION, "invocation"), label).toThrow()
    }
  })

  test("fails closed for SDK errors, unavailable data, malformed records, and unsupported boundary", async () => {
    const root = await tempRoot()
    const cases = [
      history([], "unavailable"),
      { error: "transport" },
      { data: [{ info: {}, parts: [] }] },
      history([message("anchor", "user", "Request"), message("invocation", "user", "invoke")]),
    ]
    for (const response of cases) {
      const input = clients(response)
      await expect(captureRequestContext(input as never, { from: "Request" }, context(root))).rejects.toThrow()
    }
    expect((await import("node:fs/promises")).readdir(path.join(root, "artifacts")).catch(() => [])).resolves.toEqual([])
  })

  test("serializes exact UTF-8 bytes and mechanical provenance without summary or handoff_goal", () => {
    const projection = projectHistory(supportedHistory(), { from: "Request with **Markdown**" }, SESSION, "invocation")
    const text = new TextDecoder().decode(serializeTranscript(projection))
    expect(text).toContain("text_bytes_utf8: 32")
    expect(text).toContain("\r\nwith Unicode: café 😀")
    expect(text).toContain('artifact_kind: "request_context"')
    expect(text).not.toContain("summary")
    expect(text).not.toContain("handoff_goal")
    expect(text).not.toContain("interpretation")
  })

  test("publishes fresh independent write-once artifacts and never overwrites or follows symlinks", async () => {
    const root = await tempRoot()
    const bytes = new TextEncoder().encode("exact\nbytes")
    const first = await publishContextArtifact(bytes, root)
    const second = await publishContextArtifact(bytes, root)
    expect(second).not.toBe(first)
    expect(await readFile(first, "utf8")).toBe("exact\nbytes")
    expect(await readFile(second, "utf8")).toBe("exact\nbytes")

    const requests = path.join(root, "artifacts", "requests")
    const symlinkTarget = path.join(requests, "target.md")
    const symlinkPath = path.join(requests, "CTX_amber-beacon.md")
    await writeFile(symlinkTarget, "do not overwrite")
    await symlink(symlinkTarget, symlinkPath)
    expect(await readFile(symlinkPath, "utf8")).toBe("do not overwrite")
  })

  test("exhausts observed final-name collisions without overwriting", async () => {
    const root = await tempRoot()
    const requests = path.join(root, "artifacts", "requests")
    await mkdir(requests, { recursive: true })
    const adjectives = ["amber", "brisk", "calm", "clear", "eager", "gentle", "quiet", "steady"]
    const nouns = ["beacon", "bridge", "canyon", "garden", "harbor", "meadow", "summit", "window"]
    await Promise.all(
      adjectives.flatMap((adjective) =>
        nouns.map((noun) => writeFile(path.join(requests, `CTX_${adjective}-${noun}.md`), "existing")),
      ),
    )
    await expect(publishContextArtifact(new TextEncoder().encode("new"), root)).rejects.toThrow("write_collision_exhausted")
  })

  test("fails without publishing when the artifact directory cannot be created", async () => {
    const root = await tempRoot()
    await mkdir(path.join(root, "artifacts"), { recursive: true })
    await writeFile(path.join(root, "artifacts", "requests"), "not a directory")
    await expect(publishContextArtifact(new TextEncoder().encode("x"), root)).rejects.toThrow("write_failed")
  })
})
