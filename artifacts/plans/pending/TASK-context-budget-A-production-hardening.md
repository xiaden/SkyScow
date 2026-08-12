# Task: Production-Harden the Context Budget Tool

## Problem Statement

`config/tools/common/tools/context_budget.py` is an in-progress, untracked tool
that is already registered by `config/plugins/tools.ts`. Its current implementation
reads policy from agent frontmatter, imports private tokenizer helpers from
`context_tokens.py`, detects phases with a regex, and has no dedicated tests or
fixtures. Production hardening must make the tool deterministic, safe, compact,
and independently verifiable without changing the existing `context_tokens`
counting contract.

The implementation must accept files-only input, safely inspect agent model
frontmatter while using DeepSeek V4 Flash 0731 as the fallback tokenizer, load
policy from `config/agent-context-budgets.yaml` rather than unsafe custom agent
frontmatter, use shared tokenizer helpers instead of private imports, and use
`plan_md.parse_plan` for explicit phases and per-phase validation. The fixed
policy is worker phase 48,000; manager operational 96,000; physical 128,000;
worker/fixer return 8,000; QA return 12,000; phase reread 8,000; correction
multiplier 3. Output must remain compact, and tests/fixtures must cover the
production boundaries.

**Prerequisite:** The currently uncommitted `context_budget.py`, registration,
and related agent/skill edits are change-in-flight. Preserve the committed
`context_tokens.py` tokenizer artifact/download behavior, and do not use the
unreliable `llmtokens` package. There is no existing CONTRACTS.md, test suite,
or fixture directory for this tool.

## Context Budget

```yaml
context_budget:
  model: DS_V4_F_0731
  operational_limit: 96000
  physical_limit: 128000
  known_context_tokens: 30051
  worker_phase_limit: 48000
  worker_return_tokens: 8000
  fixer_return_tokens: 8000
  qa_return_tokens: 12000
  phase_reread_tokens: 8000
  correction_multiplier: 3
  worst_case_total_tokens: 450051
  status: PHYSICAL_LIMIT_EXCEEDED
```

`known_context_tokens` and `worst_case_total_tokens` must be recalculated by
the implementing worker after the completed plan and fixture ranges are known;
the values above are explicit metadata placeholders, not estimates disguised as
measurements.

## Dependencies

- `config/tools/common/tools/context_tokens.py` — existing tokenizer loading,
  verification, assembly, and weighting behavior to expose through shared
  helpers.
- `config/tools/common/helpers/plan_md.py` — `parse_plan` and its structured
  phase/step representation.
- `config/tools/common/tools/plan_read.py` — reference behavior for plan lookup,
  parsing, phase selection, and compact structured output.
- `config/plugins/tools.ts` — existing `context_budget` registration and
  files-only argument schema.
- `config/agents/*.md` — model frontmatter remains readable metadata only; policy
  must not be inferred from custom frontmatter.

## Phases

### Phase 1: Establish the authoritative policy and shared tokenizer contract

- [x] Add `config/agent-context-budgets.yaml` as the single shipped policy source with exactly the fixed worker, manager, physical, worker/fixer return, QA return, phase reread, and correction multiplier values, plus schema validation and safe defaults for missing or malformed policy.
    **Notes:** config/agent-context-budgets.yaml created at repo config/ with operator comments; exact fixed values (48000/96000/128000/8000/8000/12000/8000/3). budget_policy.load_policy validates integers, merges partial files onto DEFAULT_POLICY, falls back to defaults with diagnostics on absent/malformed/non-mapping files — never raises.
- [x] Extract stable, documented tokenizer-loading, model-selection, section-assembly, and weighted-token helpers from `context_tokens.py` into a shared helper boundary, update both token tools to use that boundary, and remove `context_budget.py` imports of private implementation names.
    **Notes:** tokenizer_helpers.py extracted as shared public boundary (constants, assemble_sections, read_subsection, weighted_tokens, sha256, verified_path, download_tokenizer, resolve_tokenizer_path, load_tokenizers). context_tokens.py rewritten to import from helpers (private _read_subsection removed); context_budget.py imports only public names. No private cross-tool imports remain.
