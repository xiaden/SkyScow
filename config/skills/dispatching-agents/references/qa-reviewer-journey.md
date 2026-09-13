# QA-Reviewer-Journey

Dispatch the read-only journey reviewer as part of QA-PushManager's adversarial review batch.

## When to Dispatch

**Dispatch when:**
- QA-PushManager has completed deterministic validation for a candidate
- The candidate changes a workflow that must be traced end to end across commands, services, UI, persistence, events, or external systems

**Do NOT dispatch when:**
- Deterministic validation has failed
- You need the reviewer to repair code or tests
- You need only isolated correctness, boundary, or domain-specific analysis

## Dispatch Template

```text
Review candidate [CANDIDATE_SHA] for complete end-to-end journey integrity.

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
- [ENTRYPOINTS_AND_HANDOFF_FILES] — routes, commands, consumers, persistence, events, and follow-on paths
- [RELEVANT_TESTS_OR_DOCS] — supported workflow evidence

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

Identify affected actors and entry points, trace representative journeys through
every material handoff and state transition, and verify the final observable
state and follow-on behavior. Report only verified candidate-introduced defects.
Remain read-only. Return exactly one raw JSON value: `{}` for a clean review,
otherwise a single object mapping stable issue IDs to shared issue records.
Every issue record must include the shared required fields (`severity`,
`blocks_push`, `files`, `location`, `trigger`, `problem_description`, `evidence`,
`candidate_relationship`, `repair_route`, `recommended_action`,
`expected_behavior`); optionally include `journey` and `break_point`. No prose,
no PASS/FAIL heading, no Markdown fences.
```

## Required Fields

- Candidate SHA and base SHA or diff range
- Verbatim user request and immutable requirement ledger
- Deterministic validation results
- Repository instructions
- `review_root` — absolute path of the isolated snapshot at the candidate SHA
- Candidate diff or changed files
- Entry points, handoff components, consumers, persistence, and relevant tests/docs

## Expected Output

Return `{}` for a clean review. Otherwise return a single JSON object keyed by stable issue IDs; every issue must include all shared required fields listed above. Do not return prose headings or modify files.
