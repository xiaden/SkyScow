# Pin and vet third-party actions

Use third-party actions only after vetting them, and pin them to an immutable reference.

## Full-SHA pinning (preferred)
Pin third-party actions to a full commit SHA so the code you run is fixed and an action maintainer or attacker cannot silently change what executes. Floating major tags (for example `actions/checkout@<major>`, a placeholder for the `@vN` form) can move; a full SHA is immutable.

## Version-tag pinning
Where full-SHA pinning is not used, pin to a major version tag and let Dependabot keep it current. A major tag is less secure than a full SHA but better than a mutable branch reference. Never reference an action by a branch name.

## Keep actions current
Use Dependabot to receive updates for pinned actions so you pick up security fixes and avoid running a stale, vulnerable version.

## Trusted publishers
Prefer actions that authenticate through a trusted publisher (OIDC-based publication) over actions that require you to hand them a long-lived secret. This limits how much access a third-party action holds.

## Vet before use
- Review what a third-party action does, what permissions it requests, and who maintains it.
- Prefer well-known actions from the `actions/*` organization.
- Limit each action's `GITHUB_TOKEN` scope to what the workflow actually needs.

## Boundary
Pinning and vetting are part of workflow security. The general credential and least-privilege principle live in gg-env; load `gg-env` for those.

https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions | checked 2026-08-28 | re-check on GitHub security-advisory or Actions change
https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot | checked 2026-08-28 | re-check on Dependabot behavior change
