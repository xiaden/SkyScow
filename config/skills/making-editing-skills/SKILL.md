---
name: making-editing-skills
description: Create, edit, and maintain OpenCode agent skills (SKILL.md files) that agents actually discover and use. Covers progressive disclosure (the three-level loading system: metadata → body → references), frontmatter rules, description writing (the discovery trigger), skill-vs-command decisions, and validation. Use when creating a new skill, editing an existing SKILL.md, restructuring a monolithic skill with references/, or asked about skill conventions. Also use when working in `.opencode/skills/` or `~/.config/opencode/skills/`.
---

# Making & Editing Skills

**Purpose:** Produce `SKILL.md` files that agents discover and load reliably. This skill is both a guide AND an exemplar — its own structure demonstrates the conventions it teaches.

Skills are loaded on-demand via the native `skill` tool. The agent sees the skill's `name` and `description` and decides whether to load it. You don't invoke it — the model does.

---

## When to Use This Skill

**Trigger conditions:**

- Creating a new skill from scratch
- Editing or extending an existing `SKILL.md`
- Asked about skill conventions, format, or best practices
- Working inside `.opencode/skills/` or `~/.config/opencode/skills/`
- Converting a Claude Code skill to OpenCode format

**Do NOT use this skill when:**

- Writing agent definitions (see `customize-opencode`)
- Writing commands (see `command-creation-guide`)
- Capturing codebase research (use `capture-subsystem` instead)

---

## Progressive Disclosure Design

Skills use a **three-level loading system** to manage context efficiently. This is the defining architectural pattern — every skill design decision flows from it.

| Level | What loads | When | Token cost |
|-------|-----------|------|------------|
| **1. Metadata** | `name` + `description` from frontmatter | Always — listed in the `<available_skills>` block | ~100 tokens per skill |
| **2. Body** | Full `SKILL.md` content | When the agent decides the skill matches the task | <5,000 words (target) |
| **3. Bundled resources** | Files in `references/`, `scripts/`, `assets/` | Only when the agent explicitly reads or executes them | Zero until accessed |

**The implication:** You can install 50 skills without context penalty — only metadata loads at startup. The body loads on trigger. References load on demand. This is why progressive disclosure matters: it lets you ship comprehensive skills without bloating every conversation.

### What Goes Where

Treat `SKILL.md` as an **index**, not a dump. The body should contain what every invocation needs; move the rest into reference files.

| Keep in SKILL.md (always loaded) | Move to references/ (loaded on demand) |
|----------------------------------|----------------------------------------|
| Core concepts and mental model | Detailed implementation patterns |
| Essential procedures and workflows | Comprehensive API documentation |
| Decision trees and selection guidance | Edge cases and troubleshooting guides |
| Quick-reference tables | Extensive examples and walkthroughs |
| Pointers to references/ files | Migration guides and version history |
| Validation checklists | Domain-specific schemas and data |

### Directory Structure (Full Progressive Disclosure)

```
my-skill/
├── SKILL.md                    ← Core workflow, decisions, pointers (<500 lines)
├── references/                 ← Loaded on demand by the agent
│   ├── patterns.md             ← Detailed implementation patterns
│   ├── advanced.md             ← Advanced techniques, edge cases
│   └── api-reference.md        ← Comprehensive API documentation
├── scripts/                    ← Executed — only output consumes tokens
│   └── validate.py
└── assets/                     ← Templates used in output
    └── template.md
```

**Key rules for references:**

- **One level deep.** All reference files link directly from `SKILL.md`. Never chain: `a.md → b.md → c.md`.
- **Descriptive filenames.** `form-validation-rules.md`, not `doc2.md`.
- **Table of contents** for files >100 lines so the agent can preview scope.
- **No duplication.** Information lives in SKILL.md OR a reference file, never both.

