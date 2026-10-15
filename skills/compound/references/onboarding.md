# First-use repository onboarding

Run one bounded inspection and cleanup pass before a repository's first write-authorized engineering task. This is part of the engineering preference, not a background process. Explicit read-only scope, project instructions, and user opt-outs take priority. Read-only tasks do not claim or update onboarding state.

Use the installed [state helper](../scripts/onboarding.py) with the intended repository root. It resolves a canonical checkout identity and shares completion across Codex, Cursor, and Claude Code through machine-local state. It writes no project marker. A completed record suppresses automatic onboarding, not later reviews or explicitly requested cleanup.

## One pass

1. Read project instructions, repository layout, build/test configuration, and current Git status. Record pre-existing changed and untracked paths. Do not change those paths as part of cleanup; the requested task retains its normal authorization.
2. Claim the pass atomically:

   ```bash
   python3 <installed-skill-dir>/scripts/onboarding.py claim --repo <repo-root>
   ```

   Read the JSON. If already completed or another session owns the lease, continue the user's task without a duplicate pass. Retain a granted token for completion or release. For a sandbox write denial, request the host's normal approval for that state operation and retry once. Respect denials and managed policy. If storage remains unavailable, report that once and skip cleanup; do not move state into the project or loosen permissions.
3. Read [repository hygiene](repo-hygiene.md) and run its read-only audit with `--json --no-baseline`. Inspect actual responsibilities, callers, configuration, and existing checks. Audit warnings are candidates, not proof that a file is useless or that an architecture needs splitting.
4. Apply high-confidence, behavior-preserving cleanup in a reviewable diff. Examples include missing ignore entries for generated files the project uses and small simplifications supported by callers and tests. Preserve all pre-existing changed and untracked paths, including generated artifacts. Preserve user work, source, documentation, dependencies, and unknown artifacts. Defer broad redesign, migrations, dependency upgrades, public-contract changes, and speculative deletion. Keep a short actionable backlog instead of expanding the task indefinitely.
5. Verify cleanup with the relevant existing checks and inspect the diff, checking recorded changed and untracked paths remain unchanged by cleanup. An audit that produces findings (exit `0` or `1`) ran successfully; findings may remain as backlog. Complete only after inspection and cleanup verification:

   ```bash
   python3 <installed-skill-dir>/scripts/onboarding.py complete --repo <repo-root> --token <claim-token>
   ```

   Findings that cannot be safely fixed can remain in the reported backlog; completion is not a claim that the repository is perfect. If the audit cannot run, reports a configuration error (exit `2`), or cleanup cannot be verified, release the claim so a later task can retry:

   ```bash
   python3 <installed-skill-dir>/scripts/onboarding.py release --repo <repo-root> --token <claim-token>
   ```

Report what was inspected, changed, verified, and deferred, then continue the user's requested task. Do not stage, commit, push, install dependencies, or change external services merely because onboarding ran. Those actions retain their normal authorization. The helper only tracks state; it never audits or cleans the repository itself.
