# Choose hosted or self-hosted runners

Select a runner and understand the security implications of each option.

## GitHub-hosted runners
Hosted runners are ephemeral, managed by GitHub, and start from a clean image for each job. They are the safer default: you do not manage the machine, and each run is isolated.

## Self-hosted runners
Self-hosted runners run on your own infrastructure. They are not ephemeral and can persist state across jobs, so a compromised or malicious workflow can affect other work. Treat self-hosted runners as a security boundary:
- Only add self-hosted runners to repositories you trust to run arbitrary code.
- Do not run self-hosted runners in an environment with privileged access if untrusted code can reach them.
- Prefer hosted runners unless you have a concrete reason to self-host.

## Labels
Runners are addressed by `runs-on` labels. GitHub-hosted runners have predefined labels (for example `ubuntu-latest`); self-hosted runners use custom labels you assign. Choose `runs-on` labels that select the intended runner and verify a self-hosted runner is the one you expect.

## Guidance
- Default to GitHub-hosted runners for isolation and clean state.
- If you self-host, isolate the runner from anything you cannot afford to lose and restrict which workflows can target it.
- Pin `runs-on` labels deliberately.

https://docs.github.com/en/actions/using-github-hosted-runners/using-github-hosted-runners/about-github-hosted-runners | checked 2026-08-28 | re-check on hosted-runner change
https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/using-self-hosted-runners-in-a-workflow | checked 2026-08-28 | re-check on self-hosted-runner change
https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/using-labels-with-self-hosted-runners | checked 2026-08-28 | re-check on runner-labels change
