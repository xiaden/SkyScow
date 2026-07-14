---
name: opencode-plugins
description: Use when creating or updating OpenCode plugin files in .opencode/plugins/. Covers plugin structure, hook events (tool.execute.before/after, session.*, file.*, etc.), blocking operations via throw, custom tools, environment injection, and TypeScript types.
---

# OpenCode Plugins

Plugins extend OpenCode by hooking into events and customizing behavior. They provide deterministic automation: blocking dangerous operations, injecting context, adding custom tools, modifying LLM parameters, and logging.

**Do NOT use this skill for:** configuring `opencode.json` or `opencode.jsonc` (use `customize-opencode`), writing commands (use `command-creation-guide`), or creating standalone custom tools in `.opencode/tools/` (see [`references/standalone-tools.md`](file:///home/opencode/.config/opencode/skills/opencode-plugins/references/standalone-tools.md)).

---

## Plugin Installation

### Local Files

Place JavaScript or TypeScript files in the plugin directory:

| Location | Scope |
|----------|-------|
| `.opencode/plugins/*.js` or `*.ts` | Project-level |
| `~/.config/opencode/plugins/*.js` or `*.ts` | Global |

Files in these directories are automatically loaded at startup.

### npm Packages

Specify npm packages in your config file (`opencode.json`):

```json
{
  "plugin": ["opencode-helicone-session", "opencode-wakatime", "@my-org/custom-plugin"]
}
```

Both regular and scoped npm packages are supported. Plugins are installed automatically via Bun at startup and cached in `~/.cache/opencode/node_modules/`. Duplicate packages with the same name and version are loaded once.

---

## Basic Structure

```javascript
// .opencode/plugins/example.js
export const MyPlugin = async ({ project, client, $, directory, worktree, serverUrl }) => {
  console.log("Plugin initialized!")

  return {
    // Hook implementations go here
  }
}
```

The plugin function receives:
- `project`: Current project information
- `directory`: Current working directory
- `worktree`: Git worktree path
- `client`: OpenCode SDK client for AI interactions
- `$`: Bun's shell API for executing commands
- `serverUrl`: OpenCode server URL

### TypeScript Support

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ project, client, $, directory, worktree, serverUrl }) => {
  return {
    // Type-safe hook implementations
  }
}
```

---

## Hook Events

### Tool Events (Primary Hook Targets)

| Event | Fires when | Common uses |
|-------|------------|-------------|
| `tool.execute.before` | Before tool runs | Block dangerous ops, validate args, inject context |
| `tool.execute.after` | After tool completes | Run formatters, log results, trigger follow-up |

### Chat / LLM Hooks

| Event | Fires when | Common uses |
|-------|------------|-------------|
| `chat.message` | New message is received | Augment messages, inject context |
| `chat.params` | Before LLM call | Override temperature, topP, topK, maxOutputTokens |
| `chat.headers` | Before LLM call | Inject custom HTTP headers for providers |
| `experimental.chat.messages.transform` | Before messages sent to LLM | Transform message list |
| `experimental.chat.system.transform` | Before system prompt assembled | Inject or modify system prompt lines |
| `experimental.text.complete` | During text completion | Intercept completion results |

### Permission & Command Hooks

| Event | Fires when | Common uses |
|-------|------------|-------------|
| `permission.ask` | Permission dialog shown | Auto-allow or auto-deny operations |
| `command.execute.before` | Before command runs | Validate or augment command context |

### Session Events

| Event | Fires when |
|-------|------------|
| `session.created` | New session starts |
| `session.compacted` | Context compaction completes |
| `session.deleted` | Session is deleted |
| `session.diff` | Diff is generated |
| `session.error` | Session encounters error |
| `session.idle` | Session becomes idle |
| `session.status` | Status changes |
| `session.updated` | Session data changes |
| `experimental.session.compacting` | Before compaction prompt generation |
| `experimental.compaction.autocontinue` | After compaction, before auto-continue message |

### File Events

| Event | Fires when |
|-------|------------|
| `file.edited` | File is modified |
| `file.watcher.updated` | File watcher state changes |

### Lifecycle & Config Hooks

| Event | Fires when | Common uses |
|-------|------------|-------------|
| `config` | During startup | Modify configuration at runtime |
| `dispose` | Plugin shutdown / reload | Clean up resources |
| `event` | Any event fires | Listen to all session events |
| `tool.definition` | Tool definition sent to LLM | Modify tool descriptions/parameters |
| `shell.env` | Before shell execution | Inject environment variables |
| `experimental.provider.small_model` | Small model selection | Select alternative model for lightweight tasks |

### Auth Hooks

| Event | Fires when | Common uses |
|-------|------------|-------------|
| `auth` | Provider authentication | Add OAuth or API-key auth for LLM providers |
| `provider` | Provider initialization | Register custom model providers |

---

## Blocking Operations

To block a tool execution, **throw an error** in `tool.execute.before`:

```javascript
export const EnvProtection = async ({ project, client, $, directory, worktree, serverUrl }) => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read" && output.args.filePath.includes(".env")) {
        throw new Error("Do not read .env files")
      }
    },
  }
}
```

The error message is shown to the model as feedback.

---

## Environment Injection

Inject environment variables into all shell execution:

```javascript
export const InjectEnvPlugin = async () => {
  return {
    "shell.env": async (input, output) => {
      output.env.MY_API_KEY = "secret"
      output.env.PROJECT_ROOT = input.cwd
    },
  }
}
```

---

## Reference Files

This skill covers core concepts. For detailed implementation patterns, load these reference files on demand:

- **[`references/hooks.md`](file:///home/opencode/.config/opencode/skills/opencode-plugins/references/hooks.md)** — Detailed hook implementations: `tool.execute.before`, `tool.execute.after`, `permission.ask`, `command.execute.before`, `tool.definition`, compaction hooks, notifications, logging, config hook, dispose hook, and event listener
- **[`references/chat-hooks.md`](file:///home/opencode/.config/opencode/skills/opencode-plugins/references/chat-hooks.md)** — Chat lifecycle hooks: `chat.message`, `chat.params`, `chat.headers`, `experimental.chat.messages.transform`, `experimental.chat.system.transform`, `experimental.text.complete`
- **[`references/custom-tools.md`](file:///home/opencode/.config/opencode/skills/opencode-plugins/references/custom-tools.md)** — Plugin-based custom tools API: `ToolResult` type, common mistakes, args schema helpers, and complete examples with error handling
- **[`references/standalone-tools.md`](file:///home/opencode/.config/opencode/skills/opencode-plugins/references/standalone-tools.md)** — Standalone custom tools in `.opencode/tools/`: file naming, multiple exports, plain Zod approach, context access, invoking scripts in other languages
- **[`references/additional-topics.md`](file:///home/opencode/.config/opencode/skills/opencode-plugins/references/additional-topics.md)** — npm plugin loading, dependencies, load order with deduplication, `OPENCODE_DISABLE_DEFAULT_PLUGINS`, and Copilot Hooks migration guide

---

## Authoring Checklist

- [ ] Plugin exports a named function
- [ ] Returns object with hook implementations
- [ ] Uses `throw new Error()` to block (not return values)
- [ ] Handles errors gracefully (don't crash on unexpected input)
- [ ] Uses `client.app.log()` for debugging
- [ ] TypeScript types imported from `@opencode-ai/plugin`
- [ ] Dependencies declared in `.opencode/package.json` if needed
- [ ] Custom tools return `{ output: string, title?, metadata? }` — never `{ error, data, ok, result }` or other shapes
- [ ] Custom tools `throw new Error(...)` on failure — never return error objects
- [ ] Every arg in `args` uses `tool.schema` and has `.describe()`
