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

## Phase 2: Route and author

- For a genuinely local, low-risk correction with no contract or lifecycle impact, proceed with a bounded implementation through the **Direct / Bounded Edit Route** below.
- For a correction spanning multiple layers, modules, state stores, or lifecycle boundaries, route through `Change-DAG-Author` and then `Change-DAG-Runner`. The author must create or amend a verifiable Change DAG; the runner must execute it to completion through the **Change DAG Route** below.
- For high-risk work, require the Change DAG's requirements to include security implications, failure/partial-operation behavior, concurrency considerations, rollback or recovery semantics, and restart/reload behavior where applicable.
- If investigation reveals an architectural mismatch, unclear ownership, missing contract, migration requirement, contradictory ADR/ASR, or an unresolved requirement that cannot be safely implemented locally, stop and escalate to `RnD-Manager` or request user clarification. Do not silently choose an architectural shortcut.

The Change DAG (or bounded implementation) must convert `expected_behavior` into executable invariants. Include normal, negative, persistence, restart/recovery, and relevant concurrency or partial-failure tests. For example, a session-revocation fix must verify validity before reset, immediate invalidity after reset, absence from persisted storage, invalidity after restart, rejection of the old password, and successful login with the new password.

## Phase 3: Implement and verify

Implement only the approved scope. Re-read files immediately before editing and adapt around concurrent changes. Use the route-specific staging and checkpoint rules in **Concurrent worktree and commit rules**; never manually stage or commit Change DAG implementation work. Run the project virtual environment's targeted tests and linting, then broader relevant verification. Review the complete diff for unintended changes and confirm each requirement has evidence.

## Phase 4: Mandatory QA gate

Have `QA-Reviewer` perform a full review after all implementation phases. For the Change DAG Route, this means **after the executor's successful-root checkpoint**. Provide the original request, requirement ledger, risk classification, Change DAG, changed-file set, invariants, test results, and diff context. The full QA gate is mandatory for every meaningful implementation change, and independent correctness review is always required. Invoke the security review, test analysis, and documentation analysis lenses only when their canonical triggers in `/home/opencode/.config/opencode/instructions/qa-applicability.md` are met; do not restate those triggers here.

- `MINOR` findings: route to a bounded raw edit, then rerun the full QA review. If that edit follows a Change DAG checkpoint, use the **Post-Checkpoint QA Corrections** rules below.
- Planning gaps, requirement drift, architectural issues, critical/security findings, or unresolved partial-failure behavior: stop; author a remediation Change DAG (or a bounded correction) through `Change-DAG-Author`; never reopen a completed DAG, and do not paper over them with a local patch.
- QA is independent of Change DAG archival. Do not make QA a DAG archive gate.
- Do not report completion until QA explicitly passes, all required checks pass, and no high-severity findings remain.

## Concurrent worktree and commit rules

This command runs concurrently with other agents in the same worktree; unrelated file changes are expected. Preserve them and adapt your work around them where possible.

Do not assume old file contents or overwrite concurrent fleet changes. Never use git reset, git checkout, restore, or other destructive repository-state commands to resolve concurrent edits. Re-read changed files before applying edits and preserve concurrent work.

### Direct / Bounded Edit Route

- Preserve the conservative commit behavior for direct edits.
- QA and all required verification must pass before committing.
- After QA PASS, stage only files actually modified by this correction, including files modified for bounded QA corrections. Do not stage unrelated files or use repository-wide staging such as `git add .`, `git add -A`, or `git commit -a`.
- Stage the complete current changes for those correction files rather than attempting to split individual hunks. If changes to a correction file have already been committed by another agent, do not undo, recover, or duplicate them; commit only the remaining uncommitted changes from the correction's touched-file set.
- Preserve unrelated concurrent work.

### Change DAG Route

- Do not manually stage or commit the DAG's implementation work.
- `Change-DAG-Runner`/the deterministic executor owns the automatic successful-root checkpoint after `dag_start` captures the inherited starting worktree state and the DAG root becomes satisfied.
- The executor-owned checkpoint intentionally runs `git add -A` and is exempt from this command's normal selective-staging rule. It represents the actual repository state at DAG completion and may contain inherited dirty worktree state by design.
- Do not stash, split, reconstruct, selectively stage, reset, or otherwise try to isolate DAG-originated hunks before the checkpoint. Do not amend or rewrite the executor checkpoint merely to make it correspond only to DAG-authored files.
- Use the inherited starting-worktree evidence and `WORK_LOG` as provenance for distinguishing pre-existing state from DAG execution. The checkpoint is not publication and is not the final QA gate.
- Run mandatory independent QA after the checkpoint. DAG archival remains independent of QA.

### Post-Checkpoint QA Corrections

- If QA finds a small bounded defect and a raw correction is made after the DAG checkpoint, rerun QA as already required. After QA PASS, commit only those post-checkpoint correction files using the Direct / Bounded Edit Route's normal selective staging.
- If QA exposes a substantial DAG gap and a remediation Change DAG is required, that new DAG owns its own automatic successful-root checkpoint. Do not reopen the completed DAG.
- If QA makes no post-checkpoint mutations, the executor checkpoint is already the implementation commit; do not create a redundant second commit.

Use the venv (if one exists) to run testing/linting.
