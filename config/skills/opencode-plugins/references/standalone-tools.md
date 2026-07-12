# Standalone Custom Tools

Custom tools defined in `.opencode/tools/` — a separate mechanism from plugin-based tools. These are simpler, file-based tool definitions that the LLM can call alongside built-in tools.

---

## Table of Contents

- [Location](#location)
- [Structure](#structure)
- [Multiple Tools Per File](#multiple-tools-per-file)
- [Name Collisions](#name-collisions)
- [Arguments](#arguments)
- [Using Plain Zod](#using-plain-zod)
- [Context](#context)
- [Invoking Scripts in Other Languages](#invoking-scripts-in-other-languages)
- [Plugin Tools vs Standalone Tools](#plugin-tools-vs-standalone-tools)

---

## Location

| Location | Scope |
|----------|-------|
| `.opencode/tools/*.ts` or `*.js` | Project-level |
| `~/.config/opencode/tools/*.ts` or `*.js` | Global |

Options:
- **Local** — `.opencode/tools/` in your project
- **Global** — `~/.config/opencode/tools/` for all projects

---

## Structure

The **filename** becomes the **tool name**. A file named `database.ts` creates a tool called `database`.

```typescript
// .opencode/tools/database.ts
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Query the project database",
  args: {
    query: tool.schema.string().describe("SQL query to execute"),
  },
  async execute(args) {
    return `Executed query: ${args.query}`
  },
})
```

Use default export for a single tool; the filename is the tool name.

---

## Multiple Tools Per File

Named exports create tools with the name `filename_exportname`:

```typescript
// .opencode/tools/math.ts
import { tool } from "@opencode-ai/plugin"

export const add = tool({
  description: "Add two numbers",
  args: {
    a: tool.schema.number().describe("First number"),
    b: tool.schema.number().describe("Second number"),
  },
  async execute(args) {
    return (args.a + args.b).toString()
  },
})

export const multiply = tool({
  description: "Multiply two numbers",
  args: {
    a: tool.schema.number().describe("First number"),
    b: tool.schema.number().describe("Second number"),
  },
  async execute(args) {
    return (args.a * args.b).toString()
  },
})
```

This creates two tools: `math_add` and `math_multiply`.

---

## Name Collisions

If a custom tool uses the same name as a built-in tool, the **custom tool takes precedence**. For example, naming a file `bash.ts` replaces the built-in `bash` tool:

```typescript
// .opencode/tools/bash.ts
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Restricted bash wrapper",
  args: {
    command: tool.schema.string(),
  },
  async execute(args) {
    return `blocked: ${args.command}`
  },
})
```

**Prefer unique names** unless you intentionally want to replace a built-in tool. To disable a built-in tool without overriding it, use [permissions](https://opencode.ai/docs/permissions) instead.

---

## Arguments

Use `tool.schema` (re-exported Zod) to define argument types:

```typescript
args: {
  query: tool.schema.string().describe("SQL query to execute"),
  limit:  tool.schema.number().optional().describe("Max results"),
}
```

---

## Using Plain Zod

You can import Zod directly and return a plain object (no `tool()` helper):

```typescript
import { z } from "zod"

export default {
  description: "Tool description",
  args: {
    param: z.string().describe("Parameter description"),
  },
  async execute(args, context) {
    return "result"
  },
}
```

This is useful when you want full control over the tool definition shape without the `tool()` wrapper.

---

## Context

Tools receive session context in the `execute` function:

```typescript
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Get project information",
  args: {},
  async execute(args, context) {
    // Available context fields
    const { agent, sessionID, messageID, directory, worktree } = context

    return `Agent: ${agent}, Session: ${sessionID}, Message: ${messageID}, Dir: ${directory}`
  },
})
```

| Field | Description |
|-------|-------------|
| `agent` | Current agent name |
| `sessionID` | Current session identifier |
| `messageID` | Current message identifier |
| `directory` | Session working directory |
| `worktree` | Git worktree root |
| `abort` | AbortSignal for cancellation |

---

## Invoking Scripts in Other Languages

Tool definitions can invoke scripts written in any language using `Bun.$`:

```typescript
// .opencode/tools/python-add.ts
import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Add two numbers using Python",
  args: {
    a: tool.schema.number().describe("First number"),
    b: tool.schema.number().describe("Second number"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, ".opencode/tools/add.py")
    const result = await Bun.$`python3 ${script} ${args.a} ${args.b}`.text()
    return result.trim()
  },
})
```

---

## Plugin Tools vs Standalone Tools

| Aspect | Plugin-based tools | Standalone tools |
|--------|-------------------|-----------------|
| Location | Inside plugin files in `.opencode/plugins/` | `.opencode/tools/` or `~/.config/opencode/tools/` |
| Registration | Via `tool` key in Hooks object | Automatically by filename |
| Naming | Explicit name in the `tool` object | Filename (or `filename_exportname`) |
| Context access | `ToolContext` parameter | `context` parameter in `execute` |
| Best for | Tools bundled with other plugin logic | Simple, self-contained tool definitions |
