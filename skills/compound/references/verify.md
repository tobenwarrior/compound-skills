# Verify

Choose evidence that could falsify the success claim. Run it against the final artifact and inspect the result yourself, including delegated work.

- Features: exercise the caller's successful path, meaningful failure cases, and relevant integration surface.
- Bugs: show the original reproduction failing before and passing after the correction.
- Refactors: compare observable behavior against the recorded baseline.
- Performance: compare the same workload and explain what the measurement includes.
- Documentation or packaging: inspect the actual paths, examples, links, and supported host format.

Tests should detect an incorrect observable result while surviving a behavior-preserving internal rewrite. Derive expected values from the contract, not from the implementation being tested. Match verification effort to the change; a reversible wording edit needs inspection, not a new test suite.

Run relevant checks against the final artifact. Reuse passing results while the checked files, inputs and environment are unchanged; a commit or push alone does not require a rerun. Rerun after relevant edits or to resolve failures. Inspect the diff and status for unintended files. Report the outcome, checks and limits once, concisely. A passing check establishes only the artifact and surface it exercised.
