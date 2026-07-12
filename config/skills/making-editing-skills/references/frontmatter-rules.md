# Frontmatter Rules Reference

Complete validation rules for `SKILL.md` frontmatter fields.

## Contents
- [`name` (required)](#name-required)
- [`description` (required)](#description-required)
- [Optional Fields](#optional-fields)

---

## `name` (required)

Valid: `^[a-z0-9]+(-[a-z0-9]+)*$` — 1 to 64 characters.

| Valid | Invalid | Why |
|-------|---------|-----|
| `git-release` | `Git-Release` | No uppercase |
| `code-review` | `code_review` | No underscores |
| `api-docs` | `-api-docs` | Can't start with hyphen |
| `test-generator` | `test--generator` | No consecutive hyphens |
| `my-skill` | `myskill` in folder `my-skil` | Must match directory name |

**Hard rule:** The `name` value must match the name of the directory containing `SKILL.md`. Mismatch = skill won't load.

---

## `description` (required, 1–1024 chars)

**This is the discovery signal.** The agent sees only this field (plus the name) when deciding whether to load the skill. A vague description = a skill that never fires.

### Anatomy of an effective description

1. **What it does** — verb-first, concrete output
2. **When to use it** — trigger phrase with keywords the user or task will match
3. **Scope boundaries** — what it covers AND what it doesn't

### Quality Examples

| Quality | Example |
|---------|---------|
| **Good** | `Create consistent releases and changelogs from merged PRs, propose a semver bump, and emit a gh release create command. Use when preparing a tagged GitHub release.` |
| **Good** | `Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.` |
| **Good** | `Create, edit, and maintain OpenCode agent skills (SKILL.md files) that agents actually discover and use. Covers frontmatter rules, description writing, body structure conventions, validation, common mistakes, and when to create vs skip a skill. Use when creating a new skill, editing an existing SKILL.md, or asked about skill conventions.` |
| **Bad** | `Helps with releases` |
| **Bad** | `For working with documents` |
| **Bad** | `Skill helper` |

### Trigger Phrase Tips

- "Use when..." / "Use ONLY when..." for gated skills
- "Trigger when..." for condition-based loading
- Front-load concrete nouns: filenames (`SKILL.md`), directories (`.opencode/skills/`), actions (`creating a skill`)
- For convention skills: name the code area explicitly ("Use when editing anything under `packages/payments/`")

---

## Optional Fields

| Field | Type | Purpose |
|-------|------|---------|
| `license` | string | SPDX identifier (`MIT`, `Apache-2.0`) or free text |
| `compatibility` | string | Environment requirements ("Requires poppler-utils") |
| `metadata` | map[string]string | Arbitrary key-value pairs. Both keys and values must be strings. |

Most skills don't need optional fields. Add them only when they're genuinely useful.
