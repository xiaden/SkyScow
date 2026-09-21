---
name: decomposing-design-documents
description: Turn an accepted design document into dependency-ordered implementation plans, contracts, and cross-validation. Use when the user asks to decompose a design into multiple coordinated plans; do not use for a single plan or plan execution—use Exec-Planner or feature-execution.
---

# Decomposing Design Documents

Pipeline for turning requirements or a design document into a set of validated, dependency-ordered implementation plans. Each plan is self-contained, references concrete codebase patterns, and declares its contracts for downstream plans.

```
Requirements → [RnD-Manager DD workflow → DDAuthor] → Design Doc → Decompose → Initialize Ledger → Plan in Rounds → Cross-Validate
     ↓               ↓             ↓            ↓              ↓                    ↓                ↓
  Optional    DD Author agent   Already has  parts/README  CONTRACTS.md    artifacts/plans/pending/TASK-*-{A..Z}.md  Fixes
              for new features    one?
```

### Phase Quick Reference

| Phase | Action | Output |
 | --- | --- | --- |
 | 0 (Optional) | Dispatch RnD-Manager when a formal DD may be required; only Manager may later dispatch DDAuthor after selected evidence and disposition gates | `artifacts/designs/pending/{feature}/DD.md` |
 | 0.5 | DD Acceptance Gate — require a readable `request_context.path` capture, confirm accepted status, and compare the ledger against the verbatim user request | Recorded comparison; `REQUIREMENT_DRIFT` on omission/weakening |
 | 1 | Decompose design doc into lettered parts | `artifacts/designs/pending/{feature}/README.md` |
 | 2 | Create contracts ledger | `artifacts/designs/pending/{feature}/CONTRACTS.md` |
 | 3 | Dispatch Exec-Planner per part, validate, update ledger, close contract ownership | `artifacts/plans/pending/TASK-{feature}-{letter}-*.md` |
 | 4 | Cross-validate all plans for gaps and conflicts | Fixes applied to plan files |
 | 5 | Supersession sweep — retire superseded DDs/plans with back-pointers | Updated `Status`, back-pointers, clean `pending/` |

Phase 5 is the terminal archival/supersession phase. It is distinct from execution-plan phases and must run after cross-validation and QA readiness; a superseded artifact is removed from the executable set before any dispatch.

## Agent Integration

This skill may dispatch agents from the `.opencode/agents/` hierarchy:

 | Agent | When Used |
 | ------- | ----------- |
  | `RnD-Manager` | Phase 0: Compose the selected DD graph when requirements exist but no design doc |
 | `Exec-Planner` | Phase 3: For each plan in dependency order |

See [.opencode/agents/](.opencode/agents/) for agent specifications.

---

## Hard Rules

These exist because every one was violated during real usage and caused drift or errors.

### Planning Integrity
_(Ensure every plan is authored correctly, ordered correctly, and scoped to a single subagent dispatch)_

1. **Never write plans directly.** Always dispatch to the Exec-Planner agent. Direct plan authoring skips codebase research and produces layer violations, wrong method signatures, and missing patterns.
2. **Never plan out of dependency order.** A plan referencing methods from an unplanned upstream part will guess signatures.
3. **Never combine parts into one subagent call.** Each part gets its own dispatch with focused context.

### Validation & Ledger Rules
_(Govern quality gates and the anti-drift ledger)_

4. **Never skip the ledger update.** The contracts ledger is the only mechanism preventing cross-plan drift. Update it after every validated plan.
5. **Validate at both boundaries.** Validate each plan structurally when it is created; after the complete plan set exists, run cross-plan validation as one graph-level check. Do not gate or cross-validate a knowingly incomplete future set.

### Session Rules
_(Govern continuity across context boundaries)_

## Planning and quality boundaries

1. Derive implementation obligations and real producer/consumer prerequisites before creating plan containers.
2. Build the implementation DAG and close ownership before packing phases or plans.
3. Use canonical QA applicability and repository validation policy downstream; do not manufacture universal quality or commit milestones inside every plan.
4. A plan exposes changed surfaces, contracts, dependencies, downstream owners, and explicit quality obligations required by the request or accepted architecture.
5. Code review, tests, security review, and documentation are selected by their canonical owners and observable triggers, not inserted as universal plan steps.
---

## Phase 0: Create Design Document (Optional)