- [x] Define and document the callable contracts used by later phases, including safe model-to-tokenizer mapping, policy loading, explicit phase validation, and compact result construction; confirm no implementation contract depends on custom agent `context_budget` frontmatter.
    **Notes:** Callable contracts documented in module docstrings: budget_policy (frontmatter_model, select_tokenizer_model, load_policy, policy_candidates), tokenizer_helpers, context_budget module docstring lists contracts for files-only input, frontmatter-only model metadata, structured plan parsing, fixed policy, compact output. No contract depends on custom agent context_budget frontmatter.

### Phase 2: Harden files-only input and model/tokenizer selection

- [x] Restrict `context_budget` to a non-empty `files` array of validated file/range objects, reject raw text, unknown top-level input, malformed entries, traversal, invalid ranges, unreadable files, and unsupported encodings with stable compact error objects.
    **Notes:** Files-only validation: non-list/empty -> invalid_files; non-dict entries, unsupported keys beyond {path,start_line,end_line}, traversal, missing, directories -> invalid_file; non-positive/bool/inverted ranges -> invalid_line_range; range beyond EOF or binary/undecodable -> read_error. All compact JSON, bounded messages (<=303 chars).
- [x] Read agent model metadata only from the supported frontmatter block of supplied agent markdown files, never execute or interpret arbitrary markdown/config content, and ignore malformed or untrusted model values.
    **Notes:** frontmatter_model reads ONLY the leading --- frontmatter block of supplied agent .md files, allows a trusted charset, ignores malformed/untrusted values (quoted, spaces). Agent files detected by 'agents' path segment + .md suffix. No markdown interpretation beyond the frontmatter block.
- [x] Implement an allowlisted model-to-tokenizer mapping that selects a supported tokenizer only for known model identifiers and deterministically falls back to `DS_V4_F_0731` for unknown, missing, mixed, or unsafe model metadata; preserve the verified tokenizer path/cache behavior from `context_tokens.py`.
    **Notes:** MODEL_TOKENIZER_MAP allowlist {'omniroute/opencode-go/deepseek-v4-flash': 'DS_V4_F_0731'}. select_tokenizer_model: unknown/missing models don't vote; single known wins; multiple distinct known -> deterministic DS_V4_F_0731 fallback. Verified system tokenizer path/cache/download behavior preserved via tokenizer_helpers (regression-tested).
- [x] Keep the existing weighted source-token calculation semantics while returning only the selected model, measured counts, policy projections, and bounded diagnostics required by the tool contract.
    **Notes:** weighted_tokens semantics preserved (ceil(src*(1+0.03*(n-1)+0.015*(f-1)))) from original contract. Output returns only selected model + measured{source,weighted} + planning + policy block; bounded titles (120) and messages; no raw content emission.

### Phase 3: Use structured plan parsing and per-phase validation

- [x] Detect plan files from supplied paths and parse their complete content through `plan_md.parse_plan` rather than counting phase headings with a regex; preserve explicit phase numbers, titles, steps, and completion state.
    **Notes:** Plan files detected by 'plans' path segment + .md suffix; FULL content parsed via plan_md.parse_plan (requested range ignored for parsing — documented). Explicit phase numbers/titles/steps/completion preserved via Phase/Step dataclasses; phases aggregated across multiple plan files with per-entry 'plan' basename.
- [x] Validate explicit phases for sequential numbering, valid plan structure, and usable flat steps, returning a compact parse/validation error when the plan is malformed instead of silently estimating from heading text.
    **Notes:** _validate_explicit_phases: numbers must equal range(1..n) (else plan_validation 'sequential'), every phase must have >=1 flat step (else plan_validation 'no steps'). parse_plan ValueError/ImportError -> compact plan_parse error with bounded message. Malformed plans never silently counted by regex.
