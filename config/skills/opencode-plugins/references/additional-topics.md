# Additional Topics

npm plugin loading, dependencies, load order, environment flags, and Copilot Hooks migration.

---

## Table of Contents

- [npm Plugin Loading](#npm-plugin-loading)
- [Local Plugin Dependencies](#local-plugin-dependencies)
- [Load Order](#load-order)
- [Deduplication](#deduplication)
- [Environment Flags](#environment-flags)
- [Key Differences from Copilot Hooks](#key-differences-from-copilot-hooks)

---

## npm Plugin Loading

Plugins can be installed from npm instead of local files. Specify them in your config:

```json
// opencode.json
{
  "plugin": ["opencode-helicone-session", "opencode-wakatime", "@my-org/custom-plugin"]
}
```

Both regular and scoped npm packages are supported.

### How npm plugins are installed

- Installed automatically via **Bun** at startup
- Packages and dependencies are cached in `~/.cache/opencode/node_modules/`
- No manual `bun install` required

### Passing options to npm plugins

Plugin options can be specified in config as a tuple:

```json
{
  "plugin": [
    "opencode-helicone-session",
    ["@my-org/custom-plugin", { "apiKey": "sk-xxx", "endpoint": "https://api.example.com" }]
  ]
}
```

The second element is passed as `options` to the plugin function:

```typescript
export const MyPlugin: Plugin = async (input, options) => {
  const apiKey = options?.apiKey
  // ...
}
```

### When to use local vs npm

| Local files | npm packages |
|-------------|-------------|
| Development and debugging | Distribution and sharing |
| Project-specific plugins | Reusable across projects |
| Quick prototypes | Versioned releases |
| File: `.opencode/plugins/*.ts` | Config: `"plugin": ["pkg-name"]` |

---

## Local Plugin Dependencies

Local plugins can use external npm packages. Add a `package.json` to your config directory:

```json
// .opencode/package.json
{
  "dependencies": {
    "shescape": "^2.1.0"
  }
}
```

OpenCode runs `bun install` at startup. Your plugins can then import them:

```javascript
import { escape } from "shescape"

export const MyPlugin = async (ctx) => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "bash") {
        output.args.command = escape(output.args.command)
      }
    },
  }
}
```

---

## Load Order

Plugins load from all sources and all hooks run in sequence. The load order is:

1. Global config (`~/.config/opencode/opencode.json`)
2. Project config (`opencode.json`)
3. Global plugin directory (`~/.config/opencode/plugins/`)
4. Project plugin directory (`.opencode/plugins/`)

### Three loading sources

| Source | Loading Method | Typical Use Case |
|--------|---------------|-----------------|
| Internal (built-in) | Direct `import` at startup | Built-in authentication (Codex, Copilot, GitLab) |
| npm package | `BunProc.install()` + dynamic `import()` | Community ecosystem, shared plugins |
| Local file | Direct `import("file://...")` | Development, debugging, project-specific logic |

---

## Deduplication

OpenCode prevents the same plugin from loading twice through reference comparison:

- **Duplicate npm packages** with the same name and version are loaded once
- **Same function exported** as both default and named export within a module is loaded once
- **Local plugin and npm plugin** with similar names are both loaded separately (different sources)

---

## Environment Flags

| Flag | Effect |
|------|--------|
| `OPENCODE_DISABLE_DEFAULT_PLUGINS` | Disables built-in authentication plugins (Codex, Copilot, GitLab) |

Set it to skip built-in plugins while keeping user-configured ones:

```bash
OPENCODE_DISABLE_DEFAULT_PLUGINS=1 opencode
```

---

## Key Differences from Copilot Hooks

| Copilot | OpenCode |
|---------|----------|
| JSON config + shell commands | JS/TS modules |
| `{legacy_hooks_path}/*.json` | `.opencode/plugins/*.js` |
| `permissionDecision: deny` | `throw new Error()` |
| `PreToolUse`, `PostToolUse` | `tool.execute.before`, `tool.execute.after` |
| JSON via stdin | Context object parameter |
| Exit code semantics | Error throwing |
| `additionalContext` in stdout | Modify `output` object |
