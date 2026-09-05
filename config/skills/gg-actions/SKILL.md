---
name: gg-actions
description: Use when writing, reviewing, dispatching, securing, or operating GitHub Actions workflows via the direct PAT-authenticated `gh` CLI: workflow syntax, events and triggers, least-privilege permissions, secrets, action pinning, cache, artifacts, concurrency, runners, and OIDC. Load before authoring or reviewing a workflow.
---

# gg-actions

**Purpose:** Guide secure GitHub Actions workflow authoring and operation — how to write, trigger, secure, and operate workflows through the terminal with `gh`, including the full inspect/branch/push/run/watch/logs/artifact/cancel/cleanup/iterate lifecycle.

## When to use
- Writing or revising a workflow file (`.github/workflows/*.yml`)
- Choosing workflow triggers and reviewing over-broad or privileged triggers
- Setting least-privilege permissions and minimal `GITHUB_TOKEN` scopes
- Handling Actions and environment secrets safely
- Pinning and vetting third-party actions
- Tuning cache, artifacts, and concurrency
- Choosing between hosted and self-hosted runners
- Enabling cloud authentication through OpenID Connect (OIDC)
- Dispatching a workflow manually (`workflow_dispatch`) with inputs and environment protection

**Do NOT use** for local history work — load `gg-core`. **Do NOT use** for collaboration, PRs, releases, or branch protection — load `gg-repos`. **Do NOT use** for credentials, secrets, permissions, or environment fact lookup — load `gg-env`.

## First safe step
Review what the workflow can do before writing it: inspect its triggers, its `permissions` block, and every third-party action it references. Default to the least privilege that still lets the workflow complete. Never put a token, secret, or private key in plaintext.

## Task index
- Author workflow syntax and structure -> references/workflow-authoring.md
- Choose events and triggers, and dispatch workflows manually -> references/events-and-dispatch.md
- Set least-privilege permissions and minimal token scopes -> references/workflow-permissions.md
- Store and use Actions and environment secrets -> references/workflow-secrets.md
- Pin and vet third-party actions -> references/action-pinning.md
- Control cache, artifacts, and concurrency -> references/workflow-operations.md
- Choose hosted or self-hosted runners -> references/runners.md
- Enable cloud auth with OpenID Connect -> references/oidc-trust.md
- Run and drive the full workflow lifecycle (branch + push a change, dispatch/run, watch, view status and logs, download artifacts, cancel, clean up, iterate) -> references/workflow-lifecycle.md
- Look up shared visibility, credential, and artifact-attestation facts -> references/credentials-and-visibility.md

## Ownership
This skill owns the workflow authoring and lifecycle capability: inspecting/creating/modifying/removing workflow files, branching and pushing the change, dispatching or running via `gh` (`gh workflow run`/`repository_dispatch`), watching runs, viewing status and logs, downloading artifacts, cancelling failed/stale runs, cleaning up temporary branches/workflows/runs where supported, and iterating code from collected results until verification passes. Local branch/commit state is `gg-core`; push/remotes/PR collaboration is `gg-repos`; credentials/PAT hygiene is `gg-env`; hosted Docker/artifacts is `gg-artifacts`. Name those skills as pointers only; do not duplicate their reference files here.

## Unmatched task
Consult the official GitHub Actions documentation: <https://docs.github.com/actions>.