For detailed structural patterns (Guide with references, Domain-specific organization, Decision tree) with examples, formatting rules, and directory templates, see [`references/body-patterns.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/body-patterns.md).

---

## Skill File Anatomy

A skill is a **folder** named after the skill, containing a `SKILL.md` (exact capitalization). The full directory structure is shown in [Progressive Disclosure Design](#directory-structure-full-progressive-disclosure) above. Most skills only need `SKILL.md` + `references/`. Add `scripts/` for deterministic automation; add `assets/` for reusable templates.

### Frontmatter (Required)

Every `SKILL.md` starts with YAML frontmatter between `---` fences. See [Frontmatter Rules](#frontmatter-rules) for complete field documentation.

### Body

Plain markdown. This is the loaded instructions — what the agent acts on. Structure it for scannability: clear headings, concrete examples, procedural steps. See [Body Structure Conventions](#body-structure-conventions) for structural patterns.

---

## Frontmatter Rules

Two required fields (`name`, `description`) and three optional (`license`, `compatibility`, `metadata`). Both required fields determine whether the skill loads at all — `name` must match the directory, `description` is the discovery signal the agent uses to decide when to load.

| Field | Constraint | Role |
|-------|-----------|------|
| **`name`** | lowercase, hyphen-separated, 1–64 chars, must match directory | Identity — mismatched = won't load |
| **`description`** | 1–1024 chars | Discovery — the only field the agent sees before loading |

For complete validation rules (naming constraints with examples, description writing anatomy with good/bad comparisons, optional field documentation), see [`references/frontmatter-rules.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/frontmatter-rules.md).

---

## Body Structure Conventions

After the frontmatter, write the body in markdown. The body is loaded only when the skill triggers — keep it lean.

### Recommended Sections

1. **Purpose statement** — one sentence. "Produce X."
2. **When to Use** — concrete trigger conditions, with explicit "do NOT use" boundaries to prevent false loads
3. **Core content** — the actual instructions. For skills with multiple variants/domains, use decision trees that route to reference files rather than inlining everything.
4. **Checklist / Validation** — what to verify before considering the work done
5. **References** — links to canonical sources, related skills, `references/` files

### Structural Patterns

