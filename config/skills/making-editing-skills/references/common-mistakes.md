# Common Mistakes When Writing Skills

## Contents
- [Mistake 1: Vague Descriptions](#mistake-1-vague-descriptions)
- [Mistake 2: Name/Folder Mismatch](#mistake-2-namefolder-mismatch)
- [Mistake 3: SKILL.md Wrong Capitalization](#mistake-3-skillmd-wrong-capitalization)
- [Mistake 4: Nested Reference Chains](#mistake-4-nested-reference-chains)
- [Mistake 5: Monolithic SKILL.md (No Progressive Disclosure)](#mistake-5-monolithic-skillmd-no-progressive-disclosure)
- [Mistake 6: Over-Explaining](#mistake-6-over-explaining)
- [Mistake 7: Writing a Skill When a Command Is Better](#mistake-7-writing-a-skill-when-a-command-is-better)
- [Mistake 8: Bundling Unrelated Jobs](#mistake-8-bundling-unrelated-jobs)
- [Mistake 9: Relative Links in Global Skills](#mistake-9-relative-links-in-global-skills)

---

## Mistake 1: Vague Descriptions

The description is the ONLY thing the agent sees before deciding to load the skill. A vague description = a skill that never fires.

```yaml
# ❌ Won't load — agent can't tell when this applies
description: Helps with documents

# ✅ Loads reliably — concrete triggers and outputs
description: Extract text and tables from PDF files, fill forms, merge documents.
  Use when working with PDF files or when the user mentions PDFs, forms, or
  document extraction.
```

**Fix:** Include what the skill does (verb-first), concrete output, and trigger keywords the agent will match against.

---

## Mistake 2: Name/Folder Mismatch

The folder name IS the skill name. They must match exactly.

```
# ❌ Won't load
.opencode/skills/git-release/SKILL.md  →  name: git-release    ✅
.opencode/skills/git-release/SKILL.md  →  name: release-tools  ❌

# ✅ Correct
.opencode/skills/git-release/SKILL.md  →  name: git-release    ✅
```

---

## Mistake 3: SKILL.md Wrong Capitalization

The filename must be `SKILL.md` in ALL CAPS. Any other capitalization will not be discovered.

```
# ❌ Won't load
.opencode/skills/my-skill/skill.md
.opencode/skills/my-skill/Skill.md
.opencode/skills/my-skill/SKILL.MD

# ✅ Correct
.opencode/skills/my-skill/SKILL.md
```

---

## Mistake 4: Nested Reference Chains

Keep references one level deep from SKILL.md. Nested chains confuse the agent about what to load.

```
# ❌ Agent may use head -100 to preview instead of reading fully
SKILL.md → references/advanced.md → references/details.md → references/more.md

# ✅ One level deep — agent reads complete files
SKILL.md → references/advanced.md
SKILL.md → references/api-reference.md
```

All reference files should link directly from SKILL.md, never from another reference file.

---

## Mistake 5: Monolithic SKILL.md (No Progressive Disclosure)

Putting everything in one file defeats the purpose of the three-level loading system. The agent pays the context cost for all content every time the skill triggers, even when most of it isn't relevant.

```
# ❌ Context bloat — 800+ lines in SKILL.md
skill-name/
└── SKILL.md  (everything inline — detailed examples, edge cases, API references)

# ✅ Progressive disclosure — index + on-demand references
skill-name/
├── SKILL.md               (core workflow, <500 lines)
└── references/
    ├── patterns.md         (detailed patterns — loaded only when needed)
    ├── advanced.md         (advanced techniques — loaded only when needed)
    └── api-reference.md    (API docs — loaded only when needed)
```

**Fix:** Treat SKILL.md as an index. Keep core procedures and decision guidance inline. Move detailed patterns, examples, edge cases, and API references into `references/` files.

---

## Mistake 6: Over-Explaining

Skills are instructions for agents, not novels. Every sentence should earn its place. If a paragraph says what a heading already implied, cut it.

**Signs of over-explaining:**
- Paragraphs that restate the heading in prose form
- Background context the model already knows (stdlib behavior, language syntax)
- Multiple examples showing the same pattern with minor variations

**Fix:** Be imperative. State the rule, give one clear example, move on.

---

## Mistake 7: Writing a Skill When a Command Is Better

| Create a skill when... | Create a command when... |
|------------------------|--------------------------|
| The agent should auto-detect the need | The user explicitly initiates the action |
| The workflow has a natural trigger phrase | The workflow is user-driven (`/deploy`, `/review`) |
| It encodes domain conventions or knowledge | It's a repeatable action with arguments |

**Fix:** If the user always types `/something` to start the workflow, it's a command. If the agent should recognize "I need to do X" and load the skill automatically, it's a skill.

---

## Mistake 8: Bundling Unrelated Jobs

```yaml
# ❌ Too broad — description gets vague, load decisions get muddled
description: Handles releases, version bumps, deploy, changelog, and notifications.

# ✅ One job per skill
description: Draft release notes from merged PRs, propose a semver bump, and
  emit a gh release create command. Use when preparing a tagged GitHub release.
```

**Fix:** One skill, one job. If you need version bump AND deploy AND changelog, create three skills that the agent can chain together.

---

## Mistake 9: Relative Links in Global Skills

Skills in `~/.config/opencode/skills/` sit outside any workspace. When SKILL.md links to a reference file with a relative path like `references/patterns.md`, the agent resolves it from the **workspace root**, not the skill's directory — so it looks for `$WORKSPACE/references/patterns.md` instead of `~/.config/opencode/skills/my-skill/references/patterns.md`. Works in one workspace, breaks in every other.

```
# ❌ Relative link — resolves from cwd (the workspace), not the skill dir
See [references/patterns.md](references/patterns.md) for details.

# ✅ Absolute file:// URI — works from any workspace
See [references/patterns.md](file:///home/opencode/.config/opencode/skills/my-skill/references/patterns.md) for details.
```

**Fix:** Use absolute `file://` URIs for all reference links in global skills. Workspace-local skills (in `.opencode/skills/`) can use relative paths safely since they share the workspace root.
