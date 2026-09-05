# Configure protected environments

Control where deployments happen and who may deploy.

## Environments
GitHub environments group deployment targets (for example `staging`, `production`) with protection rules and secrets.

## Protection rules
- Require reviewers for deployments to sensitive environments.
- Require a configured deployment branch (or allow selected branches only).
- Use environment protection so a deploy is not performed silently.

## Secrets
Environment secrets are scoped to the environment and exposed only to jobs that target it. Keep deployment secrets in protected environments rather than repository-wide. Full credential and secret handling guidance lives in gg-env.

## Boundary
- Environments govern deployment behavior. They are a human-governance surface here; the workflow lifecycle (dispatch, run, collect, iterate) is owned by `gg-actions`.
- Environment secrets are scoped to that environment's jobs; full credential and secret handling lives in `gg-env`.

https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments | checked 2026-08-28 | re-check on GitHub environments change
