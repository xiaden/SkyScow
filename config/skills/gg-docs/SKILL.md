---
name: gg-docs
description: Use ONLY when building and publishing hosted documentation through GitHub Pages: two publishing sources (the repository Pages source, or a GitHub Actions workflow), the canonical build -> upload Pages artifact -> deploy sequence, the github-pages environment and minimal permissions, project versus user/org sites, custom domains (CNAME/DNS), HTTPS, and DNS cleanup to prevent takeover. Load before publishing or configuring documentation artifacts on Pages.
---

# gg-docs

**Purpose:** Build and publish hosted documentation through GitHub Pages for docs maintainers and release operators. This body carries no volatile facts — time-sensitive claims (action majors, plan gates, DNS behavior) live only in the dated references, never here.

## When to use
- Publishing project documentation to GitHub Pages, from either the repository Pages source or a GitHub Actions workflow
- Sequencing a Pages deployment as build, then upload the Pages artifact, then deploy
- Configuring, verifying, or retiring a custom domain and its DNS records

**Do NOT use** for general web/documentation hosting outside GitHub Pages, or for non-GitHub static hosting — out of scope. **Do NOT use** for workflow authoring or security fundamentals — load `gg-actions`. **Do NOT use** for credentials, secrets, or visibility/plan facts beyond the shared table — load `gg-env`.

## First safe step
Start from the visibility/plan branch before publishing: determine the repository visibility and account plan, because Pages sites are publicly available by default even for private/internal repositories, GitHub Free requires a public repository, and private publication is Enterprise Cloud-gated. Consult the shared visibility table before anything else.

## Task index
- Publish documentation to Pages, always in the canonical order build -> upload Pages artifact -> deploy, and configure the github-pages environment and minimal permissions -> references/publish-project-docs.md
- Configure, verify, and retire a custom domain (CNAME/DNS records, HTTPS, takeover prevention) -> references/custom-domain.md
- Visibility/plan branching, credential safety, and shared Pages facts -> references/credentials-and-visibility.md

## Boundary
This skill owns GitHub Pages documentation publication and custom-domain practice. The workflow lifecycle (dispatch, run, collect, iterate) is owned by `gg-actions`; credentials/PAT hygiene is `gg-env`. Non-GitHub static hosting is out of scope.

## Unmatched task
Consult the official GitHub Pages documentation: <https://docs.github.com/en/pages>.
