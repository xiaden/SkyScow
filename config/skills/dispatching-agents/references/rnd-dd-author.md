# RnD-DDAuthor

Dispatch RnD-DDAuthor to create or refine a formal design document.

## When to Dispatch

**Dispatch when:**
- You need a formal design document (DD) created from requirements
- An existing DD needs refinement or expansion
- You have requirements but no architectural design yet
- RnD-Manager delegates DD creation to this agent (its primary worker)

**Do NOT dispatch when:**
- You're doing a full R&D workflow with tradeoff analysis, ideation, and estimation — use `rnd-manager` instead (it spawns this agent as part of its workflow)
- You only need implementation options — use `rnd-architect` instead
- You need creative brainstorming — use `rnd-ideator` instead
- The feature is trivial and doesn't need a design document

## Dispatch Template

```
Create a design document for [FEATURE].

**Your job is to spawn your workers:**
- Spawn Support-Researcher for deep investigation (if needed)
- Spawn RnD-Ideator for creative approaches
- Spawn RnD-Architect for implementation analysis
- Spawn RnD-Estimator for effort sizing
Do NOT design the feature yourself — orchestrate your team.

Requirements: [user requirements or path to requirements doc]
Librarian briefing: [paste briefing or "see attached context"]
Prior decisions to respect: [key constraints from Librarian]
Output: Design document in artifacts/designs/pending/
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[FEATURE]` | Feature name | "Tag autocomplete system" |
| `Requirements` | What needs to be built — inline or path to ASR/DD | "Support real-time autocomplete for tags with <50ms latency, see ASR-012" |
| `Librarian briefing` | Artifact context from Support-Librarian | Paste briefing or "see attached context" |
| `Prior decisions` | Key constraints from prior ADRs | "Must use existing tag storage (ADR-0012), trie-based lookup (ADR-0018)" |

The worker-spawn instructions are **required** — without them, RnD-DDAuthor may inline the design work instead of orchestrating.

## Expected Output

- A design document in `artifacts/designs/pending/`
- Architectural decisions with rationale
- Implementation approaches with tradeoffs
- Effort estimates per phase
- Scope boundaries and integration points

## Dispatch Variants

### Greenfield (No Codebase Constraints)

```
Create a design document for [FEATURE] — greenfield.

**Your job is to spawn your workers:**
- Skip Support-Researcher (greenfield — no existing codebase to investigate)
- Spawn RnD-Ideator for creative approaches
- Spawn RnD-Architect for implementation analysis
- Spawn RnD-Estimator for effort sizing
Do NOT design the feature yourself.

Requirements: [user requirements]
Tech stack: [languages, frameworks, platforms]
Output: artifacts/designs/pending/[feature-slug].md
```

### Brownfield (Must Integrate with Existing Codebase)

```
Create a design document for [FEATURE] — must integrate with [SYSTEM/MODULE].

**Your job is to spawn your workers:**
- Spawn Support-Researcher FIRST to investigate [integration points]
- Spawn RnD-Ideator for creative approaches (must respect existing patterns)
- Spawn RnD-Architect for implementation analysis
- Spawn RnD-Estimator for effort sizing
Do NOT design the feature yourself.

Requirements: [user requirements]
Integration points: [specific modules/services to integrate with]
Existing constraints: [ADRs, patterns, tech debt]
Output: artifacts/designs/pending/[feature-slug].md
```
