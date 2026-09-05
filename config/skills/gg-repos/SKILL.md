---
name: gg-repos
description: Use for GitHub collaboration and repository hygiene: remotes, pull requests, code review, protected branches, issues and projects, releases, and environments. Load when maintaining or reviewing a shared GitHub repository via the direct PAT-authenticated gh CLI.
---

# gg-repos

**Purpose:** Guide Git/GitHub collaboration and repository governance for agents and humans operating the direct PAT-authenticated gh CLI; workflow execution mechanics are owned by gg-actions.

## When to use
- Adding, inspecting, and fixing remotes
- Opening and reviewing pull requests
- Configuring branch protection and required checks
- Tracking work with issues and projects
- Drafting and publishing releases
- Managing protected environments

**Do NOT use** for local history work (commits, rebase, worktrees, reflog) — load `gg-core`. **Do NOT use** for token, secret, or credential handling — load `gg-env`. **Do NOT use** for the workflow lifecycle (inspecting/creating/modifying/removing workflow files, running/dispatching, watching, collecting artifacts, cancelling, iterating) — that is owned by `gg-actions`.

## First safe step
Verify the remote identity before acting on it: `git remote -v` and confirm the origin URL matches the intended repository. Never operate on a remote you have not verified (see references/remotes.md).

## Task index
- Manage remotes and their authentication safely -> references/remotes.md
- Open and review a pull request -> references/pr-lifecycle.md
- Protect branches with required checks and reviews -> references/branch-protection.md
- Track and triage work with issues and projects -> references/issues-projects.md
- Draft, attach assets, and publish an immutable release -> references/releases.md
- Configure protected environments and deployment rules -> references/environments.md

## Ownership
This skill owns remotes, pushes, and PR collaboration on shared repositories. Branch creation and local commits on your own working tree are `gg-core`; the full workflow lifecycle (branch + push a workflow change, run/dispatch, watch, view logs, download artifacts, cancel, clean up, iterate) is owned by `gg-actions`. Name those skills as pointers only; do not duplicate their reference files here.

## Unmatched task
Consult the official GitHub documentation: <https://docs.github.com>.
