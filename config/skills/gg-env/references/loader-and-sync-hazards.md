# Loader and sync discovery hazards

## Global-canonical family, multi-root discovery
OpenCode scans skills from multiple roots: the repository `.opencode/skills/` and the user `~/.config/opencode/skills/`, plus sibling `.claude` and `.agents` roots at both scopes. A skill is discovered wherever a directory contains a `SKILL.md`. Under the global-only ownership model, a globally applicable skill (the generic `gg-*` family and the shared infrastructure skills such as `agent-tool-permissions` and `skill-loading-system`) has exactly ONE canonical home: the user skills root (`~/.config/opencode/skills/`). The repository `.opencode/skills/` root is reserved for genuinely repo-local skills (`ggt-conventions` and other repository-specific skills).

## Same-name loading is nondeterministic
When the same skill name exists in more than one root, loader arrival order is nondeterministic, so a same-name copy must never be used as an override. Under global-only ownership no skill name may appear at two distinct real roots at all — a duplicate is a collision to remove, not a preference to resolve. If you must customize, fork under a new name rather than shadowing a canonical skill.

## Isolation escape hatches
When discovery behavior needs to be diagnosed in this environment, these environment variables disable categories of external skills (diagnostic use only):
- `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` — disable Claude Code skill discovery.
- `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` — disable external skill discovery.

These are diagnostic escape hatches, not a replacement for correct skill placement.

## One canonical owner, no mirror
Generic family skills and shared infrastructure are canonical only under the user skills root; there is no repository mirror to keep in sync. A same-name copy anywhere else is a placement error to delete, not drift to reconcile. Retain only genuinely repo-local skills under `.opencode/skills/`. The only shared-table propagation that remains is the `gg-env` credentials-and-visibility table copied byte-identically to its global consumers (`gg-actions`, `gg-artifacts`, `gg-docs`).

https://opencode.ai/docs/skills/ | checked 2026-08-28 | re-check on OpenCode skill-discovery change
