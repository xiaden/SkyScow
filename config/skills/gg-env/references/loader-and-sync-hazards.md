# Loader and sync discovery hazards

## Dual repository/global discovery
OpenCode scans skills from multiple roots: the repository `.opencode/skills/` and the user `~/.config/opencode/skills/`, plus sibling `.claude` and `.agents` roots at both scopes. A skill is discovered wherever a directory contains a `SKILL.md`.

## Same-name loading is nondeterministic
When the same skill name exists in more than one root, loader arrival order is nondeterministic, so same-name must never be used as an override. Only byte-identical mirrors may share a name; a divergent copy is a collision, not a preference. If you must customize, fork under a new name rather than shadowing a generic skill with different bytes.

## Isolation escape hatches
When discovery behavior needs to be diagnosed in this environment, these environment variables disable categories of external skills (diagnostic use only):
- `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` — disable Claude Code skill discovery.
- `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` — disable external skill discovery.

These are diagnostic escape hatches, not a replacement for correct skill placement.

## Sync and mirror contract
Generic family skills are repository-canonical and mirrored byte-identically to the user root. A mismatch between the canonical and mirror copies is a sync error to fix, not a customization opportunity. Never create divergent same-name copies.

https://opencode.ai/docs/skills/ | checked 2026-08-28 | re-check on OpenCode skill-discovery change
