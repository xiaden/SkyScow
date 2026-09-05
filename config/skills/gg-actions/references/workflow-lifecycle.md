# Run and drive the full workflow lifecycle with `gh`

Drive a workflow change end-to-end using the existing PAT-authenticated `gh` CLI
directly through the terminal. This is the workflow lifecycle owner: inspect,
create/modify/remove, branch + push, dispatch/run, watch, view status and logs,
download artifacts, cancel, clean up, and iterate from collected results until
verification passes.

The exact `gh` flag set changes across CLI releases; validate the local `gh`
version and behavior first (see `gg-env` for credential/PAT checks and
`ggt-conventions` for whether this workspace's `gh` is a verified CLI). These
are the progressive-disclosure steps, in order.

## 1. Inspect existing workflows

- `gh workflow list` — list workflows in the repository.
- `gh workflow view <name-or-id> --yaml` — show the current workflow source.
- `gh run list` — list recent runs; `gh run list --workflow=<name>` filters to one workflow.

## 2. Create / modify / remove a workflow file

- Create or edit `.github/workflows/<name>.yml` on a feature branch. Authoring
  and syntax, triggers and events, least-privilege permissions, and secrets are
  in this skill's sibling references (workflow-authoring, events-and-dispatch,
  workflow-permissions, workflow-secrets) loaded on demand.
- Remove an obsolete workflow file with `git rm` and commit the deletion.

## 3. Branch and push the change

- Create a focused branch (`git switch -c <feature>`) and commit the workflow
  change (local state is `gg-core`).
- Push it to a remote you own or are authorized for (`git push -u origin <feature>`);
  remotes and PRs are `gg-repos`.

## 4. Dispatch or run the workflow

- `gh workflow run <name> --ref <branch>` — trigger `workflow_dispatch` from the
  terminal with optional `-f key=value` inputs.
- For an event-driven workflow, push the branch or trigger `repository_dispatch`
  (`gh api repos/<owner>/<repo>/dispatches -f event_type=<name>`); see the
  events-and-dispatch sibling reference for trigger details.

## 5. Watch the run

- `gh run watch <run-id>` — poll until the run completes, with `--exit-status`
  to exit nonzero on failure.
- `gh run list` — confirm which run id is the one you just started.

## 6. View status and logs

- `gh run view <run-id>` — job status, timings, and conclusion.
- `gh run view <run-id> --log` — full step logs; `--log-failed` for the failing
  steps only.
- `gh run list --status in_progress` — live view of in-flight runs.

## 7. Download artifacts

- `gh run download <run-id>` — download all artifacts from a run.
- `gh run download <run-id> -n <name> -D <dir>` — download one named artifact
  into a directory. Collected results feed the next iteration.

## 8. Cancel failed or stale runs

- `gh run cancel <run-id>` — cancel a failed, stale, or superseded run to stop
  wasting quota.

## 9. Clean up temporary branches / workflows / runs

- Delete a temporary remote branch after its PR merges: `git push origin --delete <branch>` (cleanup is `gg-repos`/`gg-core`).
- Remove a temporary workflow file with `git rm` when it is no longer needed.
- Cancelled/completed runs remain listed per retention; cancel stale ones so they do not linger as in-progress.

## 10. Iterate from collected results until verification passes

- Read the downloaded artifacts and step logs to find the failure.
- Fix the code or workflow, commit on the branch, and push again.
- Re-run (step 4) and watch (step 5); repeat until the run completes successfully
  and you have verified the artifact/log evidence — do not claim success on an
  unverified run.

## Boundary

Local branch/commit state is `gg-core`; push/remotes/PR collaboration is
`gg-repos`; credentials/PAT hygiene and `gh` auth checks are `gg-env`; hosted
Docker/artifacts are `gg-artifacts`. This reference is the workflow-lifecycle
loop only.

## Official sources

Run, workflow, and dispatch reference:
https://cli.github.com/manual/gh_workflow_run | checked 2026-08-28 | re-check on gh CLI run command change
https://cli.github.com/manual/gh_run_watch | checked 2026-08-28 | re-check on gh run command change
https://cli.github.com/manual/gh_run_view | checked 2026-08-28 | re-check on gh run command change
https://cli.github.com/manual/gh_run_download | checked 2026-08-28 | re-check on gh run command change
https://cli.github.com/manual/gh_run_cancel | checked 2026-08-28 | re-check on gh run command change
