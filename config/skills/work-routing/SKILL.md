---
name: work-routing
description: Canonical authority for who owns the next unit of work — direct work versus delegation, task tiers, bounded localization, the Change DAG size threshold, R&D evaluation routing, progressive research escalation, researcher scope signals, and QA/support owner selection. Use before choosing execution, investigation, design, or QA ownership; do not use to construct dispatch prompts, handoff schemas, or Change DAG/DD tool operation.
---

# Work Routing

Answers one question: **who owns the next meaningful unit of work?**

This is the canonical authority for routing ownership. It decides direct-versus-delegated work, task-shape/tier interpretation, bounded localization, implementation-size routing, architectural/R&D routing, research escalation, researcher scope-signal consumption, and QA/support owner selection.

It does **not** define:

- how to construct a native `task` prompt — the `dispatching-agents` skill owns dispatch construction;
- agent-specific handoff schemas — each agent's dispatch reference owns those;
- Change DAG tool operation — the `change-dag-lifecycle` skill owns the lifecycle tools;
- Design Document internals — RnD-Manager owns them;
- QA implementation detail or Git/GitHub mechanics.

Routing selects the owner. It never builds the dispatch prompt itself.

## When to Use

Use before choosing execution, investigation, design, or QA ownership. Do **not** use this skill to construct a dispatch prompt or to operate a Change DAG.

## Task Tiers

Determine the tier from the user's request, not from broad code reading. Bounded localization (below) may confirm the implementation surface, but the tier itself is set by the request.

| Tier | Typical requests | Posture |
|------|------------------|---------|
| **MECHANICAL** | typo fixes, formatting, lint autofixes, dependency bumps | Skip ADR/log research and skill loading (except `build-fix` if the build fails); repository-defined checks for the changed surface only |
| **STANDARD** | bug fixes, single-module features, mechanical refactors | Research proportional to need — bounded/local evidence first, then a relevant local skill/governance check; load skills only when the trigger is met |
| **ARCHITECTURAL** | new patterns, cross-module features, migrations, design | R&D evaluation depth, not a duplicate discovery pass — route to RnD-Manager, which owns the selected design-evidence graph |

## Step 1 — Direct-Work Invariant (evaluate first, before any matrix)

MECHANICAL work and genuinely bounded STANDARD work stay **direct** when all of these hold:

- the requested behavior is clear;
- the implementation surface is already known, or bounded localization can establish it;
- no architectural or design decision is required;
- no specialist-owned investigation is actually necessary.

Direct-capable examples: a typo/formatting/import fix; a one-line configuration correction; a known single-file edit; an obvious failure diagnosable from a small bounded read; a simple code-structure lookup.

Known edit locations are a discovery input, not a scope downgrade. If the request introduces a new architecture pattern, a meaningful cross-layer responsibility change, an architectural migration, or an unresolved design choice, the architectural condition above fails and the work routes to RnD-Manager for R&D evaluation even when the exact files and functions are already named. RnD-Manager owns the route and may still return `DAG_ONLY`.

Never force a dispatch because a module is unfamiliar, is the first module touched this session, or was not edited previously. **Session history is not a routing input.** A first-match specialist row never overrides this invariant — no specialist row is matched when the invariant holds. This is the routing-side statement of the dispatch skill's owner-first precondition: `dispatching-agents` builds the handoff for an owner this skill already selected, and never re-decides ownership itself.

## Step 2 — Bounded Localization (only when the surface is unknown)

Bounded localization is a small, bounded source inspection whose only purpose is to answer:

- where does the requested behavior live?
- is this still one bounded local change?
- does it cross enough implementation surface to justify Change-DAG-Author?
- does it reveal architectural/design uncertainty requiring R&D evaluation?

It is permitted before routing and is the evidence source for the size threshold. It is not broad implementation exploration: keep it to the files and symbols the request names or implies, and stop once those four questions are answered. If it reveals a large implementation surface, route to Change-DAG-Author; if it reveals design uncertainty, route to RnD-Manager. A repository-wide scan is a routing failure.

## Step 3 — Ownership Matrix (first match)

The Direct-Work Invariant is evaluated before this matrix; when it holds, no row below applies. The rows are otherwise first-match, top-to-bottom.