**Entry criteria:** Requirements exist but no design document has been created yet.
**Exit criteria:** If `DD_REQUIRED`, the selected graph has produced a design document that is reviewed by the user and ready for decomposition. Plan-only and research-only routes terminate without DD authoring or partial DD artifacts.

**Skip this phase if:** A complete and reviewed design document already exists at `artifacts/designs/pending/{feature}/DD.md`

If the user has requirements but no design doc, dispatch RnD-Manager to compose
the smallest sufficient DD graph. The Manager selects only the capabilities needed
by the evidence and risk, and may route plan-only or research-only work without
creating a DD. Do not dispatch DDAuthor directly; it is the final authoring stage
owned by Manager:

```yaml
# Dispatch to RnD-Manager
contextFiles:
  - artifacts/requests/CTX_<two-word-slug>.md     # Required source conversation
  - AGENTS.md                                      # Architecture rules
  - {layer_instructions_file}  # Layer patterns

request_context: "artifacts/requests/CTX_<two-word-slug>.md"

task:
  type: CREATE
  title: "{feature title}"
  requirements:
    - "{requirement 1 from user}"
    - "{requirement 2 from user}"
  researchFocus:
    - "existing patterns for {similar feature}"
    - "current {domain} implementation"
```

**After RnD-Manager returns, handle each status:**

| Status | Action |
| --- | --- |
| `DONE` | Design doc created at `artifacts/designs/pending/{feature}/DD.md`. Present to user for review; once approved, proceed to Phase 1. |
| `NEEDS_DECISION` | Present Manager's questions to the user. Collect answers. Re-dispatch with answers appended to requirements. Do not proceed to Phase 1 until `DONE` is returned. |
| `BLOCKED` | Critical information is missing or a DD stage failed. Stop execution and discuss the blocker with the user. Do not re-dispatch until the blocker is resolved. |

---

## Phase 1: Decompose

**Entry criteria:** A complete and reviewed design document exists at `artifacts/designs/pending/{feature}/DD.md`.
**Exit criteria:** `artifacts/designs/pending/{feature}/README.md` created and reviewed by user.

**Input:** Design document (e.g., `artifacts/designs/pending/{feature}/DD.md`)
**Output:** `artifacts/designs/pending/{feature}/README.md`

Read the design doc and repository facts. Derive the work before creating plan containers:

1. Enumerate concrete implementation obligations and their owning package.
2. Identify only real prerequisite and producer/consumer edges: contracts, interfaces, generated artifacts, registrations, migrations, or required data/control flow.
3. Build the implementation DAG and verify ownership closure. Do not derive edges from layers, alphabetical labels, commits, review order, or milestone aesthetics.
4. Pack dependency-compatible DAG nodes into worker-context phases using the canonical context policy and budget tools.
5. Pack phases into manager-review plans using request/DD/contract/annotation/changed-surface/QA/downstream review context.
6. Preserve the explicit graph in README metadata; plan labels are stable identifiers only. Independent plans remain independent and may execute concurrently when safe.

Create `artifacts/designs/pending/{feature}/README.md`:

```markdown
# {Feature} — Implementation Parts

 | Plan | Title | Depends On | Owned surfaces |
 | --- | --- | --- | --- |
 | A | {name} | None | {surfaces} |
 | B | {name} | A | {surfaces} |
 ...

## Dependency Graph
{ASCII art or equivalent existing README graph metadata}

## Dependency-ready groups
Group 1: A, G (no real prerequisites)
Group 2: B, D, E (depend on named outputs from earlier groups)
Group 3: F (depends on named outputs from Group 2)

## Per-Part Scope

### Part A: {title}
{Concise scope: what this creates, files touched, contracts exposed downstream, and any explicitly owned incomplete integration}

Detailed scope: See `PART-A-scope.md`
```

**Per-part scope documents.** Each part gets a detailed scope document in `artifacts/designs/pending/{feature}/PART-{letter}-scope.md` containing file paths, contracts, integration details, downstream ownership, and applicable repository/QA context. These specs absorb implementation detail that does not belong in the DD.

Present the README to the user for review before proceeding.

### Phase 1 Validation: DD Content Audit

Before presenting the README, verify:
- [ ] DD contains zero non-design content (no file mappings, specifications, dependency graphs, contracts, or debate transcripts)
- [ ] DD is under 200 lines

If either fails, extract implementation details to part scope documents before proceeding.

