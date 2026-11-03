# Refactor

Consolidation preserves public caller outputs, errors and accepted inputs unless changes are explicit. Choose the smallest interface serving actual callers; resolve differences once through parameters. Hypothetical tests or alternate signatures do not define requirements.

Reuse assertions/fixtures; add only missing caller cases before one passing baseline with the documented command and environment. Skip probes when source/tests settle expectations; otherwise observe the unresolved case and reuse it before and after. Preserve necessary differential baselines; do not recreate old implementations after editing.

Migrate helper, imports and callers together. Expand only for concrete caller/configuration/compatibility dependencies. Check dynamic/external references before deleting code with an uncertain role; preserve external compatibility.

Compare error and boundary cases. Unexplained mismatches are regressions; never narrow inputs to pass. Type checks do not establish equivalence. Ask only if behavior cannot be preserved; report behavior changes as a scope change.

Review behavior/scope and run required checks. Fix concrete defects; otherwise finish. Extra probes/helper tests need an uncovered case or project requirement. Do not introduce known-bad code to reconfirm covered cases. Exclude speculative APIs and unrequested cosmetic follow-ups after checks pass.
