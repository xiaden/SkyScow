# Subagent Dispatch Protocol

How to construct and dispatch Exec-Planner subagent calls that produce correct, drift-free plans.

---

## Prompt Structure

Every Exec-Planner subagent call must include these sections in this order:

```
1. TASK          — What to plan (part scope from README)
2. DESIGN REF    — Where to find full context (design doc path)
3. CONTRACTS     — Full CONTRACTS.md content
4. OUTPUT        — Plan file path and naming
5. CONSTRAINTS   — Anything the subagent must NOT do
```

---

## Prompt Template

```
Create an implementation plan for:

## Task
{Part title}: {3-5 sentence scope from README}

## Design Document
Read the full design context from: `artifacts/designs/pending/DD-{feature}.md`
Focus on sections relevant to this part.

## Contracts from Prior Plans
{Paste full CONTRACTS.md content here — not a file reference, the actual content.
If this is the first plan, paste the initialized ledger with just architectural rules.}

## Output
Create the plan at: `artifacts/plans/pending/TASK-{feature}-{letter}-{descriptor}.md`
Follow the plan format in task-plans.instructions.md.

## Constraints
- Workflow functions take `db: Database`, never services — check CONTRACTS for confirmed patterns
- Every plan must include the full verification loop: type check, lint, test execution (with coverage targets), and build verification per ECC standards. A "lint verification" step alone is insufficient
- Reference concrete method signatures from CONTRACTS when calling upstream APIs
- Do NOT create methods that duplicate what CONTRACTS already defines
- If you need a method that doesn't exist in CONTRACTS or the codebase, create it in your plan and note it clearly for the ledger
```

---

## Critical Rules

### Always inline the ledger content

The subagent cannot read files by path in its prompt. Paste the full CONTRACTS.md text. This is the single most important context injection.

### Never ask the subagent to "research the architecture"

The subagent has tools and will research automatically. Telling it to "research" wastes prompt tokens. Instead, give it concrete starting points:

```
# ❌ Bad
Research the existing patterns for persistence operations.

# ✅ Good
Follow the pattern in `src/persistence/constructor/builder.py`.
```

### Include scope boundaries

Tell the subagent what is NOT in scope to prevent over-planning:

```
# ✅ Good
Out of scope for this part:
- Genre playlist type (deferred to v1.5)
- Frontend UI (covered by Plan G)
- Plugin-side scheduling (covered by Plan C)
```

### One part per dispatch

Never combine "Plan parts B and D since they're in the same round." Each subagent call produces one plan file. Combining causes:

- Bloated context (two parts' worth of research)
- Interleaved steps from different domains
- Plans that are too large for plan_read

---

## After Receiving Subagent Output

1. **Save the plan file** — The subagent may return the plan inline rather than saving it. Always verify the file exists; create it if needed.
2. **Run `plan_read`** — Non-negotiable. If it fails, the plan has structural issues.
3. **Quick-scan for violations:**
   - Does any step pass a service to a workflow?
   - Does any step reference a method not in CONTRACTS or the existing codebase?
   - Are full verification loop steps present (type check + lint + test + coverage + build)?
   - Are quality gate steps present (code review, security review for auth/data/I/O)?
   - Are all steps flat (no nested checkboxes)?
4. **Update CONTRACTS.md** — Extract new methods, APIs, DTOs, and decisions.

---

## Common Subagent Mistakes and Fixes

 | Mistake | Cause | Fix |
 | --- | --- | --- |
 | Plan references method not yet created | Planned out of dependency order | Either: add method creation to this plan, or re-order execution |
 | Missing verification steps | Subagent omitted boilerplate | Add full ECC verification loop (type check → lint → test → coverage → build) as final steps per phase |
 | Step count > 12 | Part scope too broad | Split into two plans: `{letter}` and `{letter}2` |
 | TypedDict defined in wrong layer | Subagent put DTO in workflow file | Move to `src/helpers/dto/` per architecture rules |
