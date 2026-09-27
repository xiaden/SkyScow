# Tissue integration

SkyScow ships the resident-side OpenCode integration for [Tissue](https://github.com/xiaden/tissue) from the pinned `vendor/tissue` git submodule:

- `plugin/tissue-moderation.ts` is installed as the global `tissue-moderation` plugin.
- `agents/tissue-triage.md` and `agents/tissue-resolve.md` are installed as Tissue's agents.
- The exact upstream commit is pinned by the `vendor/tissue` gitlink. Update the submodule deliberately when changing the integration.

The Dockerfile copies these files into SkyScow's shipped configuration before generating `bootstrap-manifest.tsv`. The SkyScow bootstrap is the sole owner of the resident-side files under `/home/opencode/.config/opencode/plugins` and `/home/opencode/.config/opencode/agents`.

## Controller boundary

SkyScow does **not** bundle Tissue's controller, CLI, SQLite state, worktree manager, or s6 service. The controller remains a separate Tissue deployment and connects to a resident OpenCode service. This preserves the failure-domain and persistence boundaries defined by Tissue.

Run the Tissue controller from its own repository/image and provide its required runtime contract, including:

- an independently running OpenCode endpoint and its authentication settings;
- a writable persistent `TISSUE_STATE_DIR` for SQLite, WAL, routing, and logs;
- a writable persistent `TISSUE_SESSION_REGISTRY_DIR` shared with the resident OpenCode process;
- a `TISSUE_WORKTREE_ROOT` mounted at the same absolute path for the controller and OpenCode;
- authenticated GitHub CLI access through `/usr/bin/gh`.

The shipped plugin is inert until Tissue creates a managed `ses_*` marker in the session registry. Its moderation load beacon is kept outside SkyScow's reconciled OpenCode configuration tree.

## Installation ownership

Do not run `tissue install-plugin` or `tissue install-agents` against a SkyScow resident. Those commands target the same global OpenCode directories owned and reconciled by SkyScow's bootstrap. Update the `vendor/tissue` submodule and rebuild the image instead.

The Tissue submodule is used only as the source for the resident plugin and agents. SkyScow does not copy or maintain a second adapted implementation of those upstream files.
