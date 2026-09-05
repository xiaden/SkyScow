---
name: gg-router
description: Use when deciding which Git/GitHub skill applies to an unclassified task. A short front door that routes a Git/GitHub or repository-conventions question to the correct sibling skill (local history, collaboration, workflows, environment/credentials, Docker artifacts, Pages docs, or repo-local conventions) without guessing when nothing matches.
---

# gg-router

**Purpose:** Route an unclassified Git/GitHub or repository-conventions task to the sibling skill that owns it. This is a bounded front door only — it carries no content of its own and no references. The sibling skills own the how-to.

## When to use
- You have a Git/GitHub or repository-conventions task and are unsure which skill applies
- You want a quick map of the family before loading a specific skill

**Do NOT use** when you already know the applicable skill — load it directly.

## Route by task

| If the task is about... | Load |
|---|---|
| Local history: commits, branches, merge/rebase, worktrees, reflog, signing, hooks, config | `gg-core` |
| Collaboration and repository hygiene: remotes, PRs, reviews, issues, protected branches, releases, environments | `gg-repos` |
| Writing, reviewing, dispatching, or securing GitHub Actions workflows | `gg-actions` |
| Tokens, secrets, credentials, permissions, OIDC, visibility/plan, loader/sync behavior, dated fact lookup | `gg-env` |
| Building, publishing, attesting, or verifying versioned Docker images with provenance/SBOM/GHCR | `gg-artifacts` |
| Building and publishing hosted docs through GitHub Pages, or custom domains | `gg-docs` |
| THIS repository's current environment constraints and team conventions (repo-local) | `ggt-conventions` |

## Routing order

1. **Repo-local?** The task concerns this workspace's own environment state or team conventions → `ggt-conventions` (constraints recorded there). Generic Git/GitHub guidance stays in the `gg-*` family.
2. **Otherwise** match the task to exactly one row in the table above and load that skill. If the task spans multiple rows, load the skill owning the primary action.

## Provisional status
This router is provisional (DD open question Q5): it is retained only if the Phase-5 (plan F) trigger tests show a measurable routing benefit over loading the sibling skills directly. If it does not, its unmatched-task pointer folds into `gg-env` and this router is removed. Do not treat the router as a permanent architectural requirement.

## Unmatched task
If the task does not match any sibling skill, **do not guess**. Consult the official GitHub and Git documentation directly: <https://docs.github.com> and <https://git-scm.com/docs>. If the task is a genuinely new recurring Git/GitHub need, note it for the family maintainers — do not improvise a home for it here.
