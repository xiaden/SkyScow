# Body Structure Patterns

## Contents
- [Structural Patterns](#structural-patterns)
- [Formatting Rules](#formatting-rules)
- [Full Directory Structure Example](#full-directory-structure-example)

---

## Structural Patterns

Patterns observed across the existing skill corpus. Choose based on what the skill needs to communicate.

| Pattern | When to use | Example skill |
|---------|-------------|---------------|
| **Procedural workflow** | Multi-step processes with phase gates and entry/exit criteria | `feature-planning`, `doc-coauthoring` |
| **Template + dispatch** | The skill is a fill-in-the-blank prompt for dispatching another agent | `dispatching-support-researcher` |
| **Convention reference** | Encoding rules for a specific code area — what to do, what NOT to do | `code-migration`, `cliche-data-in-docs` |
| **Meta-guide** | Teaching how to do something (the skill IS the exemplar) | `task-plans-guide`, `customize-opencode` |
| **Decision tree** | Multiple products/tools/approaches for similar problems — branch on requirements, terminate at specific references | `cloudflare-skill` (60+ products, decision trees in SKILL.md → per-product references) |

### Decision Tree Pattern (Advanced)

When a skill covers multiple tools/products that solve similar problems, use decision trees in SKILL.md to route to the right reference:

```
Need to run code?
├─ Serverless functions at the edge → references/workers/
├─ Full-stack web app with Git deploys → references/pages/
├─ Stateful coordination/real-time → references/durable-objects/
├─ Long-running multi-step jobs → references/workflows/
├─ Run containers → references/containers/
└─ Scheduled tasks (cron) → references/cron-triggers/
```

This forces disambiguation — the agent can't default to the most common option. It must understand the use case first. Each branch terminates at a specific reference directory.

---

## Formatting Rules

- **Use tables** for reference data (fields, validation rules, comparisons). Tables are more scannable than prose lists. For research-backed guidance on when to use tables vs. lists vs. prose, see [`references/format-choice.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/format-choice.md).
- **Use code blocks with language tags** for examples. ` ```yaml ` not ` ``` `.
- **Use `**bold**` for emphasis**, not ALL CAPS. Bold draws the eye without shouting.
- **Keep headings descriptive** — "When to Use" not "Usage", "Frontmatter Rules" not "Config".
- **Reference other skills by exact `name`**: `Use \`capture-subsystem\` for...`
- **Link to reference files with absolute `file://` URIs for global skills.** Skills in `~/.config/opencode/skills/` sit outside any workspace — relative paths like `references/advanced.md` resolve from the workspace root, not the skill's directory, so they break across workspaces. Use `file:///home/<user>/.config/opencode/skills/<skill>/references/advanced.md` instead. Workspace-local skills (`.opencode/skills/`) can use relative paths since they share the workspace root.
- **Use forward slashes** in all paths, never backslashes (`\`).
- **For reference files >100 lines**, include a table of contents at the top so the agent can see scope when previewing.

---

## Full Directory Structure Example

A skill with full progressive disclosure — index in SKILL.md, details in references, reusable code in scripts, templates in assets:

```
my-skill/
├── SKILL.md                    ← Core workflow, decisions, pointers (<500 lines)
├── references/                 ← Loaded on demand
│   ├── patterns.md             ← Detailed implementation patterns
│   ├── advanced.md             ← Advanced techniques, edge cases
│   └── api-reference.md        ← Comprehensive API documentation
├── scripts/                    ← Executed, not loaded into context
│   ├── validate.py             ← Validation script
│   └── setup.sh                ← Setup automation
└── assets/                     ← Used in output, not loaded as instructions
    ├── template.md             ← Reusable template
    └── example-output.json     ← Expected output format
```

**Key principle:** Only SKILL.md and references/ files enter the context window. Scripts in `scripts/` are executed (only their output consumes tokens). Assets in `assets/` are templates the agent reads and fills in — their content is output, not instruction.
