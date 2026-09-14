---
description: Correct a set of issues through risk-based investigation, planning, implementation, QA review, and verified commits
---

For each issue listed below, task Nyx to execute the complete `/correct` workflow independently. Do not batch unrelated issues into one implementation plan or one commit.

Each issue must:

1. Preserve its complete request as an authoritative requirement ledger, including severity, affected files, problem description, recommended action, and expected behavior when supplied.
2. Review relevant ADRs/ASRs, durable logs, git history, applicable skills/instructions, definitions and callers, tests, and the full state lifecycle before editing.
3. Verify ownership of the listed files and trace related caches, persistence, startup/reload, facades, contracts, error handling, and concurrency concerns.
4. Be classified as local/low-risk, standard, or high-risk. Authentication, authorization, credentials, sessions, persistence deletion/migration, cache invalidation, startup/recovery, concurrency, cross-layer changes, public contracts, and security-sensitive data are high-risk.
5. Route multi-layer or high-risk work through `Exec-Planner` and then `Exec-Manager`. Escalate architectural mismatches, unclear requirements, missing contracts, migration needs, contradictory ADRs/ASRs, and unresolved failure semantics instead of making silent shortcuts.
6. Convert expected behavior into executable invariants and tests, including negative, persistence, restart/recovery, concurrency, and partial-failure cases where applicable.
7. Run targeted and broader relevant tests and linting using the project virtual environment, review the complete diff, and preserve unrelated concurrent changes.
8. Pass the mandatory full `QA-Reviewer` gate after all implementation phases; independent correctness review is always required. Invoke the security review, test, and documentation analysis lenses only when their canonical triggers in `/home/opencode/.config/opencode/instructions/qa-applicability.md` are met; do not restate those triggers here. Fix MINOR findings and rerun QA; stop for planning gaps, requirement drift, architectural issues, or critical findings.
9. Commit only after QA explicitly passes and verification is complete. Stage every file modified for that issue, including QA corrections, but never use repository-wide staging (`git add .`, `git add -A`, or `git commit -a`).

ISSUES:

$ARGUMENTS
