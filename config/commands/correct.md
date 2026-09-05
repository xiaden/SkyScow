---
description: Correct an issue through risk-based investigation, planning, implementation, QA review, and verified commit
---

Correct the issue below without regressing behavior. Treat the complete request as authoritative: preserve the original issue details, derive a requirement ledger from them, and verify the final implementation against every requirement and expected behavior.

$ARGUMENTS

## Phase 1: Triage and evidence

Before changing code:

1. Parse the issue fields (`severity`, `files`, `problem_description`, `recommended_action`, and `expected_behavior`) when present. If fields are absent, derive the same information from the request without inventing requirements.
2. Review relevant ADRs/ASRs, durable logs, git history for affected files, applicable skills/instructions, definitions and callers, existing tests, and the complete state lifecycle involved.
3. Verify that the listed files own the behavior. Trace related caches, persistence, startup/reload, application facades, public contracts, and error handling rather than treating the file list or recommended action as complete architectural guidance.
4. Classify the change as local/low-risk, standard, or high-risk. High-risk includes authentication or authorization, credentials or sessions, persistence deletion/migration, cache invalidation, startup/recovery, concurrency, cross-layer changes, public contracts, or security-sensitive data.

## Phase 2: Route and plan

- For a genuinely local, low-risk correction with no contract or lifecycle impact, proceed with a bounded implementation.
- For a correction spanning multiple layers, modules, state stores, or lifecycle boundaries, route through `Exec-Planner` and then `Exec-Manager`. The planner must create or amend a verifiable implementation plan; the manager must execute it phase by phase.
- For high-risk work, require the plan to include security implications, failure/partial-operation behavior, concurrency considerations, rollback or recovery semantics, and restart/reload behavior where applicable.
- If investigation reveals an architectural mismatch, unclear ownership, missing contract, migration requirement, contradictory ADR/ASR, or an unresolved requirement that cannot be safely implemented locally, stop and escalate to `RnD-Manager` or request user clarification. Do not silently choose an architectural shortcut.

The plan or bounded implementation must convert `expected_behavior` into executable invariants. Include normal, negative, persistence, restart/recovery, and relevant concurrency or partial-failure tests. For example, a session-revocation fix must verify validity before reset, immediate invalidity after reset, absence from persisted storage, invalidity after restart, rejection of the old password, and successful login with the new password.

## Phase 3: Implement and verify

Implement only the approved scope. Re-read files immediately before editing and adapt around concurrent changes. Run the project virtual environment's targeted tests and linting, then broader relevant verification. Review the complete diff for unintended changes and confirm each requirement has evidence.

## Phase 4: Mandatory QA gate

Have `QA-Reviewer` perform a full review after all implementation phases. Provide the original request, requirement ledger, risk classification, plan, changed-file set, invariants, test results, and diff context. For security-sensitive, persistence, cache, lifecycle, or cross-layer changes, require the applicable security review as well as test and documentation analysis.

- `MINOR` findings: route to the permitted fixer, then rerun the full QA review.
- Planning gaps, requirement drift, architectural issues, critical/security findings, or unresolved partial-failure behavior: stop, amend or escalate the plan; do not paper over them with a local patch.
- Do not report completion until QA explicitly passes, all required checks pass, and no high-severity findings remain.

## Concurrent worktree and commit rules

This command runs concurrently with other agents in the same worktree; unrelated file changes are expected. Preserve them and adapt your work around them where possible.

Do not assume old file contents or overwrite concurrent fleet changes. Never use git reset, git checkout, restore, or other destructive repository-state commands to resolve concurrent edits. Re-read changed files before applying edits and preserve concurrent work.

When finished, stage every file you modified while resolving this issue, including files modified for QA corrections, and commit them. Stage the complete current changes for those files; do not attempt to separate or selectively stage individual hunks because other fleet agents may also have modified the same files. Do not stage unrelated files that you did not modify. If changes to a file you modified have already been committed by another agent, do not attempt to undo, recover, or duplicate them; simply commit whatever changes from your touched-file set remain uncommitted.

Do not use repository-wide staging such as `git add .`, `git add -A`, or `git commit -a`. If the required QA, verification, or escalation gate is not satisfied, do not commit; report the blocker instead.

Use the venv (if one exists) to run testing/linting.
