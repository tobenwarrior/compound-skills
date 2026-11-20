# Verify

Choose evidence that could falsify the success claim. Run it against the final artifact and inspect the result yourself, including delegated work.

- Features: exercise the caller's successful path, meaningful failure cases, and relevant integration surface.
- Bugs: show the original reproduction failing before and passing after the correction.
- Refactors: compare observable behavior against the recorded baseline.
- Performance: compare the same workload and explain what the measurement includes.
- Documentation or packaging: inspect the actual paths, examples, links, and supported host format.

Tests should detect an incorrect observable result while surviving a behavior-preserving internal rewrite. Derive expected values from the contract, not from the implementation being tested. Select one check for each required behavior. Reuse passing regression/caller assertions; add output demonstrations or randomized probes only for a named coverage gap. Match effort to the change; inspect reversible wording edits.

Use the project's documented commands, working directory and environment. On a setup failure, inspect the captured error and correct its cause before retrying; do not rotate through runners or optional tools. Keep the exit status and enough failure output to diagnose the result. For long output, capture it once and inspect the log instead of rerunning solely to change verbosity. Run checks selected for the changed surface and project requirements against the final artifact. Reuse passing results while the checked files, inputs and environment are unchanged; a commit or push alone does not require a rerun. Rerun after relevant edits or to resolve failures. Inspect the diff and status for unintended files. Report the outcome, checks and limits once, concisely. A passing check establishes only the artifact and surface it exercised.

## UI and UX

Default to a screenshot walkthrough for UI changes and UI/UX verification in ChatGPT and Codex when the current harness can render the app, capture screenshots, and open them for inspection. In Claude Code and other harnesses, use the project's usual checks and add a screenshot walkthrough when explicitly requested and supported. Follow project and host permissions. If a required visual capability is unavailable, continue with the available checks and state which visual coverage remains unverified.

1. Walk the changed flow as a user in the running app with representative data. Cover the relevant viewports, themes, and states. When a before-and-after comparison helps, capture both at the same viewport and state.
2. Capture and open screenshots of the affected states. Inspect layout, hierarchy, readability, clipping, and whether the next action is clear. Use applicable browser assertions to check interactions, overflow, and runtime errors.
3. Fix confirmed issues within scope and recapture the affected states on the final build. Report what you saw and what the interaction checks covered. Share useful screenshots when supported and safe to share.