| If... | Then the owner is... |
|-------|----------------------|
| You need R&D evaluation or design (architectural novelty, unclear architectural requirements, design uncertainty, large scope), or the user explicitly requested a DD | **RnD-Manager**, which owns the evidence-based route (`DAG_ONLY` / `DD_REQUIRED` / `RESEARCH_ONLY`), selects the design-evidence graph, and returns the result to the router |
| Implementation spans 3+ phases across layers | **Change-DAG-Author** (owns construction end-to-end and dispatches bounded Change-DAG-Workers internally) |
| A Change DAG needs independent structural/work review | **Change-DAG-Reviewer** — only for observable coordination or authority triggers, never for node count, node types, ordinary run barriers, or mechanically independent branches |
| Implementation is done, needs review | **QA-Reviewer** |
| 3+ fix attempts failed, root cause unclear | **Support-Debugger** |
| Bounded local evidence shows substantive investigation is actually needed (deep multi-file dependency tracing, unclear integration ownership, external/API facts needing verification, or repository behavior bounded localization cannot resolve) | **Support-Researcher** |
| Prior process artifacts (logs, dead ends, prior DDs) materially constrain the route | **Support-Librarian** (historical/process context only) |
| No row matches | **Change-DAG-Author** |

## Implementation-Size / Change DAG Threshold

This threshold only sizes work that already failed the Direct-Work Invariant or that bounded localization shows is too large for one bounded reasoning context.

Estimate only from evidence the bounded localization pass produced for the localized files and line ranges. Never estimate before localizing, and never fabricate estimator inputs: do not invent char/section/file counts. If bounded localization cannot establish the edit scope credibly, do not fabricate precision — treat the task as larger than one bounded reasoning context and route to Change-DAG-Author.

**Formula:**

```
weighted_chars = char_count × (1 + 0.03 × (sections - 1) + 0.015 × max(files - 1, 0))
```

Where:

- **char_count** = estimated characters of code in the edit scope (sections being edited + adjacent context needed for understanding)
- **sections** = distinct edit locations (functions, methods, blocks, types)
- **files** = number of files touched

**Routing:**

| Weighted chars | Action |
|----------------|--------|
| < 32K (TRIVIAL or SMALL) | Edit directly — the Direct-Work Invariant applies; a Change DAG at this scope adds more noise than signal |
| ≥ 32K (MEDIUM) | Change-DAG-Author authors the Change DAG; it lowers exact work by querying the service-derived decomposition frontier and dispatching one fresh bounded Change-DAG-Worker per returned node — never a single session reasoning over the whole repository |
| ≥ 80K (LARGE) or architecturally novel or requirements unclear | Route to RnD-Manager for evidence-based R&D evaluation |

## Architectural / R&D Routing

The router decides **only** whether R&D evaluation is required; it does not predeclare the route.

- An explicit user DD request establishes `DD_REQUIRED` — that comes from the user, not from the router's own estimate.
- For every other request, route to RnD-Manager for R&D evaluation when the request shows architectural novelty, unclear architectural requirements, design uncertainty, or large scope, and let RnD-Manager decide `DAG_ONLY` vs `DD_REQUIRED` vs `RESEARCH_ONLY`.
- **Do not predeclare `DD_REQUIRED`.**
- `RESEARCH_ONLY` does not authorize implementation — it never implies DD creation, Change DAG creation, or implementation authorization.

### Pre-R&D Responsibility

Before handing work to R&D, the router owns only what is necessary to transfer ownership:

1. recognize that R&D evaluation is warranted;
2. preserve the authoritative user request;
3. capture the required `request_context`;
4. pass already-known constraints and evidence; and
5. identify a concrete blocker or user decision if one exists.

The router does **not** need to independently complete broad repository exploration, broad historical log/DD discovery, full integration tracing, or external/API research before RnD-Manager. RnD-Manager owns the selected design-evidence graph and may select the local governance skills, Support-Librarian, Support-Researcher, or other R&D capabilities as needed.

This is not a license to discard evidence: already-known relevant evidence is passed downstream in the handoff. The rule is **do not require duplicate discovery**, not hide useful context.

### Consuming the R&D Result

Consume exactly the `route` / `status` / `phase` tuple — never a fieldless readiness word.

| RnD result | Router action |
|------------|---------------|
| `route: DAG_ONLY`, `status: DONE`, `phase: READY_FOR_AUTHORING` | Dispatch Change-DAG-Author to author the implementation Change DAG (carry the `request_context`). |
| `route: DD_REQUIRED`, `status: DONE`, `phase: READY_FOR_AUTHORING` | Dispatch Change-DAG-Author with the accepted DD context (carry the `request_context`). |
| `route: RESEARCH_ONLY`, `status: DONE` | Consume the bounded analysis and continue routing or return the result; no DD, no Change DAG, and no implementation authorization is implied. |
| `status: BLOCKED` or `status: NEEDS_DECISION` | Do not dispatch implementation authoring; resolve the blocker or surface the decision to the user. |

## Progressive Research Escalation

Research is proportional, not ceremonial. Escalate only as far as unresolved evidence requires:

