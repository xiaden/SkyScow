# Credentials and visibility (shared table)

Canonical shared table for visibility/plan branching, credential safety, and the
Docker/artifact-attestation and Pages facts that the `gg-artifacts` and `gg-docs`
consumers also load. This file is the sole authored source; byte-identical copies
live in `gg-actions`, `gg-artifacts`, and `gg-docs`, each of which loads its own copy
via a relative path. Propagate changes only from this canonical copy with
`scripts/sync-shared-table.sh`; never edit a consumer copy directly. There are no
cross-skill file imports, no symlinks, and no absolute paths.

## Visibility and plan branching

Know when a GitHub feature depends on repository visibility or a paid plan, and branch
your guidance accordingly.

- GitHub Pages sites are publicly available by default even when the source repository
  is private or internal; publishing privately is Enterprise Cloud-gated, and user/org
  sites cannot be treated as private project documentation.
- GitHub Free requires a public repository for Pages publication; private publication is
  a paid-plan (Enterprise Cloud) feature.
- Branch protection on private repositories requires a paid plan (Team or Enterprise);
  protected environments and their controls likewise vary by plan. Never silently assume
  the higher tier.
- Some Actions and attestation features, for example private/internal artifact
  attestations, require GitHub Enterprise Cloud and are not available on GitHub
  Enterprise Server.
- Plan and visibility determine which branch of a procedure applies.

Guidance:

- Determine the repository visibility and the account plan before advising on a feature.
- Do not assume a private repository makes its hosted output private; publication
  behavior is separate from source visibility.
- When a feature is plan- or visibility-gated, give both branches explicitly.

https://docs.github.com/en/enterprise-cloud@latest/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site | checked 2026-08-28 | re-check on Pages visibility or plan change
https://docs.github.com/en/get-started/learning-about-github/githubs-plans | checked 2026-08-28 | re-check on GitHub plan or billing change
https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches | checked 2026-08-28 | re-check on branch-protection plan or behavior change
https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments | checked 2026-08-28 | re-check on environment-protection change

## No-plaintext credential rules

- Never store credentials in plaintext. Git's `credential.helper = store` writes
  `~/.git-credentials` in the clear; it is a hazard, never setup guidance.
- Use an OS keychain helper or a verified CLI (`gh auth login` with a keyring) so tokens
  are stored encrypted and scoped to your user. On an unverified CLI shim, validate its
  version and behavior before trusting output.
- Never put tokens, passwords, or private keys in a repository, a commit, `.git/config`,
  or an issue or PR comment. If a secret is committed, rotate it immediately.
- Prefer fine-grained personal access tokens or GitHub App installation tokens scoped to
  the smallest needed set of resources over broad tokens.
- Derived secrets must be masked in any logs or output.
- The existing PAT-authenticated `gh` CLI is the intentional mechanism; never embed a token in a URL or a committed file, and never print a token into logs or output.

https://docs.github.com/en/get-started/getting-started-with-git/caching-your-github-credentials-in-git | checked 2026-08-28 | re-check on GitHub credential-caching behavior change
https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens | checked 2026-08-28 | re-check on GitHub token-type change
https://cli.github.com/manual/gh_auth_login | checked 2026-08-28 | re-check on gh auth behavior change

## Docker and artifact-attestation shared facts

- Local Docker is unavailable on the remote-runner orientation; every Docker task begins
  with visibility/plan branching.
- Public repositories may receive documented auto-provenance at `mode=max`; private
  repositories may default to `mode=min`, so request `provenance: mode=max` explicitly
  when that level is required.
- GitHub artifact attestations for private/internal repositories require GitHub
  Enterprise Cloud, are not supported on GitHub Enterprise Server, and have plan
  limitations.
- `docker/build-push-action` is on the v7 line; attestation inputs require a supported
  action line and attestation requires direct registry push. `load: true` and the Docker
  exporter strip attestations.
- Never put secrets in build args because provenance can expose build parameters; use
  secret mounts.
- `actions/attest` is the canonical new GitHub artifact-attestation path;
  `actions/attest-build-provenance` is a wrapper. Request only the needed id-token,
  attestations, artifact-metadata, and package permissions.
- Pin the provenance schema version on build and match it during verification; do not
  trust defaults (v0.2 vs v1). Verify registry authentication, image digest, provenance,
  trusted signer repository/workflow, and SBOM.

https://docs.docker.com/build/ci/github-actions/attestations/ | checked 2026-08-28 | re-check on Docker attestation or action-major change
https://docs.docker.com/build/metadata/attestations/slsa-provenance/ | checked 2026-08-28 | re-check on SLSA provenance schema change
https://github.com/docker/build-push-action | checked 2026-08-28 | re-check on docker/build-push-action major change
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations | checked 2026-08-28 | re-check on artifact-attestation plan or behavior change
https://github.com/actions/attest | checked 2026-08-28 | re-check on actions/attest major change

## Hosted docs and Pages shared facts

- `gg-docs` covers branch-source and Actions-source publication: build, upload Pages
  artifact, deploy Pages.
- Pages are publicly available by default even when the source repository is
  private/internal. GitHub Free requires a public repository; private publication is
  Enterprise Cloud-gated. User/org sites cannot be treated as private project
  documentation.
- Restrict the workflow to the required `contents: read`, `pages: write`, and
  `id-token: write` permissions.
- The `github-pages` environment protects the deployment; publication requires a
  workflow/default-branch prerequisite, respects artifact limits, and incurs a
  publication delay.
- When disabling or changing publication, verify and clean custom-domain DNS to prevent
  takeover; avoid wildcard DNS. Treat publication and HTTPS as delayed operations.

https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site | checked 2026-08-28 | re-check on Pages publishing-source change

## Boundary

This is the canonical shared table. Consumers load their own byte-identical copy by
relative path; there are no cross-skill file imports, no symlinks, and no absolute
paths. The direct, PAT-authenticated `gh` CLI is the intentional mechanism for the
workflow lifecycle (owned by `gg-actions`); this table documents credential and
visibility practice.
