# QA-DocsAnalyzer

Dispatch QA-DocsAnalyzer to assess documentation coverage and accuracy for changed code.

WHEN documentation analysis applies and the observable trigger are owned by
`/home/opencode/.config/opencode/instructions/qa-applicability.md`; this reference
owns only HOW documentation analysis is performed.

## When to Dispatch

**Dispatch when:**
- QA-Reviewer delegates documentation analysis as part of the full review
- You need standalone documentation assessment for a module or feature
- After implementation to verify docs before review

**Do NOT dispatch when:**
- You need a full review — use `qa-reviewer` instead (it spawns this agent)
- You need docs generated — use `qa-docs-generator` instead (spawned by this agent)
- You need test analysis — use `qa-test-analyzer` instead

## Dispatch Template

```
Analyze documentation coverage and accuracy for changed files.

Context files to read:
- [PLAN_PATH]  — the plan that produced these changes
- [list changed files covered by the plan]
- [existing docs or READMEs for context]

scope: "[files/modules to analyze]"
plan: "[plan identifier]"

Identify missing docstrings, stale docs, and doc/code drift. For MINOR_DISPATCH or MAJOR_DISPATCH tiers you MUST spawn qa-docs-generator, then re-verify its output; for PASS, MINOR_PASS, and MAJOR_RAISE, report without dispatching. A dispatch-tier result is incomplete until the generator has run.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `scope` | Files/modules to analyze | `src/api/routes/, docs/api/` |
| `plan` | Plan identifier for context | `TASK-api-A-endpoints` |

## Expected Output

| Tier | Meaning | Action |
|------|---------|--------|
| `PASS` | Documentation complete and accurate | No action needed |
| `MINOR_PASS` | Minor gaps, logged but not blocking | Log findings, no dispatch |
| `MINOR_DISPATCH` | Gaps need doc generation | Spawn QA-DocsGenerator with gap list |
| `MAJOR_DISPATCH` | Significant gaps, multiple files undocumented | Spawn QA-DocsGenerator with prioritized gaps |
| `MAJOR_RAISE` | Critical gaps — public API undocumented | Escalate to caller |

Output includes:
- Coverage assessment per file/module
- Missing docstrings (specific functions/classes)
- Stale docs (docs for removed/renamed APIs)
- Doc/code drift (docs say one thing, code does another)

## Routing by Tier

| Tier | Action |
|------|--------|
| `PASS` or `MINOR_PASS` | Return to caller — no doc generation needed |
| `MINOR_DISPATCH` or `MAJOR_DISPATCH` | Spawn `qa-docs-generator` with gap list |
| `MAJOR_RAISE` | Escalate — critical gaps require caller intervention |