---

## Phase 2: Initialize Contracts Ledger

**Entry criteria:** `artifacts/designs/pending/{feature}/README.md` exists and has been reviewed.
**Exit criteria:** `artifacts/designs/pending/{feature}/CONTRACTS.md` created with architecture rules and empty contract sections.

**Output:** `artifacts/designs/pending/{feature}/CONTRACTS.md`

The contracts ledger accumulates verified facts from completed plans. Downstream Exec-Planner subagents receive it as context, replacing guesswork with concrete signatures.

Create from template — see [references/ledger-format.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/ledger-format.md).

Initial content:

- Feature name and design doc reference
- Architectural rules relevant to this feature (extracted from `AGENTS.md`)
- Empty sections: Collections & Methods, API Contracts, DTOs, Decisions

**The ledger must exist before any Exec-Planner subagent is dispatched.**

---

## Phase 3: Plan dependency-ready groups

**Entry criteria:** Both `README.md` and `CONTRACTS.md` exist under `artifacts/designs/pending/{feature}/`.
**Exit criteria:** All plans validated, `CONTRACTS.md` updated after each plan, and the complete plan-set graph is ready for cross-validation.

For each dependency-ready group from the explicit README graph:

### 3a. Dispatch Exec-Planner Agent

For each owned package in the group, dispatch the Exec-Planner agent. See [references/subagent-protocol.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/subagent-protocol.md) for the full dispatch protocol including prompt structure, critical rules, and common mistakes.

```yaml
# Dispatch to Exec-Planner agent (see .opencode/agents/exec-planner.md)
contextFiles:
  - artifacts/designs/pending/{feature}/DD.md              # Design doc
  - artifacts/designs/pending/{feature}/README.md            # Parts breakdown
  - artifacts/designs/pending/{feature}/CONTRACTS.md         # Current contracts
  - {layer_instructions_file}          # Per layer in this part

task:
  type: CREATE
  feature: "{feature}"
  part: "{stable-label}"
  partScope: "{scope from README}"              # concise manager-review scope and owned obligations
  priorContracts: true                          # Ledger has upstream methods
```

**Parallel dispatch** within a dependency-ready group is allowed only when existing metadata proves no dependency, output/annotation dependency, write overlap, unsatisfied prerequisite, or order sensitivity. Otherwise dispatch sequentially. Use the canonical budget tools to choose safe concurrency.

### 3b. Validate Plan

After receiving subagent output:

1. Save to `artifacts/plans/pending/TASK-{feature}-{letter}-{descriptor}.md`
2. Run `plan_read` — must parse without errors. Schema reference: [references/PLAN_MARKDOWN_SCHEMA.json](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/PLAN_MARKDOWN_SCHEMA.json)
3. Quick-scan for:
   - **Layer violations** — workflow receiving a service, component importing interface
   - **Missing implementation coordination** — dependencies, contracts, or authoritative requirements are absent. Do not require QA-owned tests, documentation, or evidence artifacts here.
   - **Coding standards violations** — mutation patterns, hardcoded values, missing error handling
   - **References to methods not in the contracts ledger or existing codebase**
    - **Context fit** — use `context_tokens` / `context_budget` with `config/agent-context-budgets.yaml`; split only when worker or manager context is unsafe or review becomes diffuse
   - **Surface notes for QA** — record changed surfaces and explicit risks so QA can apply its canonical applicability rules after implementation; do not turn those notes into plan obligations

Fix issues before proceeding. Re-run `plan_read` after fixes.

### 3c. Update Contracts Ledger

After validating **each plan** (not after each round), update CONTRACTS.md:

 | What to record | Example |
 | --- | --- |
  | Methods created | `resolve_file_to_library(db: Database, file_id: str) -> LibraryFileDict` |
  | API endpoints | `POST /api/v1/navidrome/similar-track` — body: SimilarTracksRequest, auth: verify_key, returns: SimilarTracksResponse |
 | DTOs | `TasteProfile(nd_user, clusters, backbone_id, total_track_count, generated_at_ms)` |
 | Collections | `navidrome_play_history` — _key: `{nd_user}:{nd_id}`, indexes: [...] |
 | Decisions | "Workflows take `db: Database` directly, not service wrappers" |

### 3d. Proceed to Next Round

The next round's subagents receive the updated ledger. This is the anti-drift mechanism.

---

