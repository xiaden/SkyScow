---
name: ci-lint-test-gates
description: Define the evidence labels and tracked-location rules for local, deferred, and continuous-integration lint and test gates.
---

# CI, Lint, and Test Gate Evidence

This global skill owns the evidence vocabulary for CI, lint, and test gates. It is global-only infrastructure: repository-specific skills may invoke these rules, but no repository mirror is required. Keep this canonical copy detailed and do not create a divergent same-name repository copy.

## Evidence location

Commit required gate manifests and evidence to tracked repository paths. Never use the gitignored `artifacts/` tree as the authoritative location. A static YAML file, manifest, or test configuration is not evidence that a gate ran.

## Required labels

Preserve exactly one of these labels when reporting a gate:

- `LOCAL_PASS`: the local lint or test command actually ran and passed.
- `LOCAL_UNAVAILABLE`: the local command could not run because its required tool, dependency, service, or environment was unavailable.
- `CI_DEFERRED`: execution is intentionally delegated to CI and no CI result is available yet.
- `CI_PASS`: tracked CI evidence proves that the configured gate ran and passed.

## Integrity rules

1. Do not relabel `LOCAL_UNAVAILABLE` or `CI_DEFERRED` as `CI_PASS`.
2. Do not call an unwired test, an unexecuted command, or a manifest-only check `CI_PASS`.
3. Preserve the producing gate's label through handoffs and summaries.
4. Report the command, workflow, or evidence source that supports `LOCAL_PASS` or `CI_PASS`.
5. If evidence is missing, retain `CI_DEFERRED` or report the gate as unavailable; never silently infer success.
