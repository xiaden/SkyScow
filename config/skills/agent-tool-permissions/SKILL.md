---
name: agent-tool-permissions
description: Use when editing OpenCode agent permission frontmatter, configuring tool access, or debugging missing-tool errors.
---

# Agent Tool Permissions

## Mental Model

Every OpenCode agent (`~/.config/opencode/agents/*.md`) has a YAML frontmatter block with a `permission:` section. This section enumerates the tools the agent may call. Tools not listed are denied. The system supports exact tool names and glob patterns. Plugin-provided tools (like `research_papers` from `opencode-research-papers`) require both: (1) the plugin registered in `opencode.json`'s `"plugin"` array, and (2) the tool name listed in the agent's `permission:` block.

## Coverage

**Documented:** How agent permissions work, the YAML frontmatter pattern, glob patterns for tool groups, how to grant plugin tools, which agents have which tools.

**Not yet documented:** The permission validation pipeline (how/when OpenCode checks the frontmatter against tool calls), the plugin tool registration lifecycle.

**Last extended:** 2026-07-10

## Key Findings

### Permission Block in Agent Frontmatter
- **Location:** `~/.config/opencode/agents/*.md` (frontmatter `permission:` key)
- **What:** Each agent has a `permission:` block listing tools with `allow` or `deny`. Tools not listed are implicitly denied.
- **Why it matters:** Adding a new tool to an agent requires editing the agent's `.md` file. This is the sole mechanism for granting tool access.

### Glob Patterns Are Supported
- **Location:** Various agent files
- **What:** Tools can be specified with glob-style wildcards: `aft_*`, `adr_*`, `dd_*`, `asr_*`, `ast_grep_*`.
- **Why it matters:** Plugin-provided tools with consistent prefixes could use glob patterns, but `research_papers` has no prefix consistent with any existing agent permission block.

### Plugin Tools Require Two Steps
- **Location:** `~/.config/opencode/opencode.json` (plugin registration) + agent frontmatter (permission grant)
- **What:** A plugin-provided tool becomes available at runtime only after (1) the plugin is registered in `opencode.json`'s `"plugin"` array, and (2) at least one agent has it in their `permission:` block.
- **Why it matters:** The `opencode-research-papers` plugin (v1.4.5) IS registered in `opencode.json` (line 7: `"opencode-research-papers"`) but NO agent has `research_papers` in their permission block. The tool exists at runtime but no agent can call it.

### No Config-Level Tool Assignment
- **Location:** `~/.config/opencode/opencode.json`
- **What:** The opencode.json file does NOT have a `"tools"` or `"permissions"` section for assigning tools to agents. All tool assignment happens in agent frontmatter.
- **Why it matters:** There is no central configuration registry — you must edit each agent file individually.

### research_papers Tool Parameters
- **Source:** `opencode-research-papers` plugin v1.4.5 (`dist/tools/research_papers.js`)
- **Parameters:**
  - `query` (string, required) — research field/topic
  - `source` (enum: "arxiv" | "openalex" | "semantic_scholar" | "auto", default: "auto")
  - `filter` (enum: "latest" | "trending" | "top_cited", default: "latest")
  - `max_results` (number, 1-50, default: 10)
  - `date_range` (enum: "week" | "month" | "year" | "all", optional)
  - `strict` (boolean, default: false) — anchor + concept-group filtering

## Critical Invariants
- Tool NOT listed in an agent's `permission:` block = agent cannot call it (implicit deny)
- Glob patterns work for tool families (`aft_*`, `adr_*`), but individual tool names must be explicitly listed if not covered by a glob
- Adding a plugin to `opencode.json` does NOT automatically grant tool access to any agent — the permission block must be updated separately
- The permission block is the ONLY mechanism for granting/denying tools; there is no config-level tool routing

## Granting Pattern
To grant a tool to an agent, add it to the `permission:` block in the agent's `.md` frontmatter:

```yaml
permission:
  # ... existing tools ...
  research_papers: allow
```

This applies to any tool — built-in or plugin-provided. No other configuration is needed (the plugin must already be registered in `opencode.json`).

## Sources
- `~/.config/opencode/agents/agent.md` — primary agent, full permission block (lines 5-32)
- `~/.config/opencode/agents/support-researcher.md` — researcher agent permission block
- `~/.config/opencode/agents/rnd-ideator.md` — ideator agent permission block
- `~/.config/opencode/agents/rnd-dd-author.md` — DD author agent permission block
- `~/.config/opencode/agents/rnd-manager.md` — R&D manager permission block
- `~/.config/opencode/opencode.json` — global config, plugin registration
- `~/.cache/opencode/packages/opencode-research-papers/node_modules/opencode-research-papers/dist/tools/research_papers.js` — tool implementation
- `~/.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts` — Plugin SDK types