1. **Bounded/local evidence first** — read the files and symbols the request names or implies.
2. **Load the relevant local skill/governance when applicable** — a workspace-local governance skill or instruction (`architecture-decisions`, `system-requirements`, `logging-system`) is a direct knowledge source; read it, plus one record by identity, instead of dispatching a research agent for it.
3. **Consult targeted historical context when materially useful** — `log_read` or prior decisions when they materially constrain the route; Support-Librarian is only for that process-artifact context.
4. **Support-Researcher only when unresolved substantive investigation remains.**

Select Support-Researcher only when bounded local evidence establishes that substantive investigation is actually needed, for example:

- deep multi-file dependency tracing;
- unclear integration ownership;
- external/API facts that must be verified;
- complex repository behavior that bounded localization cannot resolve.

Unfamiliarity, first-touch, or session history is not a trigger. Governance skills are direct knowledge sources, not Librarian research. Current architectural governance comes from the workspace-local `architecture-decisions` skill; current requirement governance comes from the workspace-local `system-requirements` skill.

### Researcher Scope Signal (consumer action)

Support-Researcher returns a named `scope_signal`. Consume it deterministically instead of guessing:

| `scope_signal` | Meaning | Router action |
|----------------|---------|---------------|
| `WITHIN_BRIEF` | Findings confirm the briefed surface | Continue the planned route. |
| `BROADER_SAME_REQUIREMENT` | The same user requirement has a larger inherent implementation surface (more files/layers), with unchanged product semantics | Re-evaluate routing/tier from the new evidence; route to Change-DAG-Author or RnD-Manager as the surface requires. Do not ask the user merely because more files/layers are needed. |
| `NEW_REQUIREMENT` | Research surfaced genuinely new requested behavior or changed product semantics | Apply the Scope Creep stop condition: question the user before absorbing it. |

A user question is also appropriate for `BROADER_SAME_REQUIREMENT` when the discovery creates an actual architectural choice, authority gap, or articulable risk that requires the user's decision.

## Change DAG review and repair routing

- Change-DAG-Author owns construction and may dispatch `change-dag-worker` for new semantic work, optionally dispatch `incomplete-dag-reviewer` for a trigger-driven construction question, and route known exact-work defects to `change-dag-fixer`.
- Nyx remains the top-level controller and lifecycle owner. Nyx alone selects the final `change-dag-reviewer`; it is optional and applies only to a completed, resolved, executable DAG when an observable coordination or authority trigger exists. It is not a mandatory review at every frontier, and Nyx never directly dispatches the internal Worker or Worker-only researchers.
- Final-review dispositions are consumed by Nyx: `BLOCK_RUN` sends exact-work defects to `change-dag-fixer`, semantic/graph defects to Change-DAG-Author, and authority/DD/architectural contradictions upstream; `ALLOW_WITH_FOLLOWUP` permits execution while preserving evidence for post-run QA/follow-on repair; `ALLOW` is informational.
- Follow-on repair after the execution boundary is routed normally against the real repository: small/local work may be direct, larger or cross-layer work starts a new Change DAG, and architectural work routes to R&D evaluation. Independent QA remains separate and never reopens a completed DAG.

## QA / Support Owner Selection

- **QA-Reviewer** is the primary post-change QA owner.
- **QA-PushManager** is the final publication gate for a candidate commit.
- **Change-DAG-Reviewer** is optional, read-only, and selected only from observable coordination or authority triggers by Nyx.
- **Support-Debugger** owns root-cause analysis when 3+ fix attempts failed and the root cause is unclear.
- **Support-Researcher** owns deep codebase/external research (see escalation above).
- **Support-Librarian** owns historical/process-artifact navigation only.

Independent QA is not part of Change DAG execution or archival: it never reopens a completed DAG.

## Ownership Exclusions

The router does not perform work it routes. It does **not**:

| This router does NOT... | Route instead to... |
|-------------------------|---------------------|
| Design features or create design documents | RnD-Manager |
| Create or amend a Change DAG | Change-DAG-Author |
| Independently review a Change DAG's structure and work | Change-DAG-Reviewer |
| Perform QA review | QA-Reviewer |
| Perform root cause analysis on failures | Support-Debugger |
| Conduct deep codebase research | Support-Researcher |

## Anti-Patterns

- Turn bounded localization into broad exploration. Localize only the requested behavior and its immediate edit surface; a repository-wide scan is a routing failure.
- Force a dispatch because the module is new to the session, the area is unfamiliar, or it is the first module touched. Session history is not a routing input.
- Fabricate estimator inputs before localizing. If bounded localization cannot establish the scope credibly, do not invent char/section/file counts.
- Predeclare `DD_REQUIRED` from your own estimate. Only an explicit user DD request establishes it.
- Treat "I should check to be safe" as a reason to research. Safety = articulable risk, not vague caution.
- Re-own a routed responsibility. Selecting the owner is routing; doing the specialist's work is not.
