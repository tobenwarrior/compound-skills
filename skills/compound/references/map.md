# Code maps

Use focused files and import neighbors to choose source reads; confirm behavior and callers in source/tests. Missing entries prove nothing: coverage is bounded and import links are not a complete call graph. Use native search for reported limits. Skip mapping for activation-only requests, non-code work, and questions answerable from a supplied snippet.

`code_map.py --no-cache` scans in memory without cache, repository writes, or a service. For write-authorized tasks, omit it to start or reuse the shared local service. Its index reuses unchanged file metadata and checks additions, edits, and deletions. If service startup fails, the helper reports it and falls back to a bounded local scan.

## Live viewer

Use the [map utility](../../map/SKILL.md) for a visual request. It starts or reuses one loopback service at `http://127.0.0.1:43127/` and opens the registered project. `COMPOUND_MAP_PORT` can select another port. Opening again reuses the index; it creates no HTML snapshot. While visible, the page checks for changes and refreshes metadata incrementally. It does not restructure source code.

Map viewing authorizes local cache and service startup only, without repository edits or onboarding cleanup. The helper's `status` and `stop` subcommands inspect or stop this shared service. It runs until stopped or the machine session ends; the next coding or map request starts it again. It scans only repositories registered by those requests, not every project at login.

Python 3.11+ and Git are required. The service uses the standard library, with no extra dependency, provider call, database, or filesystem watcher. Python and JavaScript/TypeScript receive structural outlines and local import links; other recognized source files have limited metadata. Large repositories open as folder groups; search or selection shows up to 240 nearby files and 8,000 links. The inspector uses all indexed relationships. Ordinary non-code exclusions appear under index coverage; scan failures and limits remain visible warnings. Confirm unresolved or dynamic imports with native search.

Metadata and service state live in Compound's user cache outside the repository. Source bodies are not cached or served. The listener accepts local requests only and serves the bundled UI and registered metadata, not arbitrary files. Summaries read by the agent enter normal chat context. Keep generated maps out of commits.
