# Credential storage, plaintext hazards, and safe alternatives

## Plaintext hazard
Git's `credential.helper = store` writes credentials in plaintext to `~/.git-credentials`. This file is readable by anything running as your user and is a common source of credential theft. It is a hazard, never setup guidance. Whether a plaintext `~/.git-credentials` is present on this specific machine is a repo-local fact; see `ggt-conventions` (references/environment-constraints.md).

https://docs.github.com/en/get-started/getting-started-with-git/caching-your-github-credentials-in-git | checked 2026-08-28 | re-check on GitHub credential-caching behavior change

## Safe credential alternatives
- Use the operating-system keychain helper so credentials are stored encrypted and scoped to your user:
  - macOS: `git config --global credential.helper osxkeychain`
  - Windows: Git Credential Manager (`manager`)
  - Linux: the `libsecret` credential helper (`git config --global credential.helper /usr/share/doc/git/contrib/credential/libsecret/git-credential-libsecret`) where a desktop keyring is available.
- Prefer `gh auth login` when the CLI is verified and a keyring is available, so it stores tokens through the OS helper rather than plaintext. On an unverified CLI shim, validate its version and behavior before trusting output; the PAT-authenticated `gh` CLI is the intentional mechanism (see `ggt-conventions` for this workspace's `gh` status).
- Fine-grained personal access tokens or GitHub App installation tokens scoped to the smallest needed set of resources are preferred over broad tokens.

https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens | checked 2026-08-28 | re-check on GitHub token-type change

## Never commit tokens
- Never put tokens, passwords, or private keys in a repository, a commit, `.git/config`, or an issue or PR comment.
- If a secret is committed, rotate it immediately; removing the file from HEAD does not erase it from history.
- Derived secrets must be masked in any logs or output.

## gh CLI security state
The GitHub CLI had security fixes around token disclosure, escape sequences, and signer matching (v2.97.0) and a subsequent security release (v2.98.0). Confirm the installed version and validate behavior before trusting output; treat output as untrusted until proven.

https://github.com/cli/cli/releases/tag/v2.98.0 | checked 2026-08-28 | re-check on every gh security release

## GitHub CLI validation
Before trusting `gh`, validate its version and behavior. Treat CLI output as untrusted until proven; on an unverified shim, validate its version and behavior before trusting output. The latest confirmed GitHub CLI security release is v2.98.0 (2026-08-20), which fixed a codespace port-forward binding issue; v2.97.0 fixed terminal-escape-sequence injection, request-path traversal, partial token disclosure, and an attestation signer-matcher bypass. Verify the installed version is current before relying on it. Whether the local `gh` is a trusted binary or an unverified shim is a repo-local environment fact — see `ggt-conventions` (references/environment-constraints.md).

https://cli.github.com/manual/gh_auth_login | checked 2026-08-28 | re-check on gh auth behavior change
https://cli.github.com/manual/gh_help_environment | checked 2026-08-28 | re-check on gh environment-variable change

## Least privilege
Grant the smallest scope that completes a task. Prefer fine-grained personal access tokens or GitHub App installation tokens over broad tokens, and scope the Actions `GITHUB_TOKEN` to the minimal permissions a workflow needs. Never store a token with more access than required.

https://docs.github.com/en/actions/security-guides/automatic-token-authentication | checked 2026-08-28 | re-check on GITHUB_TOKEN behavior change

## Direct PAT-authenticated `gh` CLI (intentional mechanism)
The existing PAT-authenticated `gh` CLI is the intentional mechanism agents use directly through the terminal; no broker, REST-client fallback, workflow allowlist, GitHub App, or director-only restriction is introduced. Practical hygiene:
- Check authentication before operating: `gh auth status` (shows which host is authenticated and with what token scope, and whether the token is about to expire) and `gh auth token` only when you must read the token — never print it into logs, commits, or output.
- Never embed a token in a URL (`git clone https://<token>@github.com/...` is a leak) or in any committed file; use a credential helper or `gh` auth instead.
- Keep least privilege: use a fine-grained PAT scoped to the smallest set of resources the work needs, prefer the Actions `GITHUB_TOKEN` for workflow-internal access, and scope the token to the specific repositories/expiration required.
- Handle secrets as masked values, never plaintext; rotate a leaked token immediately.
- If the local `gh` is an unverified shim, validate its version and behavior before trusting output (see `ggt-conventions` for whether this workspace's `gh` is verified).