- [x] Produce per-phase measurements and validation metadata, including phase token scope and whether each phase is independently within the 48,000 worker limit; use the worker-limit fallback only when no explicit plan phases are present.
    **Notes:** _analyze_plan measures each explicit phase's content slice (raw_lines between heading lines) with the selected tokenizer; detail entries carry plan/number/title(bounded)/tokens/within_worker_limit/steps/complete_steps. Worker-limit fallback max(1,ceil(weighted/48000)) applied only when no explicit phases (explicit_phases flag).
- [x] Compute normal and worst-case manager projections from the fixed policy, phase reread allowance, worker/fixer and QA return envelopes, and correction multiplier 3; classify results as `VALID`, `SPLIT_REQUIRED`, or `PHYSICAL_LIMIT_EXCEEDED` using 96,000 and 128,000 limits.
    **Notes:** _build_planning: overhead = phase_reread + worker_return + qa_return (28000); normal = weighted + phases*overhead; worst = weighted + phases*overhead*correction_multiplier; minimum_phases = max(1,ceil(weighted/worker)); minimum_plans = max(1,ceil(worst/operational)); status: worst>128000 -> PHYSICAL_LIMIT_EXCEEDED, worst>96000 -> SPLIT_REQUIRED, else VALID. Boundary-tested (==operational VALID, ==physical SPLIT_REQUIRED).

### Phase 4: Deliver compact integration output and configuration coverage

- [x] Align the Python tool result and `config/plugins/tools.ts` registration so the public input remains files-only and the response is compact JSON with stable keys, bounded error messages, no source dumps, and no policy/frontmatter leakage.
    **Notes:** tools.ts context_budget registration: files-only args (array of fileRangeSchema), description updated to reflect frontmatter-only model selection, structured plan parsing, per-phase worker checks, shipped policy projections. Tool output compact JSON with stable keys (model/measured/planning/policy), no source dumps, no policy/frontmatter leakage (tested via SECRET_MARKER_KNOWN omission).
- [x] Ensure policy loading resolves the repository-shipped `config/agent-context-budgets.yaml` safely from the workspace/image layout, has deterministic behavior when absent or malformed, and does not reintroduce policy parsing from agent frontmatter.
    **Notes:** load_policy resolution order: env HOLYCODE_CONTEXT_BUDGET_POLICY -> workspace_root/config/agent-context-budgets.yaml -> ~/.config/opencode/agent-context-budgets.yaml -> built-in defaults; diagnostics['source'] = env/workspace/home/defaults. Absent/malformed/non-mapping -> defaults + warnings, never raises (explicit missing policy_path raises ValueError). No policy parsing from agent frontmatter anywhere.
- [x] Add concise operator/developer documentation or inline contract comments for fallback selection, policy ownership, explicit phase parsing, and output status meanings without duplicating implementation logic.
    **Notes:** Documentation: policy yaml operator comments (ownership, value meanings, fallback semantics); context_budget module docstring contract section (files-only, frontmatter-only models, structured parsing, fixed policy, compact output); budget_policy + tokenizer_helpers docstrings for fallback selection and policy resolution; tools.ts description. No implementation logic duplicated in docs.

### Phase 5: Add fixtures, tests, and production verification

- [x] Create focused fixtures for normal plans, multi-phase plans, malformed/non-sequential plans, agent frontmatter with known/unknown/missing models, policy config variants, invalid file inputs, and oversized plans.
    **Notes:** fixtures/ created: plans/{normal_single_phase,multi_phase,non_sequential,malformed_phase,empty_phase,oversized(10 phases),no_phases}.md; agents/{known_model,unknown_model,no_model,malformed_model,mixed_a,mixed_b}.md; policy/{valid,partial,malformed,tiny,non_mapping}.yaml; inputs/app.py. Workspace builder + fixture copier helpers in tests/conftest.py.
