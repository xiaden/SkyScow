# Set least-privilege permissions

Give every workflow the minimum permissions it needs and the smallest `GITHUB_TOKEN` scope.

## The permission block
Declare `permissions:` at the workflow or job level. Start with `contents: read` and add only the scopes the job actually uses. Omit scopes that are not needed, or set them to `none`.

## GITHUB_TOKEN
GitHub provides an automatic token for each job. Its default permissions are broad; set them explicitly to least privilege. Grant only the scopes a step needs (for example `contents: read`, `packages: read`, `id-token: write` for OIDC). Never grant more than the workflow uses.

## Guidance
- Prefer fine-grained scopes over broad ones; never use a token with more access than the job requires.
- Treat the `GITHUB_TOKEN` as the default and scope it down; reserve personal access tokens for actions it cannot perform.
- Review privileged triggers alongside permissions: a privileged trigger plus a broad token is a high-risk combination.

## Boundary
Credential storage and the principle of least privilege in general are canonical guidance in gg-env; this reference covers the workflow `permissions` block and token scoping in particular.

https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token | checked 2026-08-28 | re-check on GitHub token-permissions change
https://docs.github.com/en/actions/security-guides/automatic-token-authentication | checked 2026-08-28 | re-check on GITHUB_TOKEN behavior change
