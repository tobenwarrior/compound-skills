# Review

Review the diff against its intended behavior and affected contract. Trace changed values through relevant callers, state transitions, errors and observable effects; expand only to resolve a concrete uncertainty. Examine tests as claims about that contract. Bug-fix reproduction steps apply only when implementing a fix.

Look for correctness failures, unsupported assumptions, concurrency or retry problems, and design that makes a local change unsafe elsewhere. Review reader effort: unnecessary layers, synchronized duplicate state, unclear ownership, and misleading names. Apply project conventions without turning preferences into defects.

Use independent reviewers for distinct uncertainties when the host supports it and the benefit warrants the cost. Give them the same intent and artifact, then verify findings yourself. Reviewer agreement is supporting evidence, not proof.

Return actionable findings with location, triggering condition, impact, and supporting evidence. Separate confirmed defects, unresolved questions, and optional improvements. Dismiss a false positive with a concrete reason. A review remains read-only unless changes are authorized. Execute a check only when execution is permitted and either a finding remains unresolved or project instructions require the check. After an execution or probe-setup denial, continue from source; do not write alternate scripts, switch runners, relocate artifacts or retry the blocked operation. State the verification limit once. Do not include unexecuted repro scripts or full patches unless requested.