Skills fall into a few recurring patterns. Choose based on what the skill needs to communicate, and structure `references/` accordingly. See [`references/body-patterns.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/body-patterns.md) for the full pattern catalog with examples, formatting rules, and directory structure templates.

| Pattern | SKILL.md contains | references/ contains |
|---------|-------------------|---------------------|
| **Procedural workflow** | Phase gates, entry/exit criteria | Detailed step instructions |
| **Template + dispatch** | Fill-in-the-blank dispatch prompt | Agent-specific parameter docs |
| **Convention reference** | Rules, "do this / don't do that" | Code examples, migration guides |
| **Decision tree** | Branching logic routing to references | Per-variant detailed docs |

---

## Validation Checklist

Before declaring a skill complete, verify every item:

### Structural
- [ ] `SKILL.md` is named in ALL CAPS (not `skill.md` or `Skill.md`)
- [ ] Folder name matches `name` in frontmatter exactly
- [ ] `name` is lowercase, hyphen-separated, 1–64 chars, no consecutive hyphens
- [ ] `description` is 1–1024 chars, includes both WHAT and WHEN

### Discovery Quality
- [ ] `description` includes a trigger phrase ("Use when...", "Trigger when...")
- [ ] `description` mentions concrete nouns the agent will see (filenames, directories, actions)
- [ ] The skill would load for a task that matches its purpose (test this mentally: "if the user says X, would the agent think to load this?")

### Body Quality
- [ ] Starts with a clear purpose statement
- [ ] Includes explicit "do NOT use" boundaries (prevents false loads)
- [ ] Content is scannable — headings, tables, examples, not walls of prose
- [ ] Under 500 lines (split into `references/` if larger)
- [ ] No time-sensitive information (dates, version numbers that will rot)
- [ ] Concrete examples, not abstract descriptions
- [ ] Consistent terminology throughout

### Integration
- [ ] References to other skills use their exact `name` value
- [ ] File paths use forward slashes (not Windows-style backslashes). For global skills in `~/.config/opencode/skills/`, reference-file links use absolute `file://` URIs — relative paths resolve from the workspace root, not the skill directory
- [ ] If the skill references scripts or external files, those files exist

---

## Common Mistakes

The nine most frequent skill-authoring errors, in order of impact:

1. **Vague descriptions** — the skill never triggers because the agent can't match it
2. **Name/folder mismatch** — the skill won't load at all
3. **Wrong `SKILL.md` capitalization** — `skill.md` or `Skill.md` won't be discovered
4. **Nested reference chains** — `a.md → b.md → c.md` causes partial reads
5. **Monolithic SKILL.md** — no progressive disclosure, everything loaded every time
6. **Over-explaining** — padding that wastes context budget
7. **Skill vs. command confusion** — using the wrong mechanism for the trigger pattern
8. **Bundling unrelated jobs** — description gets vague, load decisions get muddled
9. **Relative links in global skills** — `references/foo.md` resolves from the workspace root, not the skill directory; use `file://` URIs instead

For detailed examples of each mistake with before/after fixes, see [`references/common-mistakes.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/common-mistakes.md).

---

## Editing Existing Skills

When modifying a skill that already exists:

### Before Editing
1. **Read the whole skill.** Understand the current structure and intent.
2. **Check for related skills.** Is there overlap? Should they be merged?
3. **Check the `## Coverage` section** (subsystem skills). Move items from "Not yet documented" to "Documented" as you fill gaps.
4. **Check references to this skill.** Do other skills or agents reference it? Will your changes break those references?

### While Editing
- **Preserve the existing structure** unless it's broken. Consistent structure > creative reorganization.
- **Update the description** if the skill's scope changes. This is the discovery signal — stale descriptions cause missed loads.
- **Add to `## Coverage`** (subsystem skills). Mark newly documented concerns and remaining gaps.
- **If extending with new content over ~100 lines:** consider moving detail to `references/` and linking from the main body.

### After Editing
- Run the validation checklist above.
- If the skill's `name` changed: rename the folder too. They must match.
- If the skill moved: update any cross-references in other skills.

---

## Should This Be a Skill?

Before creating a skill, ask:

```
Q: Will an agent encounter this situation more than once?
├─ No  → Skip. One-off knowledge belongs in ADRs or logs.
└─ Yes → Q: Does the situation have a natural trigger phrase?
         ├─ No  → Consider a command or an auto-injected instruction instead.
         └─ Yes → Q: Is the knowledge > 3 sentences AND not obvious from reading the code?
                  ├─ No  → Skip. Short/obvious info doesn't need a skill.
                  └─ Yes → Create the skill.
```

**Skills are for discoverable, reusable expertise.** If the knowledge is already obvious from reading the code, or never surfaces in a way the agent would detect, a skill adds noise without value.

---

## References

- **Canonical source:** <https://opencode.ai/config.json> — JSON Schema for `skills` config
- **Official docs:** <https://opencode.ai/docs/skills> — Skill placement, loading, permissions
- **Open standard:** <https://agentskills.io> — The SKILL.md open standard (works across 20+ agents)
- **Claude Code skill-development:** [anthropics/claude-code](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/skill-development/SKILL.md) — Canonical progressive disclosure patterns from Anthropic
- **OpenAI skill-creator:** [openai/skills](https://github.com/openai/skills/blob/b0401f07/skills/.system/skill-creator/SKILL.md) — Progressive disclosure design principle from OpenAI Codex
- **This skill's references:**
  - [`references/common-mistakes.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/common-mistakes.md) — Detailed mistake examples with fixes
  - [`references/body-patterns.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/body-patterns.md) — Full pattern catalog, formatting rules, directory templates
  - [`references/format-choice.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/format-choice.md) — Research-backed guidance on tables vs. lists vs. prose for skill content
  - [`references/frontmatter-rules.md`](file:///home/opencode/.config/opencode/skills/making-editing-skills/references/frontmatter-rules.md) — Complete frontmatter field documentation, naming constraints, description examples
- **Related skills:** `customize-opencode` (config), `command-creation-guide` (commands), `capture-subsystem` (codebase research skills)
