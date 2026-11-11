# Compound Skills

Work directly on `main` in this checkout. Commit and push verified checkpoints. Create branches or worktrees only when the owner explicitly requests them.

Maintain five public entrypoints: shared engineering core `compound`, map utility `map`, and thin shortcuts `setup`, `setup-global`, and `status-global`. Shortcuts delegate to the core; do not duplicate workflows or add separate host command directories. Put conditional detail in the responsible reference and consolidate overlap before adding files. For owner-requested skill integrations or model compaction in this repository, read [CONTRIBUTING.md](CONTRIBUTING.md); this maintainer workflow is not a plugin command.

Stage intended changes, then run `python3 scripts/check.py --json` before completing them. The checker measures package structure and context cost; behavioral evaluation still needs representative tasks and actual outputs.

Track portable release tests in `bench/ci/`. Keep trace-dependent tests in ignored `tests/`. Commit the benchmark harness, tasks and fixture data in `bench/`. Keep `bench/work/` and `bench/results/` ignored. Compare guidance or script changes with it before shipping them ([bench/README.md](bench/README.md)). Plans, reports, transcripts, source dumps, credentials, private paths and generated artifacts do not belong in commits. Preserve source pins and required notices. Attribute commits to the human author without AI co-author trailers.

For map UI work, keep tooltips to two visible lines at supported viewports and zoom levels. Use shorter copy or move detail into an optional view. Verify the rendered tooltips.
