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
Analyze documentation coverage and accuracy for the changed files.

Context files to read:
- [DAG_PATH]
- [list changed files covered by the subject nodes]
- [existing docs or READMEs for context]

scope: "[files/modules to analyze]"
slug: "[change dag slug]"
subjectNodeIds: ["I001"]
changedFiles: ["..."]

Inspect the current surface and report concrete documentation gaps. If a repairable gap exists, dispatch
`qa-docs-generator` once with only its `description`, `files`, and `reason`. The Generator owns documentation
edits and verification. Return exactly `PASS`, `GENERATED`, or `FAIL`; `GENERATED` requires changed files,
and `FAIL` requires a concise reason. Do not re-analyze docs, inspect durable Generator records, or
reconstruct Generator history.

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `scope` | Files/modules to analyze | `src/api/routes/, docs/api/` |
| `slug` | Change DAG identity for context | `api-change` |
| `changedFiles` | Changed surface | `["src/api/routes.py"]` |

## Expected Output

DD lifecycle inputs use only `Draft`, `Approved`, `Completed`, `Superseded`, or `Rejected`; an `Approved` pending prerequisite is valid only with disposition, responsible owner, and transition condition.

| Status | Meaning | Action |
|--------|---------|--------|
| `PASS` | No actionable documentation gap; no generator needed | Return to caller |
| `GENERATED` | Generator successfully repaired a concrete gap | Return changed files |
| `FAIL` | Analysis or generation could not complete successfully | Return reason/failure kind |

Each gap contains only `description`, `files`, and `reason`. `GENERATED` requires non-empty changed files;
`FAIL` requires a concise reason.
