# Refactor

Name the behavior to preserve and structure to simplify. Inspect existing tests; add cases only for uncovered caller differences, reusing fixtures. Establish one passing baseline including those cases before source edits with the documented command and environment. Resolve setup first; reuse evidence while inputs are unchanged.

Before removing apparently dead code, inspect configuration, generated references, dynamic entry points and external consumers.

Apply each cohesive unit in one patch when supported, including imports, helper removal and caller migration; keep dependent checks ordered. Migrate internal API callers and remove obsolete implementations together; respect external compatibility.

Compare caller behavior with the baseline, including errors and boundary cases. Treat unexplained differential mismatches as regressions; never narrow inputs to make equivalence pass. Reuse caller tests; add helper tests only for uncovered behavior. Type checks do not establish equivalence. Parameterize differing callers when needed; ask only if behavior cannot be preserved. Report behavior changes as scope changes.

Do not introduce a known-bad implementation or duplicate helper tests just to reconfirm covered behavior. Stop when caller comparisons and required project checks pass.
