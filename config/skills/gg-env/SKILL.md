---
name: gg-env
description: Use for Git/GitHub credentials, tokens, secrets, permissions, OIDC, visibility or plan branching, and environment hazards.
---

# gg-env

**Purpose:** Canonical guidance for credentials, secrets, permissions, and the Git/GitHub loading environment, plus the dated fact-stamp registry. Nothing here is a volatile fact — time-sensitive claims live in the dated registry or in a fact-stamped reference.

## When to use
- Handling tokens, secrets, or credentials for Git or GitHub
- Deciding how to store credentials safely and applying least privilege
- Understanding OIDC trust and token issuance
- Determining when a GitHub feature depends on repository visibility or a plan
- Understanding how OpenCode discovers and loads skills across repository and global roots
- Looking up a dated, official source for a volatile Git/GitHub claim

**Do NOT use** for local history work — load `gg-core`. **Do NOT use** for collaboration, PRs, releases, or branch protection — load `gg-repos`.

## First safe step
Never use or encourage plaintext credential storage. Check the current state before acting: `git config --get credential.helper` and whether a plaintext `~/.git-credentials` exists. If either is present, treat it as a hazard to remediate, never as setup guidance.

## Task index
- Credential storage, plaintext hazards, and safe alternatives -> references/security-and-credentials.md
- Loader and sync discovery hazards (dual root discovery, same-name loading) -> references/loader-and-sync-hazards.md
- OIDC trust and token issuance -> references/oidc-and-trust.md
- Credentials and visibility shared table (plan branches, credential rules, Docker/Pages facts) -> references/credentials-and-visibility.md
- Dated fact-stamp registry (owner/cadence per official source) -> references/fact-registry.txt

## Direct `gh` CLI ownership
This skill owns credential and PAT hygiene for the direct, PAT-authenticated `gh` CLI that agents use through the terminal. Practical checks, no token printing or URL embedding, least-privilege scoping, and secret handling live in references/security-and-credentials.md. No broker, REST-client fallback, workflow allowlist, GitHub App, or director-only restriction is introduced as a security architecture; the direct `gh` CLI is the intentional mechanism.

## Unmatched task
Consult the official GitHub and Git documentation for credential and environment behavior: <https://docs.github.com> and <https://git-scm.com/docs>.
