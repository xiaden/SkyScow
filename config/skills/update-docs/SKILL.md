---
name: update-docs
description: Update project documentation to match code changes — generate codemaps, refresh READMEs, detect doc/code drift using AST analysis. Use when updating documentation after code changes, generating codemaps, verifying doc accuracy, or detecting stale documentation. Do NOT use for writing API reference docs from scratch (use doc-coauthoring) or for creating new skill files (use making-editing-skills).
---

# Documentation Update

**Purpose:** Keep documentation synchronized with code changes through systematic analysis, codemap generation, and drift detection. Docs should always reflect the actual codebase state.

---

## When to Use

**Trigger conditions:**

- Code changes have been merged and docs need updating
- Generating or refreshing codemaps for a codebase area
- User asks to verify documentation accuracy
- Detecting stale or drifted documentation
- Updating README after feature additions or removals

**Do NOT use this skill when:**

- Writing API reference documentation from scratch (use `doc-coauthoring`)
- Creating or editing skill files (use `making-editing-skills`)
- Writing architecture decision records (use ADR tools)
- Generating user-facing tutorials or guides (use `doc-coauthoring`)
- The codebase hasn't changed and docs are already current

---

## How This Skill Is Structured

This skill uses progressive disclosure to keep context lean:

| Level | What loads | Content |
|-------|-----------|---------|
| **Body** (always loaded) | Core workflow, decision tables, validation checklist | The 5-step doc update process, drift detection checks, when-to-update rules |
| **References** (loaded on demand) | Templates, format examples, detailed patterns | Codemap template, README template, drift report format |

---

## Core Workflow

### 1. Identify Changed Code

```bash
git diff --name-only HEAD~5..HEAD    # recent changes
git log --oneline -20                 # what changed and why
```

For each changed file, gather context using AFT tools:

| Tool | Use for |
|------|---------|
| `aft_outline` | File structure, exported symbols, heading hierarchy |
| `aft_zoom` | Read specific function/class source with signatures |
| `aft_search` | Find all references to a changed symbol across the codebase |
| `aft_inspect` | Check for broken imports, dead code, or diagnostics |

### 2. Analyze Code with AST

Use AST-aware analysis to extract accurate documentation from code:

- **Symbol extraction:** Use `aft_outline` to get all exported symbols (functions, classes, types) with their signatures and line ranges
- **JSDoc/TSDoc parsing:** Read doc comments directly from source via `aft_zoom` — these are the single source of truth for public API docs
- **Dependency mapping:** Use `aft_zoom` with `callgraph: true` to understand what a function calls and what calls it
- **Environment variables:** Parse `.env.example` for required configuration

**Key principle:** Generate documentation *from* the code, not *about* the code. Every claim in docs should be traceable to a symbol, signature, or comment in the source.

### 3. Detect Doc/Code Drift

Compare existing documentation against actual code state:

| Check | Method |
|-------|--------|
| File paths mentioned in docs | Verify each path exists with `glob` or `read` |
| Function signatures in docs | Compare against `aft_zoom` output |
| Exported symbols listed | Compare against `aft_outline` output |
| Code examples in docs | Verify they compile/type-check |
| Links to other docs | Verify target files exist |
| Environment variables | Compare against `.env.example` |

**Drift report format:** Use the template in [`references/drift-report-format.md`](file:///home/opencode/.config/opencode/skills/update-docs/references/drift-report-format.md). Every stale/missing item must reference a source-of-truth location in the codebase.

### 4. Update Documentation

Apply fixes based on drift report, prioritized:

1. **Remove stale references** — delete or update paths, signatures, examples that no longer match
2. **Add missing docs** — document newly exported symbols, new env vars, new features
3. **Refresh templates** — update README setup commands, codemap timestamps
4. **Verify examples** — ensure code snippets compile and run

### 5. Verify Accuracy

Before committing:

- [ ] All file paths in docs verified to exist
- [ ] Code examples compile/type-check
- [ ] All internal and external links tested
- [ ] Freshness timestamps updated
- [ ] No obsolete references remain
- [ ] Codemaps generated from actual code (not hand-written)
- [ ] Version numbers updated where applicable (package.json, config files)

---

## Codemaps

Codemaps are structured documentation for a codebase area, generated from code. Use the template in [`references/codemap-template.md`](file:///home/opencode/.config/opencode/skills/update-docs/references/codemap-template.md).

**Rules:**
- Generate from `aft_outline` and `aft_zoom` output — never hand-write module descriptions
- Keep under 500 lines per codemap
- Include freshness timestamp (last updated date)
- Store in `docs/CODEMAPS/` with an `INDEX.md` linking all codemaps

## README Updates

Use the template in [`references/readme-template.md`](file:///home/opencode/.config/opencode/skills/update-docs/references/readme-template.md).

**Rules:**
- Setup commands must actually work — test them
- Link to codemaps for architecture details, don't duplicate
- List features that exist in the code, not features planned

---

## When to Update

**Always update docs when:**
- New major feature added
- API routes changed (added, removed, signature changed)
- Dependencies added or removed
- Architecture significantly changed
- Setup process modified
- Environment variables added or renamed
- Public API signatures changed (update JSDoc/TSDoc comments)
- TODO/FIXME comments addressed or need resolution

**Skip when:**
- Minor bug fixes with no API impact
- Cosmetic changes (formatting, comments)
- Internal refactoring without external behavior changes

---

## References

- **Codemap template:** [`references/codemap-template.md`](file:///home/opencode/.config/opencode/skills/update-docs/references/codemap-template.md)
- **README template:** [`references/readme-template.md`](file:///home/opencode/.config/opencode/skills/update-docs/references/readme-template.md)
- **Drift report format:** [`references/drift-report-format.md`](file:///home/opencode/.config/opencode/skills/update-docs/references/drift-report-format.md)
- **Cliche data conventions:** [`references/cliche-data.md`](file:///home/opencode/.config/opencode/skills/update-docs/references/cliche-data.md) — Placeholder data rules for documentation examples
- **Related skills:** `doc-coauthoring` (writing docs from scratch), `making-editing-skills` (skill conventions), `capture-subsystem` (documenting subsystem mental models)
