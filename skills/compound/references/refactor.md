# Refactor

Name the behavior to preserve and structure to simplify. Inspect existing tests; add cases only for uncovered caller differences, reusing fixtures. Establish one passing baseline including those cases before source edits with the documented command and environment. Resolve setup first; reuse evidence while inputs are unchanged.

Before removing apparently dead code, inspect configuration, generated references, dynamic entry points and external consumers.

Apply each cohesive unit in one patch when supported, including imports, helper removal and caller migration; keep dependent checks ordered. Migrate internal API callers and remove obsolete implementations together; respect external compatibility.

Compare behavior against the baseline, including error and boundary cases. Reuse caller tests; add helper tests only for otherwise uncovered behavior. Type checks alone do not establish equivalence. Preserve differing caller behavior through parameters when needed; ask only if no behavior-preserving path exists. Report bugs or new behavior as a scope change.

Once caller comparisons and required project checks pass, finish. Do not temporarily introduce a known-bad implementation or add duplicate helper tests just to reconfirm covered behavior. Additional experiments need a specific unresolved coverage question or an explicit user/project requirement.
