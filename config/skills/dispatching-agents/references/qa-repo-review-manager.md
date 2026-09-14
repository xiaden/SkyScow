# QA-RepoReviewManager

This reference remains the retained routing/dispatch owner. It routes to the retained `qa-repo-review-manager` behavioral agent and the project-local `repository-review-manager` implementation documentation; the dispatch template, required fields, and negative constraints remain unchanged.

Dispatch QA-RepoReviewManager as the one-shot whole-tree repository-review manager
for one explicit GitHub tree URL.

QA-RepoReviewManager resolves an exact named branch/ref to its run-start head,
materializes the complete current-head tree as an immutable detached snapshot,
dispatches every selected read-only reviewer in canonical batched parallel
groups, collects responses fail-closed, and returns a concise Markdown result. It is **not** a
push gate and does **not** review a diff or candidate commit; the resolved SHA is
provenance only.

## When to Dispatch

**Dispatch when:**
- You have exactly one full HTTPS GitHub tree URL of the form
  `https://github.com/<owner>/<repository>/tree/<exact-branch-or-ref>` and need
  the complete current-head tree reviewed.
- You need manager-owned lens selection, canonical batched-parallel reviewer dispatch,
  fail-closed collection, and provenance-preserving handling of disagreement.
- You need a `report`/`dry-run` review result. (Ordinary issue and security
  publication is never implied by this dispatch; submit invokes the logical `submit_ordinary_issue` lifecycle only after manager authorization, while only the manager-owned callback capability performs the permitted ordinary operation.)

**Do NOT dispatch when:**
- No explicit target URL is supplied; never infer a target from the workspace,
  current directory, git remote, or any ambient state.
- You need candidate or push-gate validation outside this complete-tree review — use the appropriate push-review manager.
- You need a post-implementation review — use `qa-reviewer`.
- You need code repairs or implementation; this manager never edits source.

## Provider contract

Ordinary issue operations use the manager-owned direct `gh api` capability. Security findings use only the private repository security-advisory endpoint with literal GitHub API version `2022-11-28`; an owned/authorized finding whose private capability is unavailable, disabled, or rejected returns `blocked_private_security_route` and never falls back to public Issues. A finding that is non-owned, or whose authenticated identity, repository ownership, or organization authorization cannot be verified, is report-only under the exact heading **Review Prior to Submitting** and is never submitted publicly. Provider preflight requires exact equality with `2022-11-28`; any missing, malformed, or different version fails closed as `provider_unavailable`. Report and dry-run remain no-write modes; submit requires explicit authorization and the manager's ordinary-publication checks.

## Dispatch Template

```text
Run a one-shot whole-tree GitHub review for the target below.

Original user request:
[VERBATIM USER REQUEST]

Immutable requirement ledger:
- Target URL: [TARGET_URL]
- Mode: [report|dry-run|submit]
- Run confirmation: [RUN_CONFIRMATION]
- Submit authorized: [true|false]
- Required behavior and constraints: [REQUIREMENTS]

Input:
```json
{
  "target_url": "[TARGET_URL]",
  "mode": "[report|dry-run|submit]",
  "run_confirmation": "[RUN_CONFIRMATION]",
  "submit_authorized": false,
  "context": "[TASK_CONTEXT]"
}
```

Before any GitHub or Git operation, load and apply the applicable guidance
selected through `gg-router`: `gg-repos`, `gg-env`, `gg-core`, and
`ggt-conventions`. The command argument is the only target source. Review the
complete materialized tree at the run-start resolved head — never a diff and
never a candidate commit.

Dispatch the whole-tree reviewers selected per
`/home/opencode/.config/opencode/instructions/qa-applicability.md` in canonical
batched parallel groups — correctness always; boundary and journey when the tree
contains the corresponding observable surfaces; plus each
`qa-repo-reviewer-domainrisk` lens matched from the tree's observable surfaces,
dispatched in the canonical order and concurrency/batching rule owned there
(zero matched lenses dispatch none; one to three dispatch in one parallel batch;
more than three dispatch in consecutive batches of at most three until every
matched lens completes) — each with the same one immutable review context.
Reviewers never consume one another's output. Collect fail-closed: timeout, crash,
spawn_failure, missing_result, non_single_json, malformed_response, schema_invalid_response, or
dispatch_contract_failure yields REVIEW_INFRASTRUCTURE_FAILURE; no partial batch
is sufficient.
```

## Required Fields

| Field | Description |
|---|---|
| `[TARGET_URL]` | Exactly one full HTTPS GitHub tree URL; the only target source |
| `[MODE]` | `report` (default), `dry-run`, or `submit` |
| `[RUN_CONFIRMATION]` | Explicit confirmation of this exact target and run |
| `submit_authorized` | Explicit boolean; needed but never sufficient for `submit` |
| `[REQUIREMENTS]` | Required behavior, accepted ref semantics, and constraints |

## Expected Output

Return concise Markdown making the resolved `owner`/`repository`/`ref`, the
`resolved_sha`, the `run_id`, the selected `mode`, the snapshot disclosures, the
selected review lenses, and the performed read/write actions explicit. When
collection fails closed, return the terminal status
`REVIEW_INFRASTRUCTURE_FAILURE` with each failing invocation's reviewer
identity, assigned lens where applicable, and failure class.

## Negative Constraints

Do NOT infer or default the target; do NOT push or operate a push gate; report and dry-run perform no provider writes, while authorized submit may create an ordinary issue through the manager-owned callback; do NOT close or reopen issues, advisories, labels, branches, or any remote state; do NOT edit the six canonical push files; do NOT execute
repository-supplied code, scripts, builds, tests, hooks, CI, or workflows; do NOT
give reviewers credentials or provider tools; do NOT implement capabilities outside this manager's current boundary: verification/merge, report rendering, ordinary publication, security routing through the private repository-advisory mechanism only, labels, or dedupe.
