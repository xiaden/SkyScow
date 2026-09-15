---
description: Resolve a GitHub issue through a scoped implementation PR — validate the defect against current HEAD, route through the normal HolyCode workflow, and hand off to the independent resolution verifier without closing the issue
argument-hint: "<issue URL or number> [target branch override] [context]"
---

Resolve the GitHub issue below through a scoped implementation PR:

$ARGUMENTS

## Authoritative work item

Treat the GitHub issue as the authoritative work item. Read the full issue body and **all** comments before doing anything else, including any prior GPT QA Resolution Review comments. Validate the reported defect against current repository state rather than blindly implementing the proposed correction.

If current HEAD shows the issue is already resolved, obsolete, incorrectly scoped, or substantially superseded, do not manufacture a change. Report the evidence on the issue instead.

## Target branch

Determine the authoritative target branch/ref from the issue metadata and repository context.

- If the issue was filed against `main`, the PR targets `main`.
- If the issue was filed against a feature/development branch, the PR targets that branch.
- Do not silently retarget the work to the repository default branch.
- Base the implementation branch from the current HEAD of the authoritative target branch.

## Execution

Route the work through the normal HolyCode workflow.

Nyx is the coordinator, not the replacement for downstream roles:

- use RnD when design/decision work is required;
- allow the appropriate planning/execution/review agents to perform their normal responsibilities;
- do not bypass established workspace instructions, architecture constraints, or agent routing merely because the issue appears small.

Before implementation, establish:

- the actual root cause;
- the user/system journey that reaches it;
- the invariant or contract that should hold;
- the complete remediation scope;
- any existing tests that claim to cover the behavior.

## Scope discipline

Repair the issue completely, but keep the work scoped to its remediation boundary.

Follow affected callers, callees, interfaces, persistence/external boundaries, lifecycle/state behavior, and tests as necessary to restore the intended invariant.

Do not include unrelated refactors, formatting churn, dependency changes, architecture cleanup, or opportunistic fixes merely because they are nearby.

If investigation exposes a separate defect that is not required to resolve this issue, leave it outside this PR.

## Validation

Add or update regression coverage that exercises the actual failing journey or boundary where practical.

Run:

- the strongest targeted tests for the repaired behavior;
- relevant static/type/lint checks;
- the repository's applicable broader test/quality gates.

Passing tests alone are not sufficient. Verify through code-path analysis that the original issue's supported failure path is actually removed.

## Git / PR

Before performing or initiating any Git/GitHub operation, load every applicable generic `gg-*` skill; do not proceed from memory. Then:

- Create a scoped implementation branch from the authoritative target branch.
- Keep commits reviewable and organized by remediation scope. Multiple commits are fine when they represent coherent implementation/test boundaries; do not create artificial commit fragmentation.
- Push the branch and open a PR back into the authoritative target branch.

The PR should:

- reference the issue;
- explain the root cause;
- summarize the correction;
- identify important affected boundaries;
- describe validation performed;
- call out any residual scope or known limitation.

Do **NOT** use GitHub automatic-closing keywords such as `Fixes`, `Closes`, or `Resolves`. Use neutral references such as `Refs #123`.

The GPT QA Resolution Verifier owns final issue closure after independently verifying the repair.

## Issue handoff

After the PR is created, add a concise comment to the original issue containing:

- PR link/number;
- implementation branch;
- commit SHA(s), when useful;
- root cause repaired;
- summary of the correction;
- validation performed;
- any residual scope.

Do not close the issue.

This issue comment is the handoff signal to the independent resolution verifier, so make it explicit that remediation is ready for verification.

## Completion condition

The task is complete when:

- the defect has been investigated against current HEAD;
- the scoped repair and regression coverage are implemented;
- applicable validation passes, or any unavoidable failures are clearly documented;
- a PR exists against the issue's authoritative target branch;
- the issue contains a remediation comment referencing that PR;
- the issue remains open for independent GPT QA resolution verification.
