# Author GitHub Actions workflow syntax

Write and structure a workflow file in `.github/workflows/` using YAML.

## Structure
A workflow has top-level keys: `name`, `on` (triggers), `permissions`, `env`, and `jobs`. Each job runs on a runner (`runs-on`) and runs `steps` in order. A step either `run`s a shell command or `uses` an action.

## Conventions
- Give the workflow a `name`, and name jobs and steps for readable logs.
- Keep jobs focused; use `needs:` to order dependent jobs and pass data between them with job outputs or artifacts.
- Use `env` for values a job needs; reference runtime data with `github` context expressions.
- Validate syntax locally or in a dry run before relying on it.

## Guidance
- Prefer a small number of clear jobs over one monolithic job.
- Express configuration in the workflow, not in long shell one-liners.
- Reference variables with `${{ }}` expressions; quote them when they could be empty.

## Boundary
Workflow files do not themselves carry credentials. Keep secrets out of workflow source (see references/workflow-secrets.md).

https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions | checked 2026-08-28 | re-check on workflow-syntax or action-major change