## Phase 4: Cross-Validate

**Entry criteria:** All parts have plans in `artifacts/plans/pending/TASK-{feature}-{A..Z}-*.md`, each individually validated.
**Exit criteria:** All cross-validation checks pass or issues are fixed; results presented to user.

After all plans exist and are individually valid:

   | **Dependency completeness** | Every producer/consumer edge is explicit, its producer and consumer owners exist, and prerequisites are ordered; a plan may leave downstream callers incomplete when those callers have valid later owners. PlanGate validates closure of the whole graph, not global integration after each plan |
  | **Contract consistency** | JSON shapes, method signatures, migrations, registrations, and generated artifacts referenced across plans are compatible |
  | **Graph safety** | The plan-set graph is acyclic, shared writes have an owner, migration ordering is safe, and independent plans do not gain artificial edges |
  | **Implementation ownership** | Every authoritative requirement, dependency, contract, and architectural invariant has one clear owner |
  | **Coverage** | Every authoritative design requirement maps to at least one plan |
  | **Gaps** | Methods or integration needed downstream but never created or owned |
  | **Overlap** | Two plans creating the same artifact without an explicit handoff |
  | **QA handoff** | Changed surfaces and explicit user/architecture quality obligations are visible to QA; absence of a test/docs step is not a plan gap |

Fix issues by editing plan files directly. Update CONTRACTS.md if fixes change any contracts. Do not fail a plan set merely because an earlier plan leaves callers unfinished when a present later plan owns those callers.

Present the cross-validation results to the user with specific issues and fixes applied.

---

## Quality handoff

The planning pipeline produces a validated implementation DAG, ownership closure, and plan set. Expose changed surfaces, explicit user/architecture obligations, contracts, downstream ownership, and repository-defined verification context to the existing execution and QA workflows. Do not manufacture universal test, build, security, review, or commit steps in every phase or plan; canonical QA applicability and repository validation policy remain authoritative. A commit may occur at any Git-approved boundary and is not implied by plan lifecycle.

---

## Context Budget Management

Large features will exceed a single session. The skill is designed for this.

**The contracts ledger IS the continuity artifact.** When resuming in a new session:

1. Read `artifacts/designs/pending/{feature}/README.md` — explicit dependency graph and dependency-ready groups
2. Read `artifacts/designs/pending/{feature}/CONTRACTS.md` — all completed decisions
3. Check which plans exist in `artifacts/plans/pending/TASK-{feature}-*.md`
4. Resume at the next dependency-ready incomplete group

**Budget policy:** Use `config/agent-context-budgets.yaml` as the sole policy source. Measure assembled subsections with `context_tokens` and use `context_budget` for project worker/phase/manager projections. Do not duplicate numeric ceilings or infer plan boundaries from dispatch counts.

**If budget is tight within a round:**

- Finish the current plan dispatch + validation + ledger update
- Stop at the round boundary
- Do NOT write remaining plans directly to "save time"

---

## Validation Checklist

Before declaring feature planning complete:

- [ ] All parts have plans in `artifacts/plans/pending/TASK-{feature}-{A..Z}-*.md` → no unowned obligations
- [ ] All plans parse via `plan_read` → schema compliance
- [ ] CONTRACTS.md has entries for every shared method/API/DTO across all plans → ledger complete
- [ ] Cross-validation found no unresolved ownership, dependency, contract, cycle, or unsafe-write issues → coherent plan-set graph
- [ ] No plan references a producer or consumer without an explicit real edge and owner
- [ ] User has reviewed README and CONTRACTS.md → alignment
- [ ] Plans expose changed surfaces, dependencies, contracts, and explicit requested/architectural quality obligations to QA; QA owns test and documentation applicability
- [ ] Plans whose changed surface is security-sensitive identify the observable surface for downstream security review; do not add a security-review deliverable unless the user or accepted architecture makes it part of implementation
- [ ] No plans contain hardcoded values, mutation patterns, or console.log references
- [ ] Plans for behavioral changes specify observable behavior and contracts needed to implement it; no universal coverage target or test artifact is required
---

## References

Reference files loaded on demand. Read when you need detail beyond the core workflow.

### [ledger-format.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/ledger-format.md)

CONTRACTS.md template and update rules. Use during Phase 2 (initialization) and Phase 3c (updating after each plan). Covers the full template with section-by-section format, field requirements, and the six update rules (append-only, full signatures, date-stamping, etc.).

