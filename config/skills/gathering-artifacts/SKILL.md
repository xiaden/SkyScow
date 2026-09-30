---
name: gathering-artifacts
description: Gather prior process-artifact context (logs, dead ends, prior design docs) before design, decomposition, or routing work when those artifacts materially constrain the route; current governing decisions and requirements come from the workspace-local architecture-decisions and system-requirements skills. Use when prior process artifacts may materially constrain the work or when making a decision that constrains future work; do not use for quick facts or mechanical execution of an already-validated Change DAG.
---

# Artifact Context Gathering

Before design, decomposition, or routing work, assess whether prior process artifacts (logs, dead ends, prior discoveries, prior design-doc history, unresolved historical questions) materially constrain the route. Select `Support-Librarian` when they do; otherwise record the evidence-based skip in the Manager-owned routing trace. Governing decisions and requirements are a separate need — load the workspace-local `architecture-decisions` / `system-requirements` skill when current governance is materially relevant.

## Governance vs. Process History

Two distinct needs, two distinct sources:

| Need | Source |
|------|--------|
| Current architectural governance | Load the workspace-local `architecture-decisions` skill; read a known record by identity with `adr_read(name)` |
| Current requirement governance | Load the workspace-local `system-requirements` skill; read a known record by identity with `asr_read(name)` |
| Historical/process context (logs, dead ends, prior discoveries, prior DD history, unresolved historical questions, other retained process artifacts) | Select `Support-Librarian` |

Do not ask Support-Librarian to find governing ADRs/ASRs, and do not load a governance skill just because the repository has one — load it only when governance is materially relevant. A repository without the skill simply has no such corpus.

## When to Use

 | You're about to... | Use this skill |
 | -------------------- | --------------- |
  | Design a feature (RnD-Manager) | Conditional — select only when prior process artifacts materially constrain the route |
  | Create the initial semantic Change DAG (Change-DAG-Author) | Conditional — select only when prior process artifacts materially constrain the Change DAG |
  | Route work to a department (Nyx, RnD-Manager) | Conditional — select only when prior process artifacts materially constrain routing |
  | Execute a Change DAG (Nyx lifecycle control) | No — the Change DAG should already reflect artifact context |
 | Do a quick fact check | No — overhead not worth it |

**Threshold:** If prior artifacts are relevant to the task's architecture, artifact ownership, or future constraints, gather them first. If no relevant artifacts exist, log the evidence-based skip. Mechanical execution of an already-validated Change DAG skips this skill.

## How to Use

### Step 1: Identify the Task Shape

Determine what you're about to do and what scope it touches:

```yaml
task:
  action: "design"           # design | decompose | execute | review | debug
  subject: "ML tagging pipeline redesign"
  scope: "src/components/ml, src/workflows/processing"
```

### Step 2: Select Support-Librarian when warranted

When the Manager's route assessment finds materially relevant prior artifacts, use this prompt template, filling in the task details:

```
Search the artifact corpus for everything relevant to this task:

Task: {action} — {subject}
Scope: {scope}

Specific concerns:
- {any specific questions or areas of uncertainty}

Return a structured briefing with constraints (historical constraints recorded in process artifacts),
warnings (dead ends, failed approaches), context (useful background), and open questions 
(unresolved uncertainties from prior work). Do not search for governing ADRs/ASRs — the caller
loads the local governance skill for those.
```

### Step 3: Incorporate the Briefing

The Librarian returns a structured briefing. Use it:

 | Section | What to do |
 | --------- | ----------- |
  | `constraints` | These are non-negotiable. Your design/Change DAG must comply. |
 | `warnings` | Avoid these approaches. If you must use one, document why. |
 | `context` | Consider this background. May influence your approach. |
 | `open_questions` | Surface these to the user or document your resolution. |
  | `no_relevant_artifacts` | Proceed with confidence — no prior work constrains you here. |

Governing decisions and requirements are **not** part of the Librarian briefing. When they
are materially relevant, load the workspace-local `architecture-decisions` /
`system-requirements` skill and read a specific record by identity.

## Examples

For detailed walkthroughs of this skill in action, see [`references/examples.md`](file:///home/opencode/.config/opencode/skills/gathering-artifacts/references/examples.md):
- DDAuthor gathering artifact context before writing a design doc
- Nyx gathering context before routing a feature to R&D

## Formal DD ownership

Gather context for and dispatch formal design work through RnD-Manager. It owns
the selected DD graph. RnD-DDAuthor is invoked by Manager only after
sufficient selected evidence, resolved dispositions, and the required lifecycle
gates; do not dispatch DDAuthor directly for a new formal DD.

## Anti-Patterns

- **Don't skip relevant artifact context** — If prior process history materially constrains the route, select Support-Librarian regardless of task size; otherwise record why it was skipped.
- **Don't delegate governance to the Librarian** — Load the workspace-local `architecture-decisions` / `system-requirements` skill for current ADRs/ASRs; the Librarian navigates process history only.
- **Don't re-search what the Librarian already found** — Trust the briefing. Read cited artifacts only if you need more detail.
- **Don't ignore `no_relevant_artifacts`** — An empty briefing is signal: you're in uncharted territory. Log your decisions for future sessions.
- **Don't spawn Librarian during mechanical execution** — If you're following a Change DAG's exact work, the initial semantic author should have already gathered context.
