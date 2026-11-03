# Refactor

Name the behavior to preserve and structure to simplify. Pin observed outputs, errors and input differences at each public caller in existing tests; add only missing cases. Run one passing baseline with those cases before source edits, using the documented command and environment. Reuse the same assertions afterwards; resolve setup before retrying.

Before removing apparently dead code, inspect configuration, generated references, dynamic entry points and external consumers.

Apply each cohesive unit in one patch when supported, including imports, helper removal and caller migration; keep dependent checks ordered. Migrate internal API callers and remove obsolete implementations together; respect external compatibility.

Compare caller behavior with the baseline, including errors and boundary cases. Treat unexplained differential mismatches as regressions; never narrow inputs to make equivalence pass. Type checks do not establish equivalence. Caller-specific parameters encode observed requirements; preserve those differences even when one common algorithm seems cleaner. Ask only if behavior cannot be preserved. Report behavior changes as scope changes.

A standalone probe, randomized comparison or helper test needs a named behavior not covered by caller tests. Reuse baseline cases instead of rebuilding a second oracle. Do not introduce known-bad code to reconfirm covered behavior. Finish when caller comparisons and required checks pass.
