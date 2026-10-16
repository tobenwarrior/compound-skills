# Compound Skills

Work directly on `main` in this checkout. Commit and push verified checkpoints. Create branches or worktrees only when the owner explicitly requests them.

Maintain two public skills: `compound` is the shared engineering core and `map` is a thin utility that reuses its guidance and shared runtime. Keep host command directories consolidated; do not add extra discoverable workflows. Put conditional detail in the responsible reference and consolidate overlap before adding files. For owner-requested skill integrations or model compaction in this repository, read [CONTRIBUTING.md](CONTRIBUTING.md); this maintainer workflow is not a plugin command.

Stage intended changes, then run `python3 scripts/check.py --json` before completing them. The checker measures package structure and context cost; behavioral evaluation still needs representative tasks and actual outputs.

Keep tests in ignored `tests/` locally. Plans, reports, transcripts, source dumps, credentials, private paths and generated artifacts do not belong in commits. Preserve source pins and required notices. Attribute commits to the human author without AI co-author trailers.
