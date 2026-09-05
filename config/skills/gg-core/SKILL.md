---
name: gg-core
description: Use for local Git work: commits and branches, merge and rebase, worktrees, reflog recovery, commit signing, and local hooks. Load when performing local operations on your own working tree and history.
---

# gg-core

**Purpose:** Make safe, reviewable local Git history and recover cleanly from mistakes, without touching shared remotes.

## When to use
- Committing changes and structuring isolated branches
- Choosing merge vs. rebase and resolving conflicts
- Using worktrees to work on multiple branches at once
- Recovering commits lost to reset, bad merges, or checkout
- Signing and verifying commits
- Installing and troubleshooting local hooks

**Do NOT use** for shared-repository collaboration (remotes, pushes, pull requests, releases, protected branches) — load `gg-repos`. **Do NOT use** for token, secret, or credential handling — load `gg-env`. **Do NOT use** for the workflow lifecycle (inspecting/creating/modifying/removing workflow files, running/dispatching, watching, collecting artifacts, cancelling, iterating) — that is owned by `gg-actions`.

## First safe step
Inspect state before any history-changing operation: `git status`, `git log --oneline --decorate`, `git branch`. Never run a destructive command without knowing the current state (the reflog records every HEAD movement, so it is your safety net).

## Task index
- Make reviewable commits and create isolated branches -> references/commit-branch.md
- Integrate work with merge or rebase, and resolve conflicts -> references/merge-rebase.md
- Work on multiple branches concurrently -> references/worktrees.md
- Recover lost commits or undo a bad history change -> references/recover-reflog.md
- Sign and verify commits -> references/signing.md
- Configure and troubleshoot local hooks -> references/hooks.md

## Ownership
This skill owns local Git state: branch creation and local commits on your own working tree. Pushing a branch to a remote, opening PRs, and collaborating are owned by `gg-repos`; the full workflow lifecycle (branch + push a workflow change, run/dispatch, watch, view logs, download artifacts, cancel, clean up, iterate) is owned by `gg-actions`. Name those skills as pointers only; do not duplicate their reference files here.

## Unmatched task
Consult the official Git documentation: <https://git-scm.com/docs>.
