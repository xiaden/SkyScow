# Choose events and triggers, and dispatch workflows manually

Select the events that start a workflow and understand which triggers are privileged.

## Event categories
- Push and pull request events (`push`, `pull_request`, `pull_request_target`).
- Manual dispatch (`workflow_dispatch`).
- Scheduled runs (`schedule`, using cron).
- Repository events (`repository_dispatch`, `issues`, `release`, `workflow_run`).
- Webhook and activity events for many repository actions.

## Privileged and over-broad triggers — review carefully
Some triggers deserve extra scrutiny because they run workflow code in a sensitive context:
- `push` — runs on commits; make sure it is not the only review gate.
- `workflow_run` — runs when another workflow finishes; verify you filter on the expected upstream workflow and repository, or an attacker may trigger it.
- `repository_dispatch` — lets an external caller start the workflow; restrict who may send the event and validate its payload.
- `schedule` — runs on a timer, not a review; keep its jobs read-only and least privileged.
- `pull_request_target` — runs in the context of the base branch with access to secrets; never check out or execute untrusted PR-provided code with it.

Prefer narrow triggers and explicit branch filters (`on.push.branches`), and keep privileged workflows at the least privilege they need.

## Manual UI dispatch
`workflow_dispatch` starts a workflow from the Actions tab. Define `inputs` to let a human pass parameters. Combine manual dispatch with environment protection rules so a deploy to a sensitive environment requires reviewers or is limited to protected branches.

## Boundary
Manual dispatch from the Actions tab belongs here. Triggering `workflow_dispatch` or `repository_dispatch` from the terminal and the full run/collect/iterate loop are in `references/workflow-lifecycle.md`.

https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows | checked 2026-08-28 | re-check on events or input-limit change
https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments | checked 2026-08-28 | re-check on environments change
https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions | checked 2026-08-28 | re-check on GitHub security-advisory or Actions change
