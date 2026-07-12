# Hook Implementations

Detailed implementation patterns for tool, permission, command, lifecycle, and compaction hooks.

---

## Table of Contents

- [tool.execute.before](#toolexecutebefore)
- [tool.execute.after](#toolexecuteafter)
- [permission.ask](#permissionask)
- [command.execute.before](#commandexecutebefore)
- [tool.definition](#tooldefinition)
- [Compaction Hooks](#compaction-hooks)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Notifications](#notifications)
- [Logging](#logging)

---

## tool.execute.before

Access tool name and arguments. Validate, block, or modify execution:

```javascript
"tool.execute.before": async (input, output) => {
  // input.tool       — tool name (e.g., "bash", "edit", "read")
  // input.sessionID  — current session ID
  // input.callID     — unique call identifier
  // output.args      — tool arguments (mutable)

  if (input.tool === "bash") {
    if (output.args.command.includes("rm -rf /")) {
      throw new Error("Destructive command blocked")
    }
    output.args.command = output.args.command.replace("dangerous", "safe")
  }
}
```

---

## tool.execute.after

Access tool results after execution:

```javascript
"tool.execute.after": async (input, output) => {
  // input.tool       — tool name
  // input.sessionID  — current session ID
  // input.callID     — unique call identifier
  // input.args       — the arguments the tool was called with
  // output.title     — tool result title
  // output.output    — tool result output text
  // output.metadata  — tool result metadata

  if (input.tool === "edit") {
    console.log(`File edited: ${input.args.filePath}`)
  }
}
```

---

## permission.ask

Intercept and override permission prompts. Set status to `"allow"` or `"deny"` to skip the prompt.

```typescript
"permission.ask": async (input, output) => {
  // input — Permission object (contains tool, args, session info)
  // output.status — "ask" | "deny" | "allow"

  // Auto-allow read operations, ask for everything else
  if (input.tool === "read" || input.tool === "grep") {
    output.status = "allow"
  }

  // Block destructive operations even before tool.execute.before fires
  if (input.tool === "bash" && input.args.command?.includes("rm -rf")) {
    output.status = "deny"
  }
}
```

---

## command.execute.before

Intercept command execution (user-defined commands, not bash tool calls):

```typescript
"command.execute.before": async (input, output) => {
  // input.command    — command name
  // input.sessionID  — current session ID
  // input.arguments  — command arguments string
  // output.parts     — Part[] array for response

  // Append a confirmation before running a dangerous command
  if (input.command === "deploy") {
    output.parts.push({ type: "text", text: "⚠️ Deploying to production..." })
  }
}
```

---

## tool.definition

Modify tool descriptions and parameters before they're sent to the LLM:

```typescript
"tool.definition": async (input, output) => {
  // input.toolID        — tool identifier
  // output.description  — tool description (mutable)
  // output.parameters   — tool parameters object (mutable)

  if (input.toolID === "bash") {
    output.description = "Restricted bash: only safe commands allowed"
  }
}
```

---

## Compaction Hooks

### experimental.session.compacting

Customize context included when a session is compacted:

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const CompactionPlugin: Plugin = async (ctx) => {
  return {
    "experimental.session.compacting": async (input, output) => {
      // input.sessionID — current session ID
      // output.context  — string[] (additional context lines appended to prompt)
      // output.prompt   — string? (if set, replaces the entire compaction prompt)

      // Inject additional context
      output.context.push(`## Custom Context
- Current task status: implementing auth module
- Important decisions: using JWT over sessions
- Files being actively worked on: src/auth/login.ts`)
    },
  }
}
```

Or replace the compaction prompt entirely:

```typescript
"experimental.session.compacting": async (input, output) => {
  output.prompt = `You are generating a continuation prompt...`
}
```

**When `output.prompt` is set, `output.context` is ignored.**

### experimental.compaction.autocontinue

Control whether a synthetic "continue" user message is added after compaction:

```typescript
"experimental.compaction.autocontinue": async (input, output) => {
  // input.sessionID, input.agent, input.model, input.provider, input.message
  // input.overflow — true if compaction was triggered by context overflow
  // output.enabled — defaults to true; set to false to skip auto-continue

  // Don't auto-continue when compaction was due to overflow
  if (input.overflow) {
    output.enabled = false
  }
}
```

---

## Lifecycle Hooks

### config

Modify configuration during plugin initialization:

```typescript
"config": async (input) => {
  // input is the full Config object (mutable)
  // Modify theme, permissions, providers, etc. at runtime
}
```

### dispose

Clean up resources when the plugin is shut down or reloaded:

```typescript
export const MyPlugin: Plugin = async (ctx) => {
  // Setup resources
  const watcher = startFileWatcher()

  return {
    dispose: async () => {
      // Clean up
      await watcher.close()
      console.log("Plugin disposed")
    },

    // ... other hooks
  }
}
```

### event

Listen to all session events (a catch-all hook):

```typescript
export const MyPlugin = async () => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.created") {
        console.log("New session:", event.properties.info.id)
      }
      if (event.type === "session.idle") {
        console.log("Session became idle")
      }
    },
  }
}
```

---

## Notifications

Send system notifications on events:

```javascript
export const NotificationPlugin = async ({ $ }) => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        await $`osascript -e 'display notification "Session completed!" with title "opencode"'`
      }
    },
  }
}
```

---

## Logging

Use `client.app.log()` for structured logging:

```typescript
export const MyPlugin = async ({ client }) => {
  await client.app.log({
    body: {
      service: "my-plugin",
      level: "info",
      message: "Plugin initialized",
      extra: { foo: "bar" },
    },
  })
}
```

Levels: `debug`, `info`, `warn`, `error`.
