# Task Plan Syntax Reference

Plans are parsed by planning tools. Invalid structure causes parse errors.

## Template

```markdown
# Task: <Brief Title>

## Problem Statement
<What and why. Assume reader has zero context.>

## Phases

### Phase 1: <Outcome Name>
- [ ] Concrete, verifiable step
- [ ] Another step

### Phase 2: <Outcome Name>
- [ ] Step

## Completion Criteria
- Measurable success condition
- Another condition

## References
- Related issue, ADR, or prior plan
```

## Format Rules

| Element | Pattern | Note |
|---------|---------|------|
| Title | `# Task: <title>` | Required |
| Section | `## <name>` | Any `## Header` becomes a parsed key |
| Phase | `### Phase N: <title>` | N must be sequential integer (1, 2, 3...) |
| Step | `- [ ] <text>` or `- [x] <text>` | **Must be flat — no indented checkboxes** |
| Annotation | `**Notes:**`, `**Warning:**`, `**Blocked:**` | Phase-level (after steps) or step-level (indented under step) |

**Step IDs** auto-generate as `P{phase}-S{step}` (e.g., `P1-S1`, `P2-S3`).

## Writing Good Steps

| ❌ Bad | ✅ Good |
|--------|---------|
| Fix auth | Implement SessionAuthMiddleware in interfaces/api/middleware/ |
| Test stuff | Verify the project's linter passes on src/services |
| Add imports | Create config_service module with ConfigService class |
| Make it work | Update all callers of get_library() to use new signature |

**Steps must be:**
- **Actionable** - Clear action to take
- **Verifiable** - Can confirm when done
- **Atomic** - One outcome per step

**Phases are semantic outcomes** ("Discovery", "Validation"), not file names ("Edit file 1").

## Splitting Large Tasks

Split a plan into sequential parts if the total validation scope exceeds the manager's context budget.

### Plan Validation Weight

Compute `plan_weighted_chars` using the estimator formula applied to validation artifacts:

```
plan_weighted_chars = plan_char_count × (1 + 0.03 × (validation_sections - 1) + 0.015 × max(plan_files - 1, 0))
```

Where:
- **plan_char_count** = estimated chars of: plan text + contracts delta + expected worker output annotations + expected QA review report
- **validation_sections** = distinct validation items: number of phases (each generates output to verify) + number of contracts entries (each must be checked) + expected QA checkpoints
- **plan_files** = plan file + contracts file + QA context (typically 2-3 per plan)

**If `plan_weighted_chars` exceeds ~30K, split the plan into letter-suffixed parts.** Each part is independently dispatched to the manager. This replaces the old phase-count and step-count rules — those were structural proxies. Weighted context is the measurement.

**Resource link = absolute trigger.** If the plan output is too large, split immediately regardless of context weight.

### How to Split

Create independent plans with letter-suffixed names. Each plan is self-contained with its own Problem Statement, Phases, and Completion Criteria. **No orchestrator/parent plan.**

```
TASK-<feature>-A-<outcome>.md     (first part)
TASK-<feature>-B-<outcome>.md     (second part)
TASK-<feature>-C-<outcome>.md     (third part)
```

The naming convention carries the sequencing: A before B before C.

Each plan should include:

- Full Problem Statement (assume reader has zero context)
- `**Prerequisite:** TASK-<feature>-A-<outcome>` if it depends on a prior part
- Its own Completion Criteria (not "all parts done")
- References to sibling plans for navigation

### If a Part Is Still Too Large

**Add siblings, don't nest deeper.**

```
Before: TASK-feature-A-discovery.md triggers split
After:  TASK-feature-A1-discovery-scope.md
       TASK-feature-A2-discovery-assess.md
```

## Parser Rejection Rules

### Nested Steps ❌

```markdown
- [ ] Create files
  - [ ] Create auth.py    ← REJECTED: indented checkbox
```

**Fix:** Unnest as flat steps, move to `**Notes:**`, or split into phases.

### Non-Sequential Phases ❌

```markdown
### Phase 1: Discovery
### Phase 3: Implementation   ← REJECTED: skipped 2
```

### Invalid Phase Format ❌

```markdown
### Phase One: Discovery      ← REJECTED: must be integer
### Phase 1 - Discovery       ← REJECTED: must use colon
```

## Validation

**Always run `plan_read(plan_name)` after creating a plan.** Fix errors before proceeding.

Verify:
- [ ] Structure matches template
- [ ] Phase numbers are sequential integers
- [ ] Steps are flat (no nesting)
- [ ] Problem Statement provides context
- [ ] Completion Criteria are measurable

## Cross-Session Continuity

Plans enable task continuity across sessions:

1. **Starting a plan**: Create in `artifacts/plans/pending/`
2. **Resuming**: Read with `plan_read`, check completed steps
3. **Completing**: Archive with `plan_archive` to `artifacts/plans/completed/`

The plan file is the source of truth. Annotations preserve decisions and context.

## Common Mistakes

| Don't | Do Instead |
|-------|------------|
| Indent checkboxes | Flat steps only |
| Skip phase numbers (1→3) | Sequential: 1, 2, 3 |
| `### Phase One:` | `### Phase 1:` |
| Vague steps ("fix auth") | Concrete ("Implement AuthMiddleware in X") |
| Skip problem statement | Always include context |
| Manual checkbox edits | Use `plan_complete_step` |
| Micro-steps ("add import") | Meaningful units |
| Create orchestrator plans | Just use A→B→C naming |
