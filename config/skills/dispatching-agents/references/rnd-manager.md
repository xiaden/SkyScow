# RnD-Manager

Dispatch RnD-Manager to design features or conduct R&D analysis. RnD-Manager owns the full "thinking" phase — it spawns its own workers and returns a design document or recommendations.

## When to Dispatch

**Dispatch when:**
- A feature needs architectural design before implementation
- You need options, tradeoffs, or comparative analysis
- You need a formal design document (DD) created
- You need effort estimates and scope validation

**Do NOT dispatch when:**
- The task is a straightforward implementation with no design ambiguity → implement directly
- You need deep codebase research only → use Support-Researcher
- You need a single analysis (not full R&D) → use RnD-Architect or RnD-Ideator directly
- The feature is trivial and the design is obvious from existing patterns

## Core Dispatch Template

```
Design [FEATURE].

**Your job is to spawn your workers:**
- Spawn Support-Librarian if you need artifact context
- Spawn RnD-DDAuthor to create the formal design document
- Spawn RnD-Architect, RnD-Ideator, RnD-Estimator as needed for analysis
Do NOT create the design document yourself.

Requirements: [user requirements or path to requirements doc]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints from Librarian]
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[FEATURE]` | Feature name or short description | `Design the user authentication system` |
| `[user requirements]` | What needs to be built — inline or path to ASR/DD | `Support OAuth2 + MFA, see artifacts/requirements/ASR-012.md` |
| `[Librarian briefing]` | Librarian's artifact-context briefing | `see attached context` or paste the briefing |
| `[key constraints]` | Critical constraints from prior decisions | `Must use existing AuthService (ADR-003)` |

The worker-spawn instructions are **required** — without them, RnD-Manager may inline the design work instead of orchestrating its team.

## Expected Output

RnD-Manager returns:
- A design document in `artifacts/designs/pending/`
- Architectural recommendations with tradeoffs
- Effort estimates (TRIVIAL/SMALL/MEDIUM/LARGE/EPIC)
- Scope validation (via Support-PatternEnforcer)

## Dispatch Variants

### Research-Only R&D

When you need analysis and recommendations but no formal design document. RnD-Manager spawns advisory agents but skips RnD-DDAuthor.

```
Research [TOPIC] for [PURPOSE].

**Your job is to spawn your workers:**
- Spawn Support-Librarian if you need artifact context
- Spawn RnD-Architect for implementation options and tradeoffs
- Spawn RnD-Ideator for creative approaches
- Spawn RnD-Estimator for effort sizing
Do NOT create a design document — research output only.

Research question: [specific question or area to investigate]
Constraints: [any boundaries — budget, tech stack, timeline]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints from Librarian]
```

**When to use:** Evaluating a technology choice, exploring feasibility, sizing work before committing.

### Tradeoff-Focused Analysis

When the question is "which approach is better?" rather than "design this feature."

```
Analyze tradeoffs for [DECISION].

**Your job is to spawn your workers:**
- Spawn Support-Librarian if you need artifact context
- Spawn RnD-Architect to compare approaches with concrete tradeoffs
- Spawn RnD-Estimator for effort sizing per approach
Do NOT create a design document — comparative analysis only.

Decision: [what are we deciding between?]
Candidates: [approach A, approach B, approach C]
Evaluation criteria: [performance, maintainability, cost, timeline — pick 2-4]
Constraints: [any non-negotiable boundaries]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints from Librarian]
```

**When to use:** Choosing between libraries, patterns, architectures, or third-party services.

### Greenfield Design

For features with no existing codebase constraints. Skip the Librarian step.

```
Design [FEATURE] — greenfield, no existing codebase constraints.

**Your job is to spawn your workers:**
- Skip Support-Librarian (greenfield — no prior artifact context needed)
- Spawn RnD-DDAuthor to create the formal design document
- Spawn RnD-Ideator for creative approaches
- Spawn RnD-Architect for implementation options
- Spawn RnD-Estimator for effort sizing
Do NOT create the design document yourself.

Requirements: [user requirements]
Tech stack: [languages, frameworks, platforms]
Design goals: [scalability, simplicity, extensibility — pick 2-3]
```

**When to use:** New project, new service, or isolated subsystem.

### Brownfield Design

For features that must integrate with an existing, complex codebase.

```
Design [FEATURE] — must integrate with existing [SYSTEM/MODULE].

**Your job is to spawn your workers:**
- Spawn Support-Librarian FIRST to gather all relevant ADRs, logs, and design docs
- Spawn RnD-DDAuthor to create the formal design document
- Spawn RnD-Architect for implementation options (must respect existing patterns)
- Spawn RnD-Estimator for effort sizing
- Spawn Support-PatternEnforcer to validate consistency with existing patterns
Do NOT create the design document yourself.

Requirements: [user requirements]
Integration points: [specific modules, services, or APIs to integrate with]
Existing constraints: [ADRs, architectural patterns, tech debt to work around]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints from Librarian]
```

**When to use:** Adding features to established codebases, integrating with legacy systems.

### With Pre-Existing Artifact Context

When you've already run Support-Librarian and have a briefing ready.

```
Design [FEATURE].

**Your job is to spawn your workers:**
- Librarian already completed — briefing attached below
- Spawn RnD-DDAuthor to create the formal design document
- Spawn RnD-Architect for implementation options
- Spawn RnD-Estimator for effort sizing
Do NOT create the design document yourself.

Requirements: [user requirements]
Librarian briefing:
[paste the full Librarian briefing here]
Prior decisions to respect:
- [decision 1 from Librarian]
- [decision 2 from Librarian]
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| RnD-Manager created the DD itself instead of spawning RnD-DDAuthor | Ensure bolded worker-spawn block is present. Add: `Verify you spawned RnD-DDAuthor` |
| RnD-Manager returned without a design document | Feature may be too small. Re-dispatch with: `A design document in artifacts/designs/pending/ is required output.` |
| DD is missing effort estimates | Re-dispatch with: `Ensure RnD-Estimator is spawned and effort estimates are included.` |
| DD contradicts an existing ADR | Support-Librarian wasn't spawned. Re-dispatch with explicit Librarian instruction and attach the conflicting ADR as a constraint. |
