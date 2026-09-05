# Control cache, artifacts, and concurrency

Manage build performance, data sharing between jobs, and run overlap.

## Cache
Use `actions/cache` to persist dependency and build outputs across runs. Choose cache keys that match your inputs so a stale cache is not restored. Cache contents are not validated; treat restored data as untrusted where it influences a build. Current major: actions/cache v6 (as of 2026-08-28; Node 24 runtime, ESM).

## Artifacts
Use `actions/upload-artifact` and `actions/download-artifact` to share files between jobs and across runs. Current majors (as of 2026-08-28): upload-artifact v7, download-artifact v8. Artifacts have retention limits; set `retention-days` explicitly when a specific period is required. v3 and below of the artifact actions are deprecated.

## Concurrency
Use a `concurrency` group to cancel or queue overlapping runs of the same workflow, keyed by context (for example the branch or the caller). Concurrency groups prevent duplicate runs from racing and wasting quota.

## Guidance
- Cache and artifact content is untrusted input to later steps; validate before use.
- Keep retention short unless you need longer.
- Use concurrency groups to bound cost and avoid duplicate runs.

## Boundary
Retention and billing figures are volatile; recheck limits before relying on them. This reference covers the operations surface; the general security and least-privilege principle is in gg-env.

https://github.com/actions/cache | checked 2026-08-28 | re-check on actions/cache major change
https://github.com/actions/upload-artifact | checked 2026-08-28 | re-check on upload-artifact major change
https://github.com/actions/download-artifact | checked 2026-08-28 | re-check on download-artifact major change
https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-concurrency | checked 2026-08-28 | re-check on concurrency behavior change
https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts | checked 2026-08-28 | re-check on artifact retention-limit change
