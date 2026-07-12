---
name: capture-subsystem
description: Capture a subsystem's mental model, invariants, and key files as a reusable SKILL.md after deep codebase research. Use when you've explored 5+ files to understand one concept, traced IPC/process/worker/pipeline topology, or answered "how does X actually work" from scratch — save the understanding now to prevent re-researching it every session. For stable, non-churning code areas; use artifact-logging for ephemeral observations.
---

# Capture Subsystem

You have just done expensive research on a stable subsystem. Capture the mental model now — once — rather than rediscovering it every session.

## Check Before Creating

**Before creating a new skill, check if one already exists** for this subsystem. Skills live in `{project_skills_dir}` and `{tooling_skills_dir}`. If a skill exists:
- **Extend it** with what you just learned — do not create a duplicate
- Update the `## Coverage` section
- If you learned something that contradicts the skill, fix the skill and note the change

A partial skill that labels its gaps is always preferable to no skill. A partial skill with *unlabeled* gaps causes confident wrong reasoning — worse than no skill.

## What Belongs

A subsystem skill answers: **"What does a competent engineer need to know before touching this area?"**

**Include:**
- The intended mental model — why this architecture, not just what it does
- Process/thread/IPC topology (who owns what, how parts communicate)
- Key invariants an agent must not violate
- Which files are canonical owners of each concern
- How the subsystem connects to the rest of the system (entry/exit points)
- Citations to the ADRs/DDs that motivated the design

**Do not include:**
- Implementation details that change with normal refactors (method signatures, variable names)
- Information already obvious from reading one file
- Anything the model already knows (Python stdlib, FastAPI patterns, etc.)
- Episodic history ("we tried X and it failed") — that belongs in logs/ADRs

## The Test

If an agent reads all the files in the subsystem but still doesn't know *why* it's structured this way or *what would break* if they changed it naively — the gap belongs in a skill.

## Structure

Place project-specific subsystem skills in `{project_skills_dir}/{subsystem-name}/SKILL.md`.
Place generic/tooling skills in `{tooling_skills_dir}/{skill-name}/SKILL.md`.

```
{project_skills_dir}/my-subsystem/
├── SKILL.md                  ← frontmatter + mental model + key files table + invariants
└── references/               ← optional: full topology, schema, edge cases if large
    └── architecture.md
```

Keep `SKILL.md` scannable — the body should contain what every invocation needs. Move detailed examples, topology diagrams, and edge cases to `references/` and link them.

## Required Sections

Every subsystem orientation skill must include these sections, in order:

1. **One-paragraph mental model** — the "explain it to a new hire in 60 seconds" summary
2. **Coverage** — formal declaration of what this skill documents and what it does not
3. **Key Files table** — area → canonical file, no descriptions, just the map
4. **Critical Invariants** — the things an agent must never break, stated as constraints
5. **Common Task Patterns** (optional) — if there are 2-3 stereotyped tasks that are easy to get wrong

## Coverage Section Format

Every subsystem skill **must** include a `## Coverage` section immediately after the mental model. This is the staleness and incompleteness signal for future agents.

```markdown
## Coverage

**Documented:** <comma-separated list of concerns this skill covers>

**Not yet documented:** <comma-separated list of known gaps, or "none known">

**Last extended:** YYYY-MM-DD
```

Rules:
- `Documented` lists specific concerns — not the subsystem name, the *concerns*
- `Not yet documented` lists known gaps — areas that exist in the subsystem but weren't researched yet
- `Last extended` is the ISO date the skill was last written or extended
- When extending a skill, move items from `Not yet documented` to `Documented`, and add new gaps discovered
- If `Not yet documented` is empty, write `none known` — do not omit the field

## Frontmatter Discipline

The `description` field is the trigger selector. It must:
- Name the subsystem explicitly (agents match on nouns)
- List the *tasks* that should load it, not just the domain
- Be specific enough that it doesn't load for every session

See [`references/examples.md`](file:///home/opencode/.config/opencode/skills/capture-subsystem/references/examples.md) for good and bad description examples with explanations, plus a full annotated example of a well-structured subsystem skill.

## Source Citations

Every skill must cite its authoritative sources. Include at the bottom:

```
## Sources
- ADR-NNN: Title
- DD: slug (artifacts/designs/...)
```

If no ADR/DD exists for the design decision, that's a gap worth noting — the skill can serve as informal documentation until a proper ADR is written.

## Staleness Contract

A skill is a *view* over ADRs/DDs. When the underlying design changes:
- The ADR supersession and the skill update must be in the same commit
- If the skill becomes stale, it causes confident wrong reasoning — worse than no skill
- Always include a `## Sources` section so future maintainers know which ADRs to check

## References

- [`references/examples.md`](file:///home/opencode/.config/opencode/skills/capture-subsystem/references/examples.md) — Full annotated example, good/bad description patterns, and when NOT to create a skill
- Related skills: `making-editing-skills` (skill structure conventions), `artifact-logging` (logging conventions)

Base directory for this skill: /home/opencode/.config/opencode/skills/capture-subsystem
