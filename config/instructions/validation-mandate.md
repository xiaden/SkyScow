# Validation Mandate

This file is the canonical owner of the always-applicable validation core and of how verification
burden is selected from observable surfaces. It does not restate the evidence vocabulary; that
vocabulary is owned by `/home/opencode/.config/opencode/skills/ci-lint-test-gates/SKILL.md`.

## Always-applicable core (exactly eight items)

These eight items apply to every task, regardless of changed surface:

1. **Preserve explicit user requirements.** Implement what was actually asked for; do not trade it
   away for convenience or for a broader refactor.
2. **Stay in scope.** Change only what the task authorizes; note unrelated findings instead of
   fixing them.
3. **Never fabricate validation or completion evidence.** Do not report validation, inspection, or
   completion that did not happen.
4. **Prefer repository-defined validation and conventions.** Use the commands, checks, and
   conventions the repository actually defines over generic or remembered defaults.
5. **Surface failures, unavailable checks, and deferred evidence explicitly.** Report them; never
   replace them with silence or an unqualified success claim.
6. **Do not introduce new regressions.** Do not knowingly break behavior that worked before.
7. **Preserve existing security invariants.** Do not weaken sandboxing, integrity checks, or other
   existing security guarantees.
8. **Escalate when required correctness cannot be demonstrated.** If the required correctness
   cannot be shown, say so and escalate rather than claiming success.

Everything *else* in this file is conditional. It is selected from the observable changed surface
and the repository's actual capabilities — never applied as universal doctrine.

## Observable triggers only

No rule may key on subjective discretion. Phrases such as "if simple", "when appropriate",
"low-risk", or "enough context" must not be used as trigger conditions. Every conditional rule in
this file keys on an observable repository or task fact: which files changed, which repository
commands exist, what tooling and environments are actually available, and what the repository's own
policy defines.

## Surface-selected verification

The verification burden is chosen from the observable changed surface and the repository's actual
capabilities, not applied as a fixed universal sequence. Repository-native commands and conventions
outrank any generic command list.

| Observable changed surface | Evidence to produce |
| --- | --- |
| Pure logic | Targeted unit/regression test plus the repository's configured type/lint checks |
| Producer/consumer or module boundary | Contract or integration test plus real-caller evidence |
| Service, startup, or runtime | Build plus smoke test plus service-health check |
| Docker, shell, seccomp, or supervision | `docker build` plus shell validation plus container startup plus seccomp/process checks |
| Browser-visible | Browser/E2E test only when a real browser surface and browser tooling exist |

Constraints:

- Do not require a cross-browser matrix without a browser surface.
- Never invent or run a command the repository does not define.

## Repository-native verification

Do not assume a project test suite exists and do not default to generic commands such as `npm
test`. The verification burden is selected from the changed surface and the repository's real
capabilities, and repository-defined commands take precedence over any generic list. When the
repository defines no test or lint command for the changed surface, report that fact and use the
repository-native checks that do exist.

## Baseline and causality

A validation failure must be classified by observable causality before it is acted on or dismissed.
A failure may not be dismissed as pre-existing without evidence.

- **`INTRODUCED`** — the failure was introduced by this task's changes. Repair it before reporting
  DONE.
- **`BLOCKING_BASELINE`** — a pre-existing failure that blocks demonstrating the correctness of
  this task's changes. Repair it only as far as needed to establish correctness; if that cannot be
  done, report BLOCKED.
- **`UNRELATED_BASELINE`** — a pre-existing failure unrelated to this task's correctness. Report it
  and do not silently expand scope to fix it.
- **`UNKNOWN_CAUSALITY`** — causality cannot yet be determined. Investigate enough to classify it,
  or report the uncertainty explicitly.

## Coverage

Coverage remains a diagnostic when the repository supports it. A repository-defined coverage
threshold or verification policy must be honored when present. This mandate prescribes no universal
coverage percentage.

## Evidence vocabulary (owned elsewhere)

Report gate evidence using the canonical vocabulary defined by
`/home/opencode/.config/opencode/skills/ci-lint-test-gates/SKILL.md`: `LOCAL_PASS`, `LOCAL_UNAVAILABLE`, `CI_DEFERRED`,
`CI_PASS`. Do not introduce a competing taxonomy, and do not relabel unavailable or deferred
evidence as passing. That file remains the sole owner of the definitions.

## Unavailable and deferred work

A required-but-unavailable skill, tool, command, or environment must be reported as unavailable
rather than improvised around. Deferred validation and residual risk must be exposed explicitly.

## Evidence honesty

- Never claim a test passed unless it actually ran and passed.
- Never claim something was inspected if it was not.
- Distinguish unavailable evidence from passing evidence.
- Distinguish local evidence from CI evidence; do not present one as the other.
- Expose deferred validation and residual risk explicitly.
- Preserve existing security invariants under ordinary correctness review — correctness review
  includes confirming they are not weakened.

## Completion report

Failures, unavailable checks, and deferred evidence are surfaced explicitly in the completion
report, using the `ci-lint-test-gates` labels defined by
`/home/opencode/.config/opencode/skills/ci-lint-test-gates/SKILL.md`. They are never replaced by silence or an unqualified
success claim.

## Audit and verify the diff

- **Audit** — review the diff for unintended changes, scope creep, and leftover debug code.
- **Verify** — review the diff against the surface-to-evidence table above and report which
  evidence was actually produced.

"Should work" is not verification.
