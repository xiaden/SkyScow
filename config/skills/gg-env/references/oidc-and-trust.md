# OIDC trust

Understand how OpenID Connect binds workload identity to an exact context.

## What OIDC does
OIDC lets a workload (for example a GitHub Actions job) request a short-lived token that a cloud provider or registry trusts, so it can authenticate without a stored long-lived secret. GitHub issues the token when the job sets `permissions: id-token: write`.

## Trust context
Configure the relying party to accept only the exact workflow identity you control: a specific repository, branch, or environment. Prefer the immutable `sub` claim where supported rather than a mutable ref, and restrict by the conditions your provider supports. Over-broad trust conditions allow any matching identity to authenticate.

## Audience (`aud`) claim
The `aud` claim names the intended relying party and anchors trust: the action sets the audience value and the cloud IdP trust policy must pin the expected `aud` to that exact relying party. A missing or wildcard `aud` defeats the trust model. Audience guidance and set-up live in gg-actions `oidc-trust.md`.

## Guidance
- Request `id-token: write` only in the job that needs the token.
- Keep every other permission minimal.
- Prefer OIDC-based access (including trusted publishers) over embedding long-lived secrets.
- Recheck claim formats and trust policies after provider or GitHub changes, including the post-2026-07-15 immutable `sub` change.
- Always pin and match the action's `aud` value to the intended relying party; never accept a wildcard audience.

## Boundary
OIDC trust is the security context here. Workflow-specific OIDC usage is in gg-actions; this is the canonical trust guidance. Never pair OIDC with over-broad permissions or stored secrets.

https://docs.github.com/en/actions/concepts/security/openid-connect | checked 2026-08-28 | re-check on OIDC claim or trust-policy change
