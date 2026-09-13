---
description: Run the publication manager and its parallel adversarial review workflow for a candidate commit; push only when every gate passes and authorization is explicit.
agent: qa-push-manager
argument-hint: "<candidate SHA or commit range> [push_authorized=true|false] [context]"
---

Run the complete `qa-push-manager` publication workflow for the candidate described below.

Candidate input:
$ARGUMENTS

## Manager workflow

1. Establish the repository root, branch, remote, candidate SHA, base SHA or diff range, and the exact push authorization state. Treat the candidate SHA as authoritative; do not assume uncommitted changes are part of it.
2. Create a mandatory isolated, disposable, detached snapshot of the candidate at the candidate SHA (`git worktree add --detach` or a fresh-clone fallback) and verify HEAD equals the candidate SHA with a clean tracked tree. Run every validation gate and review against that snapshot, never against a mutable developer workspace.
3. Discover repository instructions and applicable format, lint, type-check, configuration, build, and test commands from the repository itself.
4. Run deterministic validation in order (static validation, build, tests). Stop on the first deterministic failure and return `PUSH REJECTED` with concise evidence and a repair route.
5. Only when deterministic validation passes and the snapshot invariants still hold, dispatch in one parallel batch:
   - `qa-reviewer-correctness`
   - `qa-reviewer-boundary`
   - `qa-reviewer-journey`
   - `qa-reviewer-domainrisk` once per materially relevant technical lens selected from the actual diff (0–3 lenses; each invocation receives its own `assigned_lens`)
   Every reviewer receives the same immutable candidate context, deterministic results, and the isolated snapshot path. Reviewers are read-only and never see or consume each other's findings.
6. Fail closed on reviewer infrastructure failure: timeout, crash, spawn failure, missing result, malformed output, or schema violation aborts with `REVIEW INFRASTRUCTURE FAILURE`. Never treat partial reviewer success as sufficient and never fabricate a product defect.
7. Independently verify every potentially blocking reviewer finding, group verified findings by review domain and repair route, and reject the candidate only for verified `blocks_push: true` findings.
8. Perform the final integrity check against the isolated snapshot. If the candidate changed during validation or review, return `VALIDATION STALE` and require a restart from Gate 1.
9. Push the exact validated commit object (`git push <remote> <candidate_sha>:refs/heads/<target-branch>`) only if every gate passed and the input explicitly authorizes pushing. Otherwise report the validated candidate with `VALIDATION PASSED` and make the authorization state clear. Never force push unless explicitly authorized.

## Output contract

Return the manager's concise Markdown result using exactly one status heading:

- `# PUSH APPROVED`
- `# VALIDATION PASSED — PUSH NOT AUTHORIZED`
- `# PUSH REJECTED`
- `# VALIDATION STALE`
- `# REVIEW INFRASTRUCTURE FAILURE`

Preserve the manager's candidate, validation, reviews, repair-routes, infrastructure-failures, and push fields as applicable. Do not modify application source, reviewer files, or the candidate while reviewing it. After any repair, rerun this command against the new candidate from Gate 1.