- [x] Add tests covering files-only validation, path/range errors, safe model mapping and DeepSeek fallback, tokenizer helper reuse, YAML policy loading/default rejection behavior, `parse_plan` phase extraction and per-phase validation, projection/status calculations, compact output, and secret/source omission.
    **Notes:** 96 tests across 4 modules: files-only validation, path/range errors, model mapping + fallback (incl. mixed via monkeypatched map), tokenizer helper reuse + no private imports (inspect.getsource check), YAML policy loading/default rejection, parse_plan phase extraction + per-phase validation, projection/status arithmetic + boundaries, compact output stable keys + secret/source omission + bounded errors (<=303). All pass in ~10s.
- [x] Add regression coverage proving `context_tokens` retains its existing o200k/DeepSeek counts, weighting formula, verified system artifact preference, and verified cache/download fallback after helper extraction.
    **Notes:** test_context_tokens.py regression: exact o200k + DS_V4_F_0731 counts via module-scoped real-tokenizer fixture, weighting formula (1.0 and 1.03 cases), verified system artifact preference, verified cache reuse without download, download-failure SHA rejection. test_tokenizer_helpers.py covers resolution order + download verification. context_tokens counting contract unchanged.
- [x] Run the repository-appropriate Python tests, focused diagnostics, syntax/format checks, and `git diff --check`; verify the changed-file set contains only the planned tool/helper/config/registration/test/fixture/documentation files and does not modify unrelated user changes.
    **Notes:** Verified: pytest 96/96 pass; py_compile OK on all 9 python files; git diff --check clean; AFT diagnostics 0 errors/0 warnings (duplicates only in pre-existing plan_md/adr_md); stdin __main__ contract smoke-tested for both tools; changed-file set = plan md, policy yaml, 2 new helpers, 2 rewritten/updated tools (context_budget, context_tokens), tools.ts registration, tests/ — pre-existing in-flight agent/skill edits untouched. Plan Context Budget recalculated: known 30051, worst 450051, PHYSICAL_LIMIT_EXCEEDED.

## Acceptance Criteria

- The public tool accepts only a non-empty files input and returns stable compact JSON errors for invalid or unsafe inputs; it never accepts raw context text or exposes source dumps/secrets.
- Model metadata is read only from agent frontmatter, model selection is allowlisted, and unknown/missing/mixed models always use the verified `DS_V4_F_0731` fallback.
- `config/agent-context-budgets.yaml` owns policy; agent frontmatter cannot override limits. The fixed values are worker 48k, manager 96k, physical 128k, worker/fixer return 8k, QA return 12k, phase reread 8k, and correction multiplier 3.
- Tokenizer and weighting behavior is shared through public/stable helpers, with no private cross-tool imports, and existing `context_tokens` behavior remains regression-tested.
- Explicit plan phases are parsed with `plan_md.parse_plan`, validated per phase, and used in projections; malformed phases fail clearly rather than being silently counted by regex.
- Normal/worst-case projections correctly apply phase rereads, return budgets, correction multiplier, worker limit, manager operational limit, and physical ceiling, with deterministic status classification.
- Fixtures and automated tests cover success, fallback, malformed input, malformed plans, policy errors, boundary limits, and compact output; focused diagnostics and `git diff --check` pass.

## References

- `config/tools/common/tools/context_budget.py`
- `config/tools/common/tools/context_tokens.py`
- `config/tools/common/helpers/plan_md.py`
- `config/tools/common/tools/plan_read.py`
- `config/plugins/tools.ts`
- `artifacts/logs/nyx.log.jsonl` (tokenizer fallback decision)
- `artifacts/logs/support-researcher.log.jsonl` (tokenizer/package research)
- `artifacts/logs/support-pattern-enforcer.log.jsonl` (permission/pattern coverage)
