# Refactor

Preserve each caller's accepted inputs, outputs, errors and defaults. An extracted helper needs the interface its current callers require; a common name does not authorize a common policy.

1. Identify the shared operation and differing policies once. Keep nonshared validation, public exceptions and I/O with their existing owners. Make differing policies required arguments at migrated call sites unless a requested/existing API specifies defaults. Choose one preserving interface and use it throughout the change.
2. Select missing caller cases once from source/tests, using existing fixtures. Add the cases together per file, then run one passing baseline before source edits. Call existing APIs, with original observed values/errors; do not import the proposed helper. Keep those assertions unchanged after extraction. A failing baseline must be resolved first.
3. Move the common implementation, imports and calls together. Check uncertain dynamic/external references before deleting code; preserve external compatibility. Do not broaden the helper merely to absorb caller-specific policy.
4. Run the retained assertions and required checks, including relevant error/boundary cases. Review the diff and new files once, reusing inspected content. Correct unexplained mismatches in the implementation; report authorized behavior changes as a scope change.

Report the outcome, recorded checks and limits directly. Settled interface choices stay settled unless a check fails or a real caller requirement appears. Do not reconsider defaults or imagined direct-call signatures while preparing the final answer. Extra probes need a named caller gap and assertions against retained evidence; unasserted sample printouts do not verify preservation. Skip duplicate checks, cosmetic follow-ups and known-bad experiments after completion.
