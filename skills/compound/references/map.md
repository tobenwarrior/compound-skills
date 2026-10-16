# Code maps

`--no-cache` scans in memory without writing map, cache, or repository files. For write-authorized tasks, omit it to reuse unchanged metadata in the external cache. Skip mapping for activation-only requests, non-code work, and questions answerable from a supplied snippet. Use focused files and dependency neighbors to choose source reads; confirm behavior and callers in source/tests. Missing entries prove nothing: coverage is bounded and import links are not a complete call graph. Use native search for reported limits. Re-run after moving files or changing imports; fall back to native tools if unavailable.

## Visual view

Map viewing authorizes only user-cache output, with no repository edits or onboarding cleanup. For `compound map` or a request to see the map:

```bash
python3 -B <installed-skill-dir>/scripts/code_map.py --repo <repo-root> --format html --open
```

Use `--query` to focus it or `--refresh` to rebuild metadata. Omit `--open` when opening is unwanted or unavailable. The command opens a self-contained local HTML snapshot in the default browser. A supported host preview can open the returned file instead of `--open`. Report the actual result and file path. Rerun to update the view.

Python 3.11+ and Git are required. Metadata and views overwrite user-cache files outside the repository. The helper uses no watcher, new dependency, or provider call; source bodies are not cached. Summaries read by the agent enter its normal chat context. Keep generated maps out of commits.
