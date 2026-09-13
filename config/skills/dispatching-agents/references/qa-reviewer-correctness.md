# QA-Reviewer-Correctness

Dispatch the read-only correctness reviewer as part of QA-PushManager's adversarial review batch.

## When to Dispatch

**Dispatch when:**
- QA-PushManager has completed deterministic validation for a candidate
- The candidate needs an independent review of logic, contracts, cross-component behavior, and regression risk

**Do NOT dispatch when:**
- Deterministic validation has failed — fix or route that failure first
- You need the reviewer to repair code or tests
- You need only boundary, journey, or domain-specific analysis

## Dispatch Template

```text
Review candidate [CANDIDATE_SHA] for logical correctness and contract preservation.

Original user request:
[VERBATIM USER REQUEST]

Immutable requirement ledger:
- Candidate SHA: [CANDIDATE_SHA]
- Base SHA or diff range: [BASE_SHA_OR_DIFF_RANGE]
- Required behavior: [REQUIREMENTS]
- Deterministic validation: [VALIDATION_RESULTS]

Context files to read (read-only, under the isolated snapshot):
- [REVIEW_ROOT] — absolute path of the isolated detached checkout at [CANDIDATE_SHA]; the only place to read candidate files
- [REPOSITORY_INSTRUCTIONS] — repository rules
- [CANDIDATE_DIFF_OR_CHANGED_FILES] — primary review subject
- [RELEVANT_SURROUNDING_FILES] — callers, consumers, tests, and contracts

Input:
```json
{
  "candidate_sha": "[CANDIDATE_SHA]",
  "base_sha": "[BASE_SHA_OR_EMPTY]",
  "diff": "[DIFF_OR_RANGE]",
  "repository_instructions": "[INSTRUCTIONS]",
  "task_context": "[TASK_CONTEXT]",
  "deterministic_validation": "[VALIDATION_RESULTS]",
  "review_root": "[REVIEW_ROOT]"
}
```

Inspect the changed execution paths and report only verified candidate-introduced
defects. Remain read-only. Return exactly one raw JSON value: `{}` for a clean
review, otherwise a single object mapping stable issue IDs to shared issue
records. Every issue record must include the shared required fields (`severity`,
`blocks_push`, `files`, `location`, `trigger`, `problem_description`, `evidence`,
`candidate_relationship`, `repair_route`, `recommended_action`,
`expected_behavior`). No prose, no PASS/FAIL heading, no Markdown fences.
```

## Required Fields

- Candidate SHA and base SHA or diff range
- Verbatim user request and immutable requirement ledger
- Deterministic validation results
- Repository instructions
- `review_root` — absolute path of the isolated snapshot at the candidate SHA
- Candidate diff or changed files
- Relevant callers, consumers, tests, and contracts

## Expected Output

Return `{}` for a clean review. Otherwise return a single JSON object keyed by stable issue IDs; every issue must include all shared required fields listed above. Do not return prose headings or modify files.
