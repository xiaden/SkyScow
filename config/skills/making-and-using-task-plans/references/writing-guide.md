# Task Plan Writing Guide

**Purpose:** Produce task plan files that maintain context across sessions — so a fresh session can read the plan and understand what's been done, what's next, and why.

---

## Step Annotations

Annotations preserve context for future sessions — decisions made, risks identified, blockers hit.

```markdown
- [x] Implement auth middleware
  **Notes:** Used JWT with HS256, stored in httpOnly cookie
  **Warning:** Rate limiting not yet implemented
```

### Annotation Markers

- `**Notes:**` — Additional context, decisions made during implementation
- `**Warning:**` — Risks, gotchas, things to watch for in future steps
- `**Blocked:**` — Why this step couldn't be completed (external dependency, missing info)
- `**Deviation:**` — How implementation differed from the plan

---

## Best Practices

### Problem Statement

Include:
- **What** needs to be done
- **Why** it matters (business/technical value)
- **Context** a fresh session needs (prior decisions, constraints)
- **Scope** boundaries (what's in, what's out)

### Phases

- Group related steps into semantic phases
- Phase names should describe **outcomes**, not actions ("Core Auth Logic", not "Write Auth Code")
- Keep phases small enough to complete in one session when possible
- Order phases by dependency — what must come first?

### Steps

- Each step should be **atomic and verifiable**
- Start with a verb (Create, Update, Delete, Verify, etc.)
- Include file paths or module names when relevant
- Mark steps complete with `- [x]` as you go
- Add annotations for decisions, warnings, or blockers

### Completion Criteria

- List **measurable outcomes**, not aspirations
- Include verification steps (lint, tests, manual checks)
- Specify what "done" looks like unambiguously

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Non-integer phase numbers (`### Phase 1.5:`) | Use integers only (`### Phase 1:`, `### Phase 2:`) |
| Nested steps (`  - [ ] substep`) | Flatten to top-level or use annotations |
| Missing problem statement | Always include context for fresh sessions |
| Vague steps ("Fix the thing") | Be specific: file paths, module names, expected outcomes |
| No completion criteria | List measurable outcomes and verification steps |

---

## Cross-Session Continuity

When resuming work on a plan:

1. Read the plan with `plan_read`
2. Check which steps are complete (`- [x]`)
3. Read annotations for context on decisions made
4. Continue from the first incomplete step
5. Update annotations as you make new decisions

The plan file is the source of truth. Annotations preserve the "why" behind decisions — they're what makes a stale plan recoverable months later.