### [subagent-protocol.md](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/subagent-protocol.md)

How to construct Exec-Planner subagent dispatch calls that produce correct, drift-free plans. Use during Phase 3a (dispatch). Covers prompt structure (TASK → DESIGN REF → CONTRACTS → OUTPUT → CONSTRAINTS), critical rules (inline ledger content, scope boundaries, one part per dispatch), and common subagent mistakes with fixes.

### [PLAN_MARKDOWN_SCHEMA.json](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/PLAN_MARKDOWN_SCHEMA.json)

JSON Schema for task plan markdown files. Use during Phase 3b (validation) to verify plan structure — required fields (`title`, `phases`), phase numbering, flat step lists (no nesting), and annotation format. The plan parser consumes this schema; `plan_read` failures often trace to schema violations.

### [ADR_MARKDOWN_SCHEMA.json](file:///home/opencode/.config/opencode/skills/decomposing-design-documents/references/ADR_MARKDOWN_SCHEMA.json)

JSON Schema for Architecture Decision Record markdown files. Relevant when a plan's implementation spawns an ADR. Covers required metadata (`status`, `date`, `tags`), required sections (`Context`, `Decision`, `Consequences`), and optional fields (`source_log`, `supersedes`).


## Lifecycle and Contract Gates

### Phase 0.5: DD Acceptance Gate

Every DD creation or amendment must carry a readable
`request_context.path` to an `artifacts/requests/CTX_*.md` conversation snapshot.
Read the snapshot before validating the immutable requirement ledger. A summary,
DD, or handoff goal cannot replace the source capture; missing or unreadable
context blocks acceptance and decomposition.

Before decomposition, the DD must have a recognized accepted status (`Approved` or `Completed`). An `Approved` DD may remain in `pending/` only when its metadata explicitly names the prerequisite disposition, responsible owner, and transition condition; without those fields it is stale/invalid and cannot be decomposed, executed, or archived as complete. A `Completed` DD belongs in `artifacts/designs/completed/`. Compare the DD requirement ledger against the verbatim original user request and record that comparison. If any ledger item is omitted, weakened, deferred, inverted, or contradicted, stop with `REQUIREMENT_DRIFT`; do not decompose.

Every plan's `Ownership` must name the implementation files and coordination boundaries it owns. Use call-graph/import checks when needed to establish dependency or contract closure, and record uncertainty honestly. Do not require universal resolved/unresolved edge inventories or integration-test evidence; unresolved edges block only when they prevent satisfying an authoritative requirement or architectural invariant.
### Phase 5: Supersession Sweep

When a later artifact supersedes a DD or plan, update the superseded file's `Status`, add a back-pointer, and remove it from the executable set. Do not leave superseded work in `pending/`.

### Anti-Churn and Ledger Rules

- Each feature has exactly one authoritative requirement ledger. Amendments append a dated amendment or fully supersede the ledger; never create duplicate section numbers or stacked contradictory clauses.
- Remediation reopens the owning plan, or is one bounded bridge with named predecessor and successor. Lettered/generational families (R, D2R, Q3-A..K) are permitted **only** under the successor-graph rules below.

### Successor-Graph Rules (generational families)

A generational family is allowed when every condition below holds; otherwise remediation must reopen the owning plan:

1. **Explicit successor graph.** Record each generation as an explicit predecessor → successor edge with a bounded scope (the specific symbols/files it reworks) and a rationale for why the predecessor's step cannot simply be reopened.
2. **No flat-model violation.** The successor edge must be representable: the successor depends on, and does not silently replace, the predecessor. Do not leave a successor for which no dependency edge can be drawn.
3. **Supersession metadata and back-pointers.** The predecessor's `Status` must be updated to `Superseded`, and both files must carry matching back-pointers (predecessor names the successor; successor names the predecessor).
4. **Exec-PlanGate approval.** After every plan required for the coordinated group exists and is individually valid, Exec-Planner evaluates coordination triggers. A triggered generational family requires a recorded current `Exec-PlanGate: PASS` covering the successor graph before execution; an untriggered group records Planner-owned `plan_gate: status: NOT_REQUIRED` with observable rationale. Do not gate a knowingly incomplete future group.
5. **Cross-plan validation timing.** Validate each plan before it joins the complete group; perform cross-plan validation only after the complete group exists.
