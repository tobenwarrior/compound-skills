# Refactor

Preserve each public caller's outputs, errors and accepted inputs unless changes are explicit.

1. Read affected code/callers and identify observable differences once. Choose the first simple parameterization preserving them, keeping existing algorithms. Stop comparing signatures or guessing evaluator requirements once actual callers are covered.
2. Before source edits, reuse assertions/fixtures and add only missing caller cases for those differences; run one passing baseline with the documented command and environment. Probe only a specific expectation source/tests cannot settle; retain baseline evidence.
3. Next, migrate the shared helper, imports and callers together. Preserve differing behaviors in the first patch. Check uncertain dynamic/external references before deleting code; preserve external compatibility.
4. Compare error and boundary cases with the baseline, review the diff and run required checks. Unexplained mismatches are regressions; never narrow inputs to pass. Type checks do not establish equivalence. Ask only when behavior cannot be preserved; report changes as a scope change.

Then finish. Reopen design/tests only for new evidence of a concrete defect, an uncovered caller behavior or a project requirement. Avoid late cosmetic edits, overlapping compile/import checks and repeated status/review rounds; required checks still apply. Reuse unchanged passing assertions. Do not introduce known-bad code to reconfirm covered cases or recreate old implementations after editing.
