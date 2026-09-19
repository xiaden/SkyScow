# Custom Tools

Plugins can add custom tools that appear in the agent's tool set.

---

## Table of Contents

- [Basic Custom Tool](#basic-custom-tool)
- [Shipped Native Tool: `capture_request_context`](#shipped-native-tool-capture_request_context)
- [Tool Result Type](#tool-result-type)
- [Common Mistakes](#common-mistakes)
- [Full Example with Error Handling](#full-example-with-error-handling)
- [Args Schema Helpers](#args-schema-helpers)

---

## Basic Custom Tool

```typescript
import { type Plugin, tool } from "@opencode-ai/plugin"

export const CustomToolsPlugin: Plugin = async (ctx) => {
  return {
    tool: {
      mytool: tool({
        description: "This is a custom tool",
        args: {
          foo: tool.schema.string(),
        },
        async execute(args, context) {
          const { directory, worktree } = context
          return `Hello ${args.foo} from ${directory} (worktree: ${worktree})`
        },
      }),
    },
  }
}
```

If a plugin tool uses the same name as a built-in tool, the plugin tool takes precedence.

---

## Shipped Native Tool: `capture_request_context`

SkyScow ships one native request-context capture tool through `ToolsPlugin`:

```typescript
capture_request_context({ from: string })
```

`from` must identify exactly one visible user message in the current session. Anchor matching may normalize runs of whitespace for equality, but the captured transcript preserves the stored user and assistant text. The tool captures visible user/assistant conversation from that anchor through the last completed visible message strictly before the invocation; the invocation record is excluded from the transcript and provenance boundary. Tool results, reasoning, internal or synthetic content, and child-session content are not included.

On success, the tool creates a fresh write-once Markdown artifact under `artifacts/requests/` with a `CTX_<two-word-slug>.md` filename and returns the created artifact path. The artifact contains lightweight mechanical provenance and the exact transcript; it does not generate a summary or `handoff_goal`.

The operation fails closed and does not return a path when `from` is invalid, the anchor is absent or ambiguous, the current-session history is unavailable or cannot establish the required visibility or completion boundary, or exclusive artifact publication fails. Existing artifacts are not overwritten; only an observed destination collision is retried within the tool's bounded attempt limit.

---

## Tool Result Type

The `execute` function must return `ToolResult`, which is either a string or a structured object:

```typescript
type ToolResult =
  | string                    // Shorthand: string becomes the output
  | {
      output: string          // REQUIRED — the text shown to the model
      title?: string          // Optional — displayed in the tool UI
      metadata?: Record<string, any>  // Optional — arbitrary metadata
      attachments?: Array<{   // Optional — file attachments
        type: "file"
        mime: string
        url: string           // data: URL or absolute path
        filename?: string
      }>
    }
```

**Returning a string** is equivalent to `{ output: theString, title: "", metadata: {} }`.

---

## Common Mistakes

| Wrong | Right | Why |
|-------|-------|-----|
| `return { error: "not_found", message: "..." }` | `throw new Error("not found: ...")` | The registry checks for an `output` field. An object with `error` but no `output` produces empty/garbage output. Errors must be thrown. |
| `return { data: { ... } }` | `return { output: JSON.stringify(data, null, 2) }` | The `output` field must be a string. Arbitrary data objects are not auto-serialized. |
| `return { ok: true, result: "..." }` | `return { output: "...", title: "ok" }` | Only `output`, `title`, `metadata`, and `attachments` are read. Extra fields are ignored. |

---

## Full Example with Error Handling

```typescript
import { type Plugin, tool } from "@opencode-ai/plugin"

export const ToolsPlugin: Plugin = async () => {
  return {
    tool: {
      read_widget: tool({
        description: "Read a widget by ID.",
        args: {
          id: tool.schema.string().describe("Widget ID"),
        },
        async execute(args, context) {
          const { directory } = context

          // On error: throw, do NOT return an error object
          const widget = await loadWidget(args.id, directory)
          if (!widget) {
            throw new Error(`Widget not found: ${args.id}`)
          }

          // On success: return { output, title, metadata }
          return {
            output: JSON.stringify(widget, null, 2),
            title: `widget:${args.id}`,
            metadata: { id: widget.id, status: widget.status },
          }
        },
      }),
    },
  }
}
```

---

## Args Schema Helpers

Use `tool.schema` (re-exported Zod) to define arg types:

```typescript
args: {
  name:        tool.schema.string().describe("Description"),           // required string
  count:       tool.schema.number().describe("Description"),           // required number
  tag:         tool.schema.string().optional().describe("Description"), // optional string
  limit:       tool.schema.number().optional().describe("Description"), // optional number
  enabled:     tool.schema.boolean().optional().describe("Description"),// optional boolean
  tags:        tool.schema.array(tool.schema.string()).describe("..."), // required string[]
  filters:     tool.schema.array(tool.schema.string()).optional().describe("..."), // optional string[]
  nested:      tool.schema.object({                                     // nested object
    key: tool.schema.string(),
    value: tool.schema.string(),
  }).describe("Description"),
}
```
