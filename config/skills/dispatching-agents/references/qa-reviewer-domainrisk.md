# QA-Reviewer-DomainRisk

Dispatch the read-only domain-risk reviewer as part of QA-PushManager's adversarial review batch. Dispatch it **once per selected lens**; do not bundle lenses into a single invocation.

## When to Dispatch

**Dispatch when:**
- QA-PushManager has completed deterministic validation for a candidate
- The actual diff exposes one or more concrete technical risk lenses such as security/auth, concurrency, filesystem/path, persistence/data integrity, migrations/schema, networking/protocol, api-compatibility, frontend-state, resource/performance, or process-execution/configuration
- Up to 3 materially relevant lenses justify up to 3 simultaneous domain-risk invocations

**Do NOT dispatch when:**
- Deterministic validation has failed
- No meaningful technical lens can be grounded in the candidate diff — zero domain-risk invocations is valid
- You need the reviewer to repair code or tests
- You need a general code review rather than one assigned risk lens
- You intend to review more than one lens in a single invocation — dispatch one invocation per lens

## Dispatch Template

```text
Review candidate [CANDIDATE_SHA] through this explicitly assigned risk lens: [ASSIGNED_LENS].

Original user request:
[VERBATIM USER REQUEST]

Immutable requirement ledger:
- Candidate SHA: [CANDIDATE_SHA]
- Base SHA or diff range: [BASE_SHA_OR_DIFF_RANGE]
- Required behavior: [REQUIREMENTS]
- Deterministic validation: [VALIDATION_RESULTS]
- Assigned lens: [ASSIGNED_LENS]

Context files to read (read-only, under the isolated snapshot):
- [REVIEW_ROOT] — absolute path of the isolated detached checkout at [CANDIDATE_SHA]; the only place to read candidate files
- [REPOSITORY_INSTRUCTIONS] — repository rules
- [CANDIDATE_DIFF_OR_CHANGED_FILES] — primary review subject
- [DOMAIN_BOUNDARY_FILES] — trust, state, resource, protocol, or configuration boundaries relevant to the lens
- [RELEVANT_TESTS_OR_DOCS] — supported invariants and safeguards

Input:
```json
{
  "candidate_sha": "[CANDIDATE_SHA]",
  "base_sha": "[BASE_SHA_OR_EMPTY]",
  "diff": "[DIFF_OR_RANGE]",
  "repository_instructions": "[INSTRUCTIONS]",
  "task_context": "[TASK_CONTEXT]",
  "deterministic_validation": "[VALIDATION_RESULTS]",
  "review_root": "[REVIEW_ROOT]",
  "assigned_lens": "[ASSIGNED_LENS]"
}
```

Review only the assigned lens. Establish exposure, infer invariants, attack
plausible scenarios, and verify existing safeguards before reporting a finding.
If the lens is not materially relevant, return `{}`. Remain read-only. Return
exactly one raw JSON value: `{}` for a clean review for the assigned lens,
otherwise a single object mapping stable issue IDs to shared issue records.
Every issue record must include the shared required fields (`severity`,
`blocks_push`, `files`, `location`, `trigger`, `problem_description`, `evidence`,
`candidate_relationship`, `repair_route`, `recommended_action`,
`expected_behavior`); optionally include `impact` and
`existing_safeguard_analysis`. No prose, no PASS/FAIL heading, no Markdown
fences.
```

## Required Fields

- Candidate SHA and base SHA or diff range
- Verbatim user request and immutable requirement ledger
- Deterministic validation results
- Explicit assigned lens selected from the actual diff
- Repository instructions
- `review_root` — absolute path of the isolated snapshot at the candidate SHA
- Candidate diff and files defining the relevant domain boundaries

## Expected Output

Return `{}` for a clean or irrelevant review. Otherwise return a single JSON object keyed by stable issue IDs; every issue must include all shared required fields listed above. Do not return prose headings or modify files.
