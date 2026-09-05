# Store and use Actions and environment secrets

Keep secrets out of workflow source and pass them through encrypted mechanisms only.

## Actions secrets vs environment secrets
- Repository (Actions) secrets are encrypted values you reference in a workflow with `${{ secrets.NAME }}`; they are available to workflows in that repository.
- Environment secrets are scoped to a protected environment and are exposed only to jobs that target it. Use environment secrets for deployment credentials that should be gated by environment protection rules.
- Choose the narrowest scope that works: environment secrets over repository-wide secrets when the value belongs to one deployment target.

## Never plaintext
- Never put a token, password, private key, or other secret in a workflow file, a commit, or a log.
- Secrets referenced as `${{ secrets.NAME }}` are masked in logs; derived secrets must be masked too.
- If a secret is exposed, rotate it immediately; removing it from the workflow does not undo exposure in history or logs.

## Guidance
- Reference secrets only through the encrypted secrets mechanism, never by embedding values.
- Give each secret the smallest scope and use environment protection to gate sensitive deployments.
- Prefer fine-grained tokens or GitHub App installation tokens for human/service use over broad personal access tokens.

## Boundary
Credential storage, plaintext hazards, and safe alternatives are canonical in gg-env; load `gg-env` for that guidance. This reference covers where secrets live in workflows.

https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/storing-and-using-secrets | checked 2026-08-28 | re-check on Actions-secrets change
https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments | checked 2026-08-28 | re-check on environments change
