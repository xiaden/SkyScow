---
description: Resolve a GitHub issue by committing the scoped repair directly onto the branch referenced by the issue — validate the defect against current HEAD, route through the normal SkyScow workflow, push that branch, comment on the issue, and hand off to the independent resolution verifier without closing the issue
argument-hint: "<issue URL or number> [target branch override] [context]"
---

Resolve the GitHub issue below by committing the repair directly onto the branch referenced by the issue:

$ARGUMENTS

## Workspace preflight (early return)

This command mutates the local workspace, so it must run inside a checkout of the repository that owns the issue.

1. Parse the issue reference from the arguments above **before** reading the issue:
   - a full issue URL (`https://github.com/<owner>/<repo>/issues/<n>`) supplies the authoritative `<owner>/<repo>` directly;
   - a bare number means the issue belongs to the workspace's own repository.
2. Resolve the workspace repository:
   - `git rev-parse --show-toplevel` must succeed — the command must run inside a git working tree;
   - read the `origin` remote URL and, when present, the `upstream` remote URL (`git remote get-url origin`, `git remote get-url upstream`).
3. Normalize each remote URL to `<owner>/<repo>` — handling `git@github.com:<owner>/<repo>.git`, `ssh://git@github.com/<owner>/<repo>.git`, and `https://github.com/<owner>/<repo>` with or without a `.git` suffix and with trailing slashes — and compare case-insensitively. A fork clone is a match when `upstream`, not only `origin`, is the issue's repository.

**Early return:** if the workspace is not a git working tree, exposes no GitHub remote, or no remote matches the issue's `<owner>/<repo>`, stop immediately. Report the expected `<owner>/<repo>`, the remotes actually configured in the workspace, and the mismatch, then make no further tool calls — do not read, comment on, or modify the issue, and do not create branches, edit files, commit, or push. Never proceed against a different repository.

## Authoritative work item

Treat the GitHub issue as the authoritative work item. Read the full issue body and **all** comments before doing anything else, including any prior GPT QA Resolution Review comments. Validate the reported defect against current repository state rather than blindly implementing the proposed correction.

If current HEAD shows the issue is already resolved, obsolete, incorrectly scoped, or substantially superseded, do not manufacture a change. Report the evidence on the issue instead.

## Repository resolution

Derive the authoritative `owner/repo` from the issue URL. Every `gh` command that operates on the repository — `gh issue view`, `gh issue comment`, `gh api` — MUST pass an explicit `--repo <owner>/<repo>`.

Never rely on the ambient `gh` default repository. In a fork clone that has an `upstream` remote and no `remote.<name>.gh-resolved` entry, bare `gh` resolves to the parent repository rather than `origin`, so an unqualified command silently targets the wrong repository.

## Target branch

Determine the authoritative target branch/ref from the issue metadata and repository context. This is the branch the commit lands on.

- If the issue was filed against `main`, commit on `main`.
- If the issue was filed against a feature/development branch, commit on that branch.
- Do not silently retarget the work to the repository default branch, and do not create a substitute branch.
- Fetch and check out the authoritative target branch so the commit is based on its current HEAD.

If the referenced branch cannot be resolved, stop and report; never commit on a different branch.

## Execution

Route the work through the normal SkyScow workflow.

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

If investigation exposes a separate defect that is not required to resolve this issue, leave it out of this commit.

## Validation

Add or update regression coverage that exercises the actual failing journey or boundary where practical.

Run:

- the strongest targeted tests for the repaired behavior;
- relevant static/type/lint checks;
- the repository's applicable broader test/quality gates.

Passing tests alone are not sufficient. Verify through code-path analysis that the original issue's supported failure path is actually removed.

## Git / commit

Before performing or initiating any Git/GitHub operation, load every applicable generic `gg-*` skill; do not proceed from memory. Then:

- Check out the authoritative target branch named by the issue and fetch it first, so the commit is based on its current HEAD.
- Commit the scoped repair on that same branch in the issue's repository. Keep commits reviewable and organized by remediation scope. Multiple commits are fine when they represent coherent implementation/test boundaries; do not create artificial commit fragmentation.
- Push the referenced branch itself, with an explicit remote and branch (`git push origin <target-branch>`). Never push a different branch and never force-push.
- Do not open a pull request. This command resolves the issue by landing the commit directly on the branch referenced by the issue.

The commit message(s) should:

- reference the issue;
- explain the root cause;
- summarize the correction;
- identify important affected boundaries;
- describe validation performed;
- call out any residual scope or known limitation.

Do **NOT** use GitHub automatic-closing keywords such as `Fixes`, `Closes`, or `Resolves`. Use neutral references such as `Refs #123`.

The GPT QA Resolution Verifier owns final issue closure after independently verifying the repair.

## Issue handoff

After the commit is pushed, add a concise comment to the original issue (`gh issue comment --repo <owner>/<repo> <issue>`) containing:

- commit SHA(s);
- the branch the commit landed on;
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
- the commit is pushed to the branch referenced by the issue;
- the issue contains a remediation comment referencing that commit;
- the issue remains open for independent GPT QA resolution verification.
