# RnD-Estimator

Dispatch RnD-Estimator to size implementation effort.

## When to Dispatch

**Dispatch when:**
- You need effort sizing for a feature or plan before committing
- You're comparing implementation approaches and need relative effort
- You need to validate scope before planning
- You're evaluating a technology choice and need ballpark effort

**Do NOT dispatch when:**
- The scope is trivial (single-file change, typo fix)
- You need a full design document — use `rnd-manager` or `rnd-dd-author` instead
- You need implementation analysis — use `rnd-architect` instead
- You need creative ideation — use `rnd-ideator` instead

## Dispatch Template

```
Estimate effort for [WORK ITEM].

Context files to read:
- [design doc, plan, or requirements]
- [relevant code for context]

work item: "[description of what needs to be built]"
scope: "[files/modules/layers affected]"

Return effort estimate with file count breakdown. Read-only — estimation only.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[WORK ITEM]` | What needs to be sized | "Add OAuth2 authentication flow" |
| `work item` | Description of what needs to be built | "Add OAuth2 login, token refresh, and session management to the auth service." |
| `scope` | Files/modules/layers affected | "src/auth/service.ts, src/auth/middleware.ts, src/auth/types.ts, src/auth/__tests__/" |

## Expected Output

The Estimator sizes tasks by weighted context scope, not file count.

**Cognitive weight formula:**
```
cognitive_weight = 1 + 0.03 × (sections - 1) + 0.015 × max(files - 1, 0)
weighted_chars = char_count × cognitive_weight
```

Where **sections** = distinct edit locations (functions, methods, blocks) and **files** = files touched.

| Size    | Weighted Chars | ~Tokens | Typical Scope                | Pipeline                         |
|---------|---------------|---------|------------------------------|----------------------------------|
| TRIVIAL | < 8K          | < 2K    | Single function, config      | Edit directly                    |
| SMALL   | 8K-32K        | 2K-8K   | Few functions, 1-3 files     | Edit directly                    |
| MEDIUM  | 32K-80K       | 8K-20K  | Multiple files, one layer    | Plan needed — can't hold in one pass |
| LARGE   | 80K-320K      | 20K-80K | Cross-cutting, multi-layer   | DD + plan                        |
| EPIC    | 320K+         | 80K+    | Multi-workflow, schema change| DD + decompose                   |

**DD threshold:** LARGE or above, OR architecturally novel, OR incomplete/ambiguous requirements.

Output includes:
- Effort tier with rationale
- Estimated sections, files, char count, and weighted chars
- Pipeline recommendation (plan_needed, dd_needed)
- Key risk factors
- Confidence level

This agent is **read-only** — it returns estimates, does not execute or implement.
