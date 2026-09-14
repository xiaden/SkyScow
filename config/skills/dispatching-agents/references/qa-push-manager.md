# QA-PushManager

Dispatch QA-PushManager as the final publication gate for a candidate commit.

## When to Dispatch

**Dispatch when:**
- A candidate commit is ready for publication and must pass deterministic validation before push
- You need a repository-aware pre-push gate with independent adversarial review
- A repaired candidate must be revalidated from Gate 1
- A validated candidate needs the exact validated SHA pushed after authorization

**Do NOT dispatch when:**
- Implementation is still in progress — finish the implementation workflow first
- You need code repairs — route the reported issue to the appropriate implementation worker
- You need a normal post-implementation quality review — use `qa-reviewer`
- You are asking the manager to modify source, reviewer files, or the candidate while reviewing

## Dispatch Template

```text
Run the final publication gate for the candidate below.

Original user request:
[VERBATIM USER REQUEST]

Immutable requirement ledger:
- Candidate SHA: [CANDIDATE_SHA]
- Base SHA or diff range: [BASE_SHA_OR_DIFF_RANGE]
- Push authorization: [true|false] (explicit; false means validation only, never push)
- Required validation and publication constraints: [REQUIREMENTS]

Context files to read:
- [REPOSITORY_INSTRUCTIONS] — repository-specific rules
- [BUILD_AND_TEST_CONFIG] — applicable deterministic commands
- [CANDIDATE_CONTEXT_FILES] — changed files or relevant artifacts

Input:
```json
{
  "candidate_sha": "[CANDIDATE_SHA]",
  "base_sha": "[BASE_SHA_OR_EMPTY]",
  "diff": "[DIFF_OR_RANGE]",
  "repository_instructions": "[INSTRUCTIONS]",
  "task_context": "[TASK_CONTEXT]",
  "deterministic_validation": "[KNOWN_VALIDATION_RESULTS_OR_EMPTY]",
  "push_authorized": true
}
```

Run Gate 0 through Gate 5 in order. In Gate 0, create a mandatory isolated
disposable detached snapshot of the candidate at `candidate_sha` and run every
deterministic gate and review against that snapshot — never against a mutable
developer workspace. Stop at the first deterministic failure. Only after Gates
1–3 pass, dispatch the read-only reviewers selected per
`/home/opencode/.config/opencode/instructions/qa-applicability.md` in parallel:
correctness always, plus boundary, journey, and 0–3 domain-risk lenses as their
observable triggers hold. Every reviewer receives the same immutable candidate
context and the isolated snapshot path; each DomainRisk invocation receives its
own `assigned_lens`.

Fail closed: if any required reviewer invocation times out, crashes, fails to
spawn, returns no result, returns malformed output, or violates its schema,
abort with REVIEW INFRASTRUCTURE FAILURE — never treat partial reviewer success
as sufficient and never fabricate a product defect. Independently verify every
potentially blocking finding and gate rejection on verified `blocks_push: true`
findings only. Run the final integrity check against the isolated snapshot.
Push only the exact validated commit object
(`git push <remote> <candidate_sha>:refs/heads/<target-branch>`) and only when
`push_authorized` is exactly true; never force push unless explicitly authorized.
If validation passes without exact authorization, report the validated candidate
without pushing.
```

## Required Fields

| Field | Description |
|---|---|
| `[CANDIDATE_SHA]` | Exact commit under review |
| `[BASE_SHA_OR_DIFF_RANGE]` | Comparison point or diff range |
| `[REQUIREMENTS]` | Publication constraints and acceptance requirements |
| `[REPOSITORY_INSTRUCTIONS]` | Repository instructions and contribution rules |
| `[BUILD_AND_TEST_CONFIG]` | Manifests and formatter/linter/build/test configuration |
| `[CANDIDATE_CONTEXT_FILES]` | Changed files and relevant surrounding artifacts |
| `push_authorized` | Required explicit boolean; never infer authorization and never push without it |

The Input block is a template: replace the sample `true` in `push_authorized` with the candidate's actual explicit authorization boolean before dispatch.

## Expected Output

Return concise Markdown with exactly one status heading:

- `# PUSH APPROVED` — every applicable gate passed and the exact validated SHA was pushed
- `# VALIDATION PASSED — PUSH NOT AUTHORIZED` — every applicable gate passed and `push_authorized` was not exactly `true`; no push was attempted
- `# PUSH REJECTED` — a deterministic gate or a verified `blocks_push: true` review finding failed; also used when the push operation itself failed after validation
- `# VALIDATION STALE` — the candidate changed after validation/review
- `# REVIEW INFRASTRUCTURE FAILURE` — a required reviewer invocation failed its dispatch/completion contract; not a candidate finding

The report must preserve the manager's candidate, validation, reviews, repair-routes, infrastructure-failures, and push fields as applicable. For rejection, include the failed gate, evidence, why it blocks, and recommended repair route. After any repair, restart this dispatch from Gate 1 against the new candidate.

## Worker Coordination

QA-PushManager is responsible for creating and removing the isolated validation snapshot and for spawning all reviewers. The reviewers selected per `/home/opencode/.config/opencode/instructions/qa-applicability.md` (correctness always; boundary, journey, and 0–3 DomainRisk lens invocations when their observable triggers hold) must run in one parallel batch only after deterministic validation is green. Reviewers are read-only and return the shared issue-report object defined in their individual references (`{}` for a clean review). The manager independently verifies every potentially blocking finding.

## Validation Checklist

- [ ] Candidate SHA, branch, base/diff, and exact push authorization are explicit
- [ ] Mandatory isolated detached snapshot at `candidate_sha` created and verified before any gate
- [ ] Repository-specific commands are discovered rather than assumed
- [ ] Deterministic gates stop on first failure
- [ ] Reviewers selected per the canonical applicability reference dispatched in parallel after Gates 1–3 pass
- [ ] DomainRisk dispatched once per selected lens (0–3 lenses), each confined to its `assigned_lens`
- [ ] Reviewer infrastructure failure fails closed with REVIEW INFRASTRUCTURE FAILURE
- [ ] Blocking findings are independently verified; rejection gates on verified `blocks_push: true` only
- [ ] Final integrity check confirms the reviewed SHA is unchanged in the isolated snapshot
- [ ] Push is never attempted without explicit authorization
- [ ] The exact validated commit object is pushed; no force push without explicit authorization
