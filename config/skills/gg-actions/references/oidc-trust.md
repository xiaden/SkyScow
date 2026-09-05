# Enable cloud auth with OpenID Connect

Use OIDC to let a workflow obtain short-lived credentials for cloud or registry access without storing long-lived secrets.

## Token issuance
To mint an OIDC token, the job must request `permissions: id-token: write`. GitHub then issues a token the workflow can exchange with a cloud provider or registry for short-lived credentials.

## Trust conditions
Configure the cloud provider or registry to trust only the exact workflow identity you control. Bind trust to a specific repository, branch or environment, and, where supported, the immutable `sub` claim rather than a mutable ref. Over-broad trust lets any matching workflow authenticate.

## Audience (`aud`) claim
The `aud` claim names the intended relying party and anchors OIDC trust. The action sets the audience value (e.g. via an `audience`/`aud` action parameter), and the cloud provider's IdP trust policy must pin the expected `aud` to that exact relying party. A missing or wildcard `aud` lets the token authenticate to the wrong party and defeats the trust model — always pin and match the expected audience.

## Guidance
- Request `id-token: write` only in the job that needs the OIDC token.
- Set and verify the `aud` value matches the relying party exactly; never accept a wildcard audience.
- Keep `contents: read` and other permissions minimal alongside it.
- Prefer OIDC-based access (including trusted publishers) over embedding long-lived secrets in a workflow.
- Recheck trust-policy and claim formats after GitHub or provider changes, including the post-2026-07-15 immutable `sub` change.

## Boundary
OIDC replaces stored secrets with short-lived, context-bound credentials. The general credential and least-privilege principle is canonical in gg-env; load `gg-env` for it.

https://docs.github.com/en/actions/concepts/security/openid-connect | checked 2026-08-28 | re-check on OIDC claim or trust-policy change
https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect | checked 2026-08-28 | re-check on OIDC hardening or trust-policy change
https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-cloud-providers | checked 2026-08-28 | re-check on OIDC aud or public trust-policy change
