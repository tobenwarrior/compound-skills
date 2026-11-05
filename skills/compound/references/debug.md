# Debug

Capture a concrete failing input, expected result, actual result, and execution surface. Add and run the regression in the nearest test that can express the failure before exploring dependencies, history, or alternative fixes. Use the project test runner before probing interpreters or dependencies. If it fails to start, diagnose that error in its own environment before retrying. Use the same environment for necessary probes. For Python tests and imports, set `PYTHONDONTWRITEBYTECODE=1`. Expand output or inspect more source only for a question that could change the fix. If the failure is intermittent, record conditions and instrument the narrowest uncertain boundary within the authorized environment.

Form competing hypotheses and run checks that distinguish them. Follow the first incorrect state or effect back to its cause. A guard is appropriate when it handles a legitimate domain state; otherwise it may hide a broken invariant.

Confirm the regression fails on the reported behavior. Reuse existing fixtures and make the smallest causal correction. For split paths, test the required property directly. One operation's success does not prove another's preconditions. Cover supported input categories and equivalent values across paths in both orders. Remove instrumentation and changes whose hypothesis was refuted.

Verify the correction on the same surface. If the final suite includes the regression, its passing result verifies the fix. Go straight to that suite and the diff check. Run a separate check only for a specific gap or project requirement. Reuse that result while checked inputs and environment are unchanged. If the original surface is unavailable, report the narrower evidence and unresolved limitation instead of declaring the defect gone.
