---
name: gathering-artifacts
description: Gather prior ADR, ASR, log, and design-doc context before design, planning, or routing work. Use when entering an unfamiliar area or making a decision that constrains future work; do not use for quick facts or mechanical execution of an already-validated plan.
---

# Artifact Context Gathering

Before acting on any significant task, spawn `Support-Librarian` to search the artifact corpus for relevant constraints, warnings, and context. This skill templates the prompt.

## When to Use

 | You're about to... | Use this skill |
 | -------------------- | --------------- |
  | Design a feature (RnD-Manager) | Yes — before dispatching the DD workflow |
 | Create an implementation plan (Exec-Planner) | Yes — before creating the plan |
 | Route work to a department (Nyx, RnD-Manager) | Yes — before dispatching |
 | Execute a plan phase (Exec-Worker) | No — the plan should already reflect artifact context |
 | Do a quick fact check | No — overhead not worth it |

**Threshold:** If the task touches architecture, creates artifacts, or makes decisions that constrain future work — gather context first. If it's mechanical execution of an already-validated plan — skip.

## How to Use

### Step 1: Identify the Task Shape

Determine what you're about to do and what scope it touches:

```yaml
task:
  action: "design"           # design | plan | execute | review | debug
  subject: "ML tagging pipeline redesign"
  scope: "src/components/ml, src/workflows/processing"
```

### Step 2: Spawn Support-Librarian

Use this prompt template, filling in the task details:

```
Search the artifact corpus for everything relevant to this task:

Task: {action} — {subject}
Scope: {scope}

Specific concerns:
- {any specific questions or areas of uncertainty}

Return a structured briefing with constraints (ADRs/decisions that must be respected), 
warnings (dead ends, failed approaches), context (useful background), and open questions 
(unresolved uncertainties from prior work).
```

### Step 3: Incorporate the Briefing

The Librarian returns a structured briefing. Use it:

 | Section | What to do |
 | --------- | ----------- |
 | `constraints` | These are non-negotiable. Your design/plan must comply. |
 | `warnings` | Avoid these approaches. If you must use one, document why. |
 | `context` | Consider this background. May influence your approach. |
 | `open_questions` | Surface these to the user or document your resolution. |
 | `no_relevant_artifacts` | Proceed with confidence — no prior work constrains you here. |

## Examples

For detailed walkthroughs of this skill in action, see [`references/examples.md`](file:///home/opencode/.config/opencode/skills/gathering-artifacts/references/examples.md):
- DDAuthor gathering artifact context before writing a design doc
- Nyx gathering context before routing a feature to R&D

## Formal DD ownership

Gather context for and dispatch formal design work through RnD-Manager. It owns
the complete DD workflow. RnD-DDAuthor is invoked by Manager only after the
upstream research, full adversarial review, architecture, complexity, and
estimation stages; do not dispatch DDAuthor directly for a new formal DD.

## Anti-Patterns

- **Don't skip this for "small" design decisions** — Small decisions that contradict ADRs cause big problems.
- **Don't re-search what the Librarian already found** — Trust the briefing. Read cited artifacts only if you need more detail.
- **Don't ignore `no_relevant_artifacts`** — An empty briefing is signal: you're in uncharted territory. Log your decisions for future sessions.
- **Don't spawn Librarian during mechanical execution** — If you're following a plan step-by-step, the plan author should have already gathered context.
