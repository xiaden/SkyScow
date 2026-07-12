---
name: creating-auto-injected-instructions
description: Create instruction files that are automatically injected into agent context when working with files matching specific path patterns. Use when you need to enforce conventions, patterns, or constraints for a specific area of the codebase — such as a layer, module type, or directory structure — without cluttering always-on context. Triggers include needing to document layer-specific rules, establishing conventions for a subsystem, or preventing recurring mistakes in a code area.
---

# Creating Auto-Injected Instructions

**Purpose:** Produce instruction files with `applyTo` frontmatter that are automatically injected into agent context when the agent touches files matching the specified glob patterns. This lets you enforce conventions for specific code areas without adding them to always-on context.

## When to Use

Use auto-injected instructions when:

- A code area has conventions that differ from the rest of the codebase
- Agents repeatedly make the same mistakes in a specific directory
- Layer boundaries or architectural constraints need enforcement
- Naming patterns, import rules, or structural requirements are area-specific

Do **not** use when:

- The rule applies everywhere → use `AGENTS.md` instead
- The rule is about a workflow or process → use a skill instead
- The rule is already enforced by linting or type-checking → let the tools handle it

## File Location and Naming

Place instruction files in `.opencode/instructions/` (project-level) or `~/.config/opencode/instructions/` (global).

Use descriptive names that identify the area:

```
.opencode/instructions/
├── services-layer.instructions.md
├── api-routes.instructions.md
├── database-migrations.instructions.md
└── ui-components.instructions.md
```

The filename is for human navigation only — the plugin matches files by the `applyTo` pattern, not the filename.

## Frontmatter Format

Every instruction file requires YAML frontmatter with three fields:

```markdown
---
name: Display Name
description: Brief description of what this covers and when it applies
applyTo: glob/pattern/**, another/pattern/**
---
```

**`name`**: Human-readable identifier. Shown in logs and debugging.

**`description`**: Explains what the instruction covers. This is for human readers — the plugin injects based on `applyTo`, not description matching.

**`applyTo`**: Comma-separated glob patterns. Injection triggers when the agent touches any file matching these patterns. Standard glob syntax applies:
- `**` matches any number of directories
- `*` matches within a single directory level
- `**/*.ts` matches all TypeScript files recursively
- `src/services/**` matches everything under `src/services/`

Multiple patterns are separated by commas with optional spaces:

```yaml
applyTo: src/api/**, src/routes/**, src/handlers/**
```

## Content Structure

After the frontmatter, write the instruction body in markdown. The content is injected verbatim into agent context — treat it as direct instructions to the agent.

### What to Include

- **Purpose**: One sentence explaining what this area does and why it exists
- **Naming conventions**: File, class, function, or variable patterns specific to this area
- **Allowed and forbidden imports**: What this area can depend on and what it cannot
- **Structural rules**: Required patterns, layer boundaries, size limits
- **Validation steps**: What to run after editing files in this area

### What to Exclude

- Information that applies globally (put that in `AGENTS.md`)
- Implementation details that change with normal refactors
- Content already enforced by tooling (linters, type-checkers, formatters)
- Workflow instructions (those belong in skills)

For annotated examples of complete instruction files, see [`references/example-structure.md`](file:///home/opencode/.config/opencode/skills/creating-auto-injected-instructions/references/example-structure.md).

## Scope Decisions

Each instruction file should cover **one coherent area**. Split when conventions conflict, patterns don't overlap naturally, or the file exceeds ~300 lines. Combine when two areas share identical conventions and the combined content stays under ~100 lines.

**Overlap rule:** Instruction files must not have overlapping `applyTo` patterns. When two files would match the same path, merge them or narrow the patterns:

```yaml
# Bad — overlapping
# File 1: applyTo: src/api/**
# File 2: applyTo: src/api/v2/**

# Good — non-overlapping
# File 1: applyTo: src/api/v1/**
# File 2: applyTo: src/api/v2/**
```

For detailed rules on when to split, combine, or resolve nested-convention overlaps, see [`references/scope-decisions.md`](file:///home/opencode/.config/opencode/skills/creating-auto-injected-instructions/references/scope-decisions.md).

## Relationship to Other Mechanisms

| Mechanism | When to use | Scope |
|-----------|-------------|-------|
| **Auto-injected instructions** | File-area-specific conventions | Injected when matching files are touched |
| **`AGENTS.md`** | Rules that apply to all files | Always in context |
| **Skills** | Workflow guidance, process instructions | Loaded when task matches description |
| **`opencode.json` instructions** | External file references | Always in context |

If a rule applies to all files, put it in `AGENTS.md`. If it applies only when editing specific paths, use auto-injected instructions. If it's about how to do something rather than what files should look like, use a skill.

## Validation Checklist

Before declaring an instruction file complete, verify:

- [ ] `applyTo` patterns are correct glob syntax and cover the intended directories
- [ ] No other instruction file has an overlapping `applyTo` pattern
- [ ] Content is area-specific — nothing that belongs in `AGENTS.md` or a skill
- [ ] No rules already enforced by tooling (linters, type-checkers, formatters)
- [ ] Includes a concrete validation step the agent can run after editing
- [ ] File is placed in `.opencode/instructions/` (project) or `~/.config/opencode/instructions/` (global)

## Maintenance

When conventions change:

1. Update the instruction file directly
2. Commit the change alongside the code that reflects the new convention

Instruction files are version-controlled with the project. Treat them as living documentation — stale instructions cause agents to produce incorrect output.

## References

- **This skill's references:**
  - [`references/example-structure.md`](file:///home/opencode/.config/opencode/skills/creating-auto-injected-instructions/references/example-structure.md) — Annotated examples of complete instruction files
  - [`references/scope-decisions.md`](file:///home/opencode/.config/opencode/skills/creating-auto-injected-instructions/references/scope-decisions.md) — Detailed rules for granularity, splitting, combining, and overlap resolution
- **Related skills:** `making-editing-skills` (skill conventions), `customize-opencode` (config), `command-creation-guide` (commands), `capture-subsystem` (codebase research skills)
