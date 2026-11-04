# Review

Read the diff first and compare it with the intended behavior. When the diff establishes the trigger and impact, report from it. Read callers and tests to settle specific gaps in the evidence. Bug-fix reproduction steps apply only when implementing a fix.

Look for correctness failures, unsupported assumptions, concurrency or retry problems, and design that makes a local change unsafe elsewhere. Review reader effort: unnecessary layers, synchronized duplicate state, unclear ownership, and misleading names. Apply project conventions without turning preferences into defects.

Use independent reviewers for distinct uncertainties when the host supports it and the benefit warrants the cost. Give them the same intent and artifact, then verify findings yourself. Reviewer agreement is supporting evidence, not proof.

Return actionable findings with location, triggering condition, impact, and supporting evidence. Separate confirmed defects, unresolved questions, and optional improvements. Dismiss a false positive with a concrete reason. Use a permitted check when source cannot settle a specific finding or when project instructions or the user require a check. Prefer a documented test that covers the question. Before preparing a reproduction, identify which finding the result could change. Confirm permission before creating scratch files or running the check. A review remains read-only unless changes are authorized. After an execution or probe-setup denial, continue from source; do not write alternate scripts, switch runners, relocate artifacts or retry the blocked operation. State the verification limit once. Do not include unexecuted repro scripts or full patches unless requested.
