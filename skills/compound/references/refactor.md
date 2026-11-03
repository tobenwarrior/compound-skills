# Refactor

An extraction shares code while preserving each caller's accepted inputs, outputs, errors and defaults. A common helper name does not authorize a common policy.

1. Read the affected callers/tests and identify their differences once. Keep existing algorithms and pass only policies actual callers need; do not design defaults or signatures for imagined consumers.
2. Add only missing characterization cases through existing caller APIs, using original observed results. Do not import the proposed helper before it exists. Run one passing baseline after these additions, before source edits. A failing baseline must be resolved first; it is not a bug-fix red test. Keep those assertions and expected values unchanged through the refactor.
3. Move the helper, imports and callers together, preserving every characterized difference in the first patch. Check uncertain dynamic/external references before deleting code; preserve external compatibility.
4. Run the same caller assertions and required checks. Review the diff and new files once; reuse unchanged content already inspected. Unexplained mismatches are regressions. Correct the implementation, not the baseline expectations; report any authorized behavior change as a scope change.

Then report the result, checks and limits. Reopen only for a concrete defect or requirement. Extra helper tests or standalone probes need caller behavior the existing assertions cannot establish. Reuse fixtures rather than duplicating them in print scripts. Do not add unused options/defaults, polish, or known-bad experiments after checks pass.
