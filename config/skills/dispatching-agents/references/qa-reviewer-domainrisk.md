# QA-Reviewer-DomainRisk

Dispatch the read-only domain-risk reviewer as part of QA-PushManager's adversarial review batch. Dispatch it **once per selected lens**; do not bundle lenses into a single invocation.

WHEN a domain-risk lens applies and the observable repository/task fact that triggers it are owned by `/home/opencode/.config/opencode/instructions/qa-applicability.md`, which also owns the candidate lens set and the 0–3 bound. This reference owns only HOW the assigned lens is reviewed.

## When to Dispatch

**Dispatch when:**
- QA-PushManager has completed deterministic validation for a candidate
- The candidate's observable changed surface triggers one or more domain-risk lenses per `/home/opencode/.config/opencode/instructions/qa-applicability.md` (0–3 lenses per change)
- Each selected lens justifies its own domain-risk invocation; up to 3 simultaneous invocations

**Do NOT dispatch when:**
- Deterministic validation has failed
- No domain-risk lens is selected from the candidate's observable surfaces per the canonical applicability reference — zero domain-risk invocations is valid
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
Whether the lens applies — and the observable fact that triggered it — is owned by the canonical applicability file `/home/opencode/.config/opencode/instructions/qa-applicability.md`; if no verified finding holds within the assigned lens, return `{}`. Remain read-only. Return
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
