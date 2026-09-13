# Authorized repository-review pilot checklist

Use this checklist only for a deliberately authorized, disposable repository owned by the operator. The normal safe operation remains `report` or `dry-run`; a pilot is optional and must not be represented as successful without recorded evidence.

## Before enablement

- [ ] The operator has explicitly approved this exact pilot target, run, mode, and bounded action caps.
- [ ] The target is disposable, owned by the authenticated operator, and contains no production secrets or sensitive data.
- [ ] The credential is verified as a fine-grained token scoped to only this repository, with the minimum metadata/contents read and intended issue or advisory permission; the credential value is never printed or passed to reviewers.
- [ ] The direct GitHub CLI/provider capability and API version are probed and verified before any write path is considered.
- [ ] The six canonical push files pass the byte-preservation gate, conformance passes, and offline validators pass.

## Review and bounded proposal

- [ ] Run the complete review in `report` mode first and retain its result as operator evidence.
- [ ] Run `dry-run` for the exact same target/run confirmation; inspect findings, labels, dedupe, stale checks, security route, caps, and uncertainty.
- [ ] Confirm that hidden reviewers are read-only, credential-free, provider-free, return one raw JSON value, and remain confined to the whole-tree contract.
- [ ] Set explicit low per-run finding/action caps and stop on any provider ambiguity, rate limit, stale result, missing label, or unauthorized security route.

## Optional submit and reconciliation

- [ ] Reconfirm operator approval immediately before `submit`; credentials alone are not authorization.
- [ ] Reconcile every outcome from the provider, including created, skipped, blocked, stale, rate-limited, partial, and unknown writes. Do not blindly retry an ambiguous write.
- [ ] Confirm security findings used only the private advisory/reporting route when ownership and authorization were independently verified; otherwise confirm **Review Prior to Submitting** and no public fallback.
- [ ] Record target, run ID, resolved SHA, caps, provider probe, dry-run output, submit authorization, provider outcomes, and cleanup status without secrets.

## Deliberate enablement decision

- [ ] The operator explicitly chooses whether to enable or disable future submit use after reviewing the evidence.
- [ ] Rollback is report mode or removal of submit authorization only; do not delete or reopen issues/advisories, mutate push state, add scheduling, or retain a review baseline.

No live pilot is implied by this checklist. In the absence of operator-supplied approval and evidence, report the pilot as skipped.
