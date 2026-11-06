# Changelog

Notable changes to Compound Skills, newest first. Every change is in the Git history; benchmark numbers come from [bench/](bench/README.md) and are explained in the [README](README.md#benchmark).

## 0.16.76 (2026-11-07)

- Route Python file, symbol, and line requests to a batched lookup that verifies the enclosing definitions from source.
- Save a project solution and refresh its index in one command. Search prefers exact matches and can recover related notes from matching tags.
- Shorten saved guidance. Review a compact diff, retain existing regression cases, and batch the final suite with the scoped diff check.

## 0.16.75 (2026-11-06)

- Deliver the updated skill through normal plugin upgrades. Refresh saved defaults after updating to load the revised rule.
- Try the project test runner first, batch related edits, and finish after required checks pass. Deliver source-backed review findings promptly.
- Report strict benchmark savings separately from cost ties and keep each review finding attached to its evidence.

## 0.16.74 (2026-11-05)

- Route local bug fixes through the saved rule when local conventions are clear. Shorten the core skill and use relevant source ranges and concise check output. [Saved Flask trace](bench/README.md#consecutive-upstream-flask-fixes)

## 0.16.73 (2026-11-05)

- Skip line-by-line matching in exact symbol lookup when the source lacks the literal query. Five offline Flask and Django lookups returned identical results and took 2–8% less median wall time.

## 0.16.72 (2026-11-05)

- Start known bug fixes by writing and running the nearest regression before opening dependency internals, history or alternative implementations. [Saved Flask traces](bench/README.md#consecutive-upstream-flask-fixes)

## 0.16.71 (2026-11-05)

- Skip map focus ranking during exact symbol lookup when the selected inventory fits, avoiding an extra content scan before lexical occurrence search.

## 0.16.70 (2026-11-05)

- Make the native read prerequisite explicit for each edit target in the saved routing rule. [Saved Flask traces](bench/README.md#consecutive-upstream-flask-fixes)

## 0.16.69 (2026-11-05)

- Refresh change labels when Git status exceeds the map freshness limit.

## 0.16.68 (2026-11-05)

- Refresh an open code map after the local service restarts, even when the first index revision matches the last displayed revision.

## 0.16.67 (2026-11-05)

- Reuse safe path validation for repeated references to the same URI within a language-server response.

## 0.16.66 (2026-11-05)

- Reuse one Git inventory for semantic lookup source validation and result filtering.

## 0.16.65 (2026-11-05)

- End bare `compound contribute` after source-only orientation, before map or engineering startup.

## 0.16.64 (2026-11-05)

- Split ASCII identifiers directly from source bytes during code-map ranking. The local replay matched results and read counts, with 15–26% lower median ranking CPU across ten pinned Flask and Django queries. [Ranking profile](bench/README.md#profile-local-map-queries)

## 0.16.63 (2026-11-05)

- Add `compound contribute` for existing repositories. Learn local conventions and the rationale for relevant decisions, then use the smallest patch that fits the project. Without a task, provide read-only orientation.

## 0.16.62 (2026-11-04)

- Keep more ranked paths in compact code-map summaries. At a 1,300-character limit, a focused query on the pinned Flask fixture now shows both the session implementation and its existing test.

## 0.16.61 (2026-11-04)

- Turn a known bug into its failing regression before further investigation. After the fix, run the full suite and check the diff, then finish. Reserve extra probes for a specific evidence gap or project requirement.

## 0.16.60 (2026-11-04)

- Give test files priority for explicit test searches. Keep mixed queries such as production behavior alongside `TestCase` focused on both paths. [Pinned navigation replay](bench/README.md#multi-step-navigation-preflight)

## 0.16.59 (2026-11-04)

- Keep more complete ranked paths visible in truncated map summaries. [Pinned navigation replay](bench/README.md#multi-step-navigation-preflight)

## 0.16.58 (2026-11-04)

- Direct agents from focused map results to scoped search and nearby source lines. [Saved navigation trace](bench/README.md#multi-step-navigation-preflight)

## 0.16.57 (2026-11-04)

- Reuse test-path classification and skip scoring metadata for files with no matching query terms. [Warm query profile](bench/README.md#profile-local-map-queries)

## 0.16.56 (2026-11-04)

- Show up to eight declarations in an exact-file agent summary, including declarations whose names differ from the filename. [Exact-path replay](bench/README.md#exact-path-agent-summaries)

## 0.16.55 (2026-11-04)

- Use the failing regression as the bug-fix baseline and the full suite as confirmation in the default rule. This covers the same regression without a separate passing run when the full suite includes it. [Saved Flask verification](bench/README.md#consecutive-upstream-flask-fixes)

## 0.16.54 (2026-11-04)

- Recognize `ctx` in paths as a match for context and give implementation files a little more weight when a query does not ask for tests. [Pinned navigation replay](bench/README.md#multi-step-navigation-preflight)

## 0.16.53 (2026-11-04)

- Reuse the complete untracked inventory during live map freshness checks and avoid a second directory walk in Git status. [Warm query replay](bench/README.md#warm-map-query-work)

## 0.16.52 (2026-11-04)

- Start reviews from the diff. Use a reproduction only for a specific unresolved finding or a required check, with permission established before scratch setup. [Saved review replay](bench/README.md#source-first-review-trace-replay)

## 0.16.51 (2026-11-04)

- Show the indexed definition of a bare, unambiguous symbol directly in CLI summaries. [Pinned replay](bench/README.md#exact-symbol-agent-summaries)

## 0.16.50 (2026-11-04)

- Prioritize exact structured symbol definitions in code-map results and summaries, while preserving explicit test searches. [Pinned navigation replay](bench/README.md#multi-step-navigation-preflight)

## 0.16.49 (2026-11-04)

- Check Claude Code's saved map allow entries on request. Report missing entries for the current install separately from routing status, and leave user settings untouched.

## 0.16.48 (2026-11-04)

- Match lowercase queries such as `methodview` to the complete mixed-case symbol name in ranking and summaries. [Local replay](bench/README.md#lowercase-symbol-queries)

## 0.16.47 (2026-11-04)

- Give the exact requested file first use of the inventory and source read budgets in an in-process code map. [Local regression replay](bench/README.md#exact-path-agent-summaries)

## 0.16.46 (2026-11-04)

- Use the editor's required native Read before edits. Keep the failing regression and final suite, and reserve extra checks for project requirements or gaps in evidence. [Saved Flask traces](bench/README.md#consecutive-upstream-flask-fixes)

## 0.16.45 (2026-11-04)

- Give bug fixes a targeted failing regression before source edits and a full suite afterward. Keep the pre-edit baseline instruction with scoped extractions and give Python checks a concrete way to avoid bytecode cleanup. [Saved verification replay](bench/README.md#direct-routing-and-edit-reads)

## 0.16.44 (2026-11-04)

- Keep tracked files navigable when Git cannot list untracked files. Show partial coverage, preserve the full disk cache, and recheck the inventory on the next explicit query. [Recovery replay](bench/README.md#warm-map-query-work)

## 0.16.43 (2026-11-04)

- Preserve the existing code-map cache and live index when Git cannot list the checkout. After a simulated failure, the unchanged Flask and Django checkouts needed 0 and 1 file parses to recover, versus 125 and 3,497 before. [Recovery replay](bench/README.md#warm-map-query-work)

## 0.16.42 (2026-11-04)

- Keep the bounded missing-keyword lookup when a query adds repository context. The three qualified Flask, Click and Packaging probes now show their target while keeping their three leading paths. [Replay and controls](bench/README.md#mixed-keyword-lookups)

## 0.16.41 (2026-11-04)

- Reuse file classification and symbol-name terms across map queries. On pinned Django, median ranking CPU fell 17–32% across five warm queries with identical ranked paths and source reads. [Local ranking measurements](bench/README.md#profile-local-map-queries)

## 0.16.40 (2026-11-04)

- Refresh existing project or global routing after an upgrade with `compound refresh` or `compound refresh global`. Status points stale installations to the new action. Refresh leaves setup and repository assessment for explicit setup requests.

## 0.16.39 (2026-11-04)

- Use the indexed file directly for exact-path text in read-only, no-cache, and service fallback commands. Keep the index coverage and import hints.

## 0.16.38 (2026-11-04)

- Route scoped extractions with known callers and policies through the saved rule. Reserve the full skill for refactors that need discovery or behavior decisions.
- Read edit targets with the editor's required read tool on the first pass and batch independent reads and checks. [Saved trace evidence](bench/README.md#direct-routing-and-edit-reads).

## 0.16.37 (2026-11-04)

- Keep scoped extraction searches inside the checkout and start from named files and callers. Expand discovery for concrete dependencies required by the task.
- Two saved refactors spent five requests on searches outside their checkouts without finding new implementation evidence. [Trace evidence](bench/README.md#checkout-scope-in-saved-refactors).

## 0.16.36 (2026-11-04)

- Ask reviews to report findings once source establishes the trigger and impact. Use a permitted probe only for a specific evidence gap or required check. Keep the saved rule within 100 words.
- In four saved Compound Flask reviews, 11 Bash calls were denied after the first denial and five scratch writes or edits still occurred. Both modes found all three defects. [Trace replay](bench/README.md#source-first-review-trace-replay).

## 0.16.35 (2026-11-04)

- Keep audit content and worktree scans within the selected checkout. In-checkout links still work, and audit configuration that points outside reports a configuration error.
- Reuse one checkout handle for file reads where descriptor-relative opens are supported. The pinned Django audit returned the same 101 findings.

## 0.16.34 (2026-11-04)

- Return the named file and its import hints in exact-path agent summaries. The warm service reads the indexed row directly.
- On 50 exact paths from pinned Flask and Django, ranking source probes fell from 2,500 to zero and emitted text shrank 64.9% in total. [Offline replay](bench/README.md#exact-path-agent-summaries).

## 0.16.33 (2026-11-04)

- Keep Unicode identifier parts in focused map queries, including single CJK characters and combining marks. Match normalized spellings in paths, symbol outlines and bounded source scans.
- Five local Unicode queries found their intended file and 48 existing controls kept their focus and probe counts. [Offline checks](bench/README.md#unicode-map-queries).

## 0.16.32 (2026-11-04)

- Route scoped extractions with known callers and behavior through the saved rule. Keep the caller baseline and final checks, and finish after diff review. Load the full guide for broader refactors. Run `setup-global` again to refresh saved rules.
- The saved Dispatchkit refactor passed the independent cumulative grader before its final helper signature rewrite. [Offline trace replay](bench/README.md#scoped-refactor-replay).

## 0.16.31 (2026-11-04)

- Validate required manifests, marketplaces, skill entrypoints, rules and local links against staged files. Continue scanning untracked public files for accidental disclosure and validate unpacked archives from their contents.

## 0.16.30 (2026-11-04)

- Reject invalid JSON in the map cache, runtime record and project registry. Reparse source when saved metadata cannot be decoded, and enforce read caps on actual cache and runtime bytes.
- Verify that an installed map can open again after all three state files are invalid. The read-only query reparses source while preserving the saved file. [Install smoke test](bench/README.md#installed-plugin-smoke-test).

## 0.16.29 (2026-11-04)

- Global status checks the apps selected by default setup. A configured Codex-only or Claude-only installation reports enabled. Use `--host all` to inspect every supported host.
- Add a keyless install smoke test that installs a Git archive with both CLIs, exercises saved routing and opens the local viewer with Python 3.11. [Install smoke test](bench/README.md#installed-plugin-smoke-test).

## 0.16.28 (2026-11-04)

- Let agent map requests resume when the index check finishes instead of sleeping between status requests. Keep a bounded wait and signal completion after queued refreshes finish.
- Fourteen warm queries on pinned Flask and Django checkouts each used one status request and returned byte-identical summaries. [Latency replay](bench/README.md#index-completion-wait).

## 0.16.27 (2026-11-04)

- Keep agent text and JSON queries separate from the saved viewer focus. Preserve the viewer query when an agent starts the service again.
- Six distinct warm text queries on pinned Flask and Django snapshots produced identical summaries. Registry replacements fell from six to zero, and explicit viewer updates still persisted. [Replay](bench/README.md#saved-viewer-focus).

## 0.16.26 (2026-11-04)

- Route global setup and status directly to the activation guide. A saved-guidance status check inspects map permissions only when asked.
- Group related source hunks into one patch when the editor supports it. A saved retry refactor's six replacements and one new file can be applied in one patch with byte-identical source. [Offline replay](bench/README.md#grouping-source-edits).

## 0.16.25 (2026-11-04)

- If one of two keywords has evidence, look for the missing keyword in up to 50 more files within the same byte budget. Stop at the first hit and preserve the first three results.
- The three selected mixed-keyword lookups on Flask, Click and packaging now show their target files. In the 36 commit-title controls, all focus lists stayed the same and 35 used the same number of source probes. [Replay and probe costs](bench/README.md#mixed-keyword-lookups).

## 0.16.24 (2026-11-04)

- Put exact repository-relative path queries first, including paths written with `./`. The requested file remains visible under a one-file response cap.
- In a replay on pinned Flask and Django checkouts, all 50 exact-path queries ranked their file first. The two topic controls kept the same ranking. [Replay](bench/README.md#exact-path-queries).

## 0.16.23 (2026-11-04)

- Reuse passing checks when inputs and environment are unchanged. Count the final bug suite as confirmation when it includes the regression, and rerun only unresolved parts of a combined refactor probe.
- Deliver the same 100-word guidance through generated rules, Cursor and chat activation. The default rule is 50 bytes shorter. [Saved examples](bench/README.md#reusing-final-checks).

## 0.16.22 (2026-11-04)

- Save global guidance before configuring optional map access. A denied or unavailable cache setting is reported separately, so it cannot prevent routing setup.
- Return a working local map URL when automatic browser launch fails. Open it manually without running the map command again.

## 0.16.21 (2026-11-04)

- Resolve the repository root without reading its file inventory in the map client or service. Index freshness checks still detect changes to the checkout.
- On pinned Flask and Django snapshots, three warm queries per repository each ran 6 Git subprocesses, down from 12, with byte-identical summaries. [Measurements](bench/README.md#warm-map-query-work).

## 0.16.20 (2026-11-04)

- Find PHP declarations written with mixed-case tags and keywords, or preceded by attributes on the same line. Keep declarations in PHP regions and ignore apparent symbols inside backtick strings.
- Refresh PHP entries from the previous map cache format while reusing other validated entries. Existing Python and other language outlines can stay warm after the upgrade.

## 0.16.19 (2026-11-04)

- Look past the first 50 candidates when a query has no lexical evidence. Promote source-only matches found within the remaining 8 MiB budget and a 200-file total cap. The same no-follow opener handles both passes.
- Four selected source-only queries on pinned Flask, Click and packaging snapshots now show their target paths. The three ordinary controls retain their focus and 50 source probes. The three no-hit controls use 92 to 125 probes and preserve their ranking. [Replay and source pins](bench/README.md#source-only-map-lookups).

## 0.16.18 (2026-11-04)

- Keep the first four focused candidates visible when long signatures or import lists would crowd them out and their paths fit. The compact fallback keeps whole paths and adds the best matching symbol when space permits.
- On 36 commit-parent replays, complete changed-file paths visible at 500 characters rose from 22 to 29 out of 41. The default 2,500-character budget showed 38 of 41 in both renders. Each pair used the same ranked map. [Replay and source pins](bench/README.md#focused-summary-coverage).

## 0.16.17 (2026-11-04)

- Recheck the original instruction text before applying project or global setup. When a target changes during preparation, stop and preserve the newer edit. Recheck each file before its replacement or removal and report any earlier updates if setup stops partway through.

## 0.16.16 (2026-11-04)

- Start with known files and keep searches inside the checkout. Use existing caller assertions to identify coverage gaps, add the missing cases, then run one baseline before source edits. Batch the helper and caller changes after that baseline.
- Prevent untracked test byproducts with supported options. The saved Dispatchkit refactor spent two requests checking and removing Python bytecode from earlier test runs. The same fixture tests pass with `python -B` and create no bytecode in a clean copy. Refresh saved project or global rules to pick up this instruction.
- The [saved work audit](bench/diagram_sources/work_review_dispatch_v01615.json) records the extra searches, early test run and cleanup alongside the measured cache and reasoning differences. These changes have offline checks. Model cost for 0.16.16 has yet to be measured.

## 0.16.15 (2026-11-04)

- Use one workflow guide for a behavior-preserving extraction. Read the matching guide with the initial source batch, and open Verify only for independent verification or a specific evidence gap. Retain the passing baseline, final caller checks and required project checks.
- Reuse sufficient caller tests. Batch additions for uncovered behavior and group independent final checks. In the saved 0.16.12 slug trace, one separate request opened Design after Refactor and Verify had already loaded. That request used 1,835 reasoning tokens. The saved charges remain intact. No new model runs measured the effect on total cost.

## 0.16.14 (2026-11-04)

- Rank each live JSON map response once, even when the transport limit requires progressively smaller projections. The projections share the same index snapshot, ranked candidates and lexical matches.
- On the pinned Django tree (`a05e16a`, 3,496 indexed files), the query `model query annotations` with a 2 MiB test cap returned identical JSON before and after. Ranking passes dropped from 5 to 1 and candidate source scans from 250 to 50. Median local process CPU time over five warm responses was 348 ms before and 128 ms after on macOS arm64 with Python 3.14.5. This measures response construction with a reduced cap. Model usage was not measured.

## 0.16.13 (2026-11-03)

- Extract the shared operation while leaving nonshared validation, public exceptions and I/O with their existing owners. Differing caller policies become required arguments unless an actual API contract specifies defaults, removing the need to invent a canonical helper default.
- Select missing caller cases once and apply additions together per file before the passing baseline. After the retained assertions and required review pass, report the recorded evidence without revisiting defaults or hypothetical direct-call signatures. Extra probes require caller assertions rather than sample printouts.
- Deliver the explicit-policy cue through project/global setup, Cursor and chat activation while keeping the routing rule at 100 words. Refresh saved rules with `setup` or `setup-global` after updating; no user configuration is changed by this release commit.
- The saved 0.16.12 completion trial remains 9.1% more Go allowance overall with both modes 3/3 correct. Its money task used 9 versus 6 requests and 12,483 versus 6,708 reasoning tokens. Offline caller checks validate the common-core extraction pattern; no new model runs establish fewer future calls or lower total cost. README benchmark claims and graphics are unchanged.

## 0.16.12 (2026-11-03)

- Shared-helper requests preserve each caller's behavior; extraction alone does not authorize standardizing their outputs or defaults. Project/global setup, Cursor and chat activation deliver the same clarification. Saved rules from earlier versions are flagged for refresh with `setup` or `setup-global`.
- Refactor characterization uses existing caller APIs and original observed results, passes before source edits, and retains its expected values. A test importing a proposed helper is not a valid pre-refactor baseline. Fix implementation mismatches rather than changing the baseline to agree with the rewrite.
- Obtain host-required current-turn read receipts before constructing edits. Reuse caller fixtures and inspected content; exclude unused helper defaults and duplicate print/probe verification once required checks pass.
- The saved 0.16.11 trial used 38 versus 29 requests, with one repair and 3/3 accepted tasks per mode, at 75.5% more Go allowance with Compound. Its trace review motivates these changes; no new model runs establish fewer future calls or lower total cost. README benchmark claims and graphics are unchanged.

## 0.16.11 (2026-11-03)

- Refactors preserve observed caller differences in the first patch. Choose one sufficient interface from source evidence, characterize missing caller behavior before the baseline, and proceed to implementation instead of comparing hypothetical APIs or evaluator expectations.
- Named-file work skips unrelated inventories/history. Passing caller assertions remain evidence; required checks remain, while cosmetic edits and overlapping check/review rounds need a concrete reason.
- Saved-step auditing reports reasoning tokens and native stop reasons, including billed responses that produce no tools. The saved 0.16.10 trial stopped at the shared response cap on its second Compound task; its completed first task also consumed more allowance than control, including control's repair. No new model runs validate these prompt changes or lower total cost; README benchmark claims and graphics are unchanged.

## 0.16.10 (2026-11-03)

- Bound instruction discovery and refactor decisions to supplied context, actual callers and concrete dependencies; exclude hidden-evaluation and parent-workspace searches.
- Put missing caller cases before one baseline. Reuse preserved baseline evidence, retain real behavior corrections, and stop unrequested polish after passing checks.
- Add an optional per-request saved-trace ledger with no-tool responses, unknown costs and duplicate/invalid meter validation. Record the 0.16.9 work review without new model runs or a savings claim.

## 0.16.9 (2026-11-03)

- Ground agent map suggestions in query evidence while preserving the full ranked JSON/viewer index. No-match queries recommend native search instead of unrelated files.
- Address extra work in saved Y Harness / DeepSeek traces: reuse caller assertions, preserve observed differences, honor edit prerequisites, avoid known-file map queries and require uncovered behavior for extra probes. The failing regression supplies bug reproduction; final-suite verification remains required.
- Add keyless saved-call auditing and navigation replay. No new model runs or total-cost savings claims.

## 0.16.8 (2026-11-03)

- Reuse one pinned repository directory for map-query candidate reads; preserve fresh content, no-follow checks and ranking. Add a keyless local profiler.
- Clarify refactor guidance for unexplained differential mismatches found in a saved workflow trace. No new model runs were made to validate this guidance.
- Present the main README comparisons as without/with Compound; retain plain-rule controls, historical versions and internal map measurements in the benchmark methodology.

## 0.16.7 (2026-11-02)

- Finish refactors once caller comparisons and required project checks pass. Additional mutation or helper experiments need a concrete unresolved coverage question or an explicit user/project requirement; do not temporarily introduce known-bad production code merely to reconfirm behavior already covered by caller assertions. The core completion rule uses the same stopping condition.
- Apply related imports, helper removal and caller migration as a cohesive patch when supported, preserving dependent check order. Reuse caller tests for before/after comparisons; add helper tests only for behavior they do not cover. Keep baseline, compatibility and scope requirements. Discovery and the always-on rule are unchanged.
- In saved `v016b` run `b891376b`, the agent introduced a known-bad retry policy, inspected it, then restored it after the new caller checks had already passed. Those three tool-bearing model messages motivate the stopping rule. No new model runs establish future call counts or lower billed cost.

## 0.16.6 (2026-11-02)

- Reproduce bug fixes through the failing regression test before source edits, using a separate probe only for unresolved uncertainty. The generated project/global rule and Cursor rule deliver this without loading the full skill; debugging and chat activation follow the same sequence. Keep the final full suite. The always-on rule is 731 UTF-8 bytes and 100 words (up from 697 bytes); the additional setup check targets avoided tool rounds, not a smaller prompt.
- Resolve documented test commands and environments before refactor baselines; inspect setup errors before retrying. Preserve check exit status and useful failure output, inspect captured logs rather than rerunning for verbosity, and select tools from project requirements and the changed surface.
- Saved `v016b` Compound refactors contain seven missing-pytest outputs and four missing-shopkit import outputs across 12 runs; the fixture README already supplied a dependency-free test command. Offline execution of that command runs all 13 original fixture tests. These are setup-waste targets, not measured savings from the revised prompts; no new model runs establish lower total cost.

## 0.16.5 (2026-11-02)

- Put source-first review routing in the always-on rule, which the saved reviews actually loaded. The rule grows from 633 to 697 UTF-8 bytes without loading another guide for ordinary reviews. Scope reproduction and regression-test steps to bug fixes. Execute during reviews only for unresolved findings when permitted, and stop after execution/probe setup is denied instead of writing alternate scripts or changing runners.
- Clarify PR authoring versus read-only PR reviews in discovery and routing. Explicit Compound reviews go directly to the review guide, skipping engineering startup; session activation uses the same review boundary.
- Saved `v016b` Compound reviews contain 14 blocked reproduction/setup attempts, five scratch writes/edits and one other tool error across 28 tool calls. The full skill was not loaded in any of the four reviews, so changing its review guide alone would not address this path. These observations motivate the prompt fix; no new model runs establish its future call count or billed savings.

## 0.16.4 (2026-11-02)

- Query summaries stop expanding unrelated symbol outlines. They retain ranked paths, query-matching declarations, import hints and coverage; unqueried overviews, JSON and the viewer retain full outlines. Offline replay of seven saved queries emits 12,200 bytes versus 15,741 with 0.16.3, with all twelve ranked paths still visible in every reply. No model runs or billed savings are claimed.
- Refactors establish one baseline after adding needed characterization cases, using existing test fixtures and the project command. Batch independent source lookups; start source reads narrowly and expand when needed. Keep the always-on rule at 633 bytes and defer optional navigation procedures out of the core, reducing it from 4,929 to 4,575 bytes.
- Add a saved-query replay tool that never executes recorded shell commands or fixture code and checks path, matching-declaration and metadata preservation. Original README benchmark comparisons and graphics remain intact.

## 0.16.3 (2026-11-02)

- Restore the README before the speculative cost section. Retain its original benchmark comparisons, measured costs and theme; remove the three added cost graphics and hypothetical repair-cost projections.
- Use supplied code, named files and current context before navigation. Query the map only for unknown files or dependencies and reuse it when unchanged. Use the project's test command and fixtures for refactor baselines; keep completion reports brief. Saved traces identify these overhead targets; no new model runs establish savings from this wording.
- Keep the no-map ablation compatible with both startup wordings. Saved cost comparisons now report only observed spend, accepted outcomes and whether the candidate meets a lower-cost/no-fewer-acceptances target. Remove recovery-cost scenarios.

## 0.16.2 (2026-11-02)

- Reanalyse saved side-by-side costs in the README: selective routing reduced bug-fix spend by 19.9% (Opus) and 17.9% (Sonnet) versus earlier Compound, with the same hidden-test pass counts. Show stock alongside both, cost per accepted refactor including unsuccessful spend, and explicit recovery-cost scenarios; do not claim measured lifetime savings.
- Extend `cost-audit` with matched-cohort comparisons. Reject different tasks, repetitions, pairing, settings or served models; keep unsuccessful, invalid and superseded spend and disclose missing usage. No new model or judge calls.
- Reuse guidance already in context and passing checks for unchanged checked files, inputs and environment. Commits and pushes alone do not invalidate evidence. Clarify that the full-suite rule belongs to reported bug fixes; other tasks use relevant checks. Report results concisely. These instruction changes have not been remeasured in model runs; saved rules update through `setup-global`.

## 0.16.1 (2026-11-02)

- Focus agent summaries on matching symbols while retaining two orientation symbols when needed. In 15 offline query pairs across five pinned repositories, full outlines contain 21.6% fewer UTF-8 bytes and the median complete file entries inside the same 2,500-character cap rises from 3 to 4. Ranking and JSON metadata are unchanged. These measurements do not establish lower model bills or improved task outcomes.

- Use the hey.trading cream-and-green theme across the live code map, source previews, mobile panels and every README graphic. Remove legacy host-skin overrides and dark chart variants; replace map screenshots with captures of the updated viewer on Flask. Benchmark data is unchanged.

- Shorten the saved always-on rule from 745 to 633 UTF-8 bytes while retaining its task routing, verification requirements and project overrides. Existing installations update it by running `setup-global` again; the recorded agent results still describe the earlier wording. No new agent runs or billed-cost savings are claimed.
- Add `bench.py cost-audit` to inspect saved agent spend and accepted outcomes without model calls, including recorded costs from invalid and superseded attempts.

## 0.16.0 (2026-11-01)

- **The bug-fix habits live in the always-on rule, and the skill loads only where it made the difference.** The rule now asks the agent itself to reproduce a reported bug, show a new test failing on the unfixed code before editing the source, run the full test suite after its last change, record current behavior with a test before a refactor, commit without AI co-author trailers or generated-by lines, and list what it ran and did not verify. The skill, with its guides and map query, loads for refactors, new features, performance work and pull requests; bug fixes, reviews and questions get only the rule. On 12 real bugs, the version before this one matched a plain five-sentence rule's fixes and habits at 1.26× (Claude Opus 5.5) and 1.38× (Claude Sonnet 5.5) the rule's cost. 0.16.0 fixed about as many bugs (38 of 48 runs, against 39), reproduced the bug and showed the failing test first in all 48 runs, ran the whole suite more often (46 of 48 runs, against 37), and cost 0.71× and 0.75× as much per fix as before: 1.09× and 1.14× stock. On three held-out refactors it again did all 30 runs correctly, where stock did 20 and the plain rule 19, at 1.07× the earlier version's cost. The longer rule and the skill list add about 510 tokens to each request. We chose this design after seeing the first runs, then measured it on the same tasks.
- **A second round ran every arm side by side.** Stock, the plain rule, the version before this one and 0.16.0 started together in every group, in Claude Code 2.1.312, with 1 run per real bug and 2 per held-out refactor, review and question. 0.16.0 did all 12 held-out refactor runs correctly, against 8 for stock and 6 for the rule, and its tests caught all 36 planted wrong refactors. On the 12 real bugs it fixed 19 of 24 runs, against 20 for stock and the rule, and reproduced the bug and showed the failing test first in 23. A fix cost 1.16× and 1.20× stock's cost and 0.80× the earlier version's; a refactor cost 1.65× and 1.56× stock's.
- **Reviews don't load the skill.** On a held-out review of a commit whose three helper merges each change one caller, 0.16.0 without the skill for reviews found as much as with it (the same score in all 10 pairs) and cost 0.75× as much (95% interval 0.72–0.78), which met a rule fixed before the run. Typing `compound` still loads the review guide.
- **One-chat mode follows the same routing.** Typing `compound` alone now applies the rule's habits to every task in that chat and the skill to refactors, new features, performance work and pull requests, as a saved setup does.
- **Fewer permission prompts.** The map query now runs as one plain command, and guides are read with the file tool. For Claude Code, `setup-global` adds allow rules for this install's map query and guides. In 12 held-out refactor runs in Claude Code's default permission mode with only those rules, the skill loaded, the map query ran and the guides were read without asking; 0.15.0's batched startup needed approval in 6 of 6 runs. The rules name Claude Code's own copy of the plugin, so run `setup-global` from Claude Code; from Codex or Cursor it now adds none and says so.
- **Setup touches only the apps you have.** `setup-global` without `--host` sets up only the apps whose configuration folder exists and names the ones it skipped; `--host all` keeps the old behavior.
- **Outdated rules are flagged.** `status` and `status-global` warn when a saved rule is from an earlier version and say to run setup again. Run `setup-global` again after updating: saved rules keep the 0.15.0 text until you do.
- **The map query stays.** Measured on its own against a rule fixed before the run: without it, the habits were the same, one fewer bug was fixed, and runs cost 0.98× as much (95% interval 0.95–1.004), which missed the bar for dropping it.
- **Benchmark:** a held-out review (`review-shopkit`); `--permissions setup`, `strict` and `helpers`; `+variant:nomap` and `+variant:noreview`; three held-out refactors on a second library, shopkit, frozen before any run. The judge's check that its quotes appear in the answer now ignores list markup and accepts quotes that elide words, and `judge --regrade` rechecks stored votes: two Sonnet reviews that named all three planted defects had scored 0 and 1 of 3 because a quote ran across two bullet points. The habit detector now times a source edit from when it was applied, and the check that a control arm never mentions Compound ignores Claude Code's own "compound command" permission message.

## 0.15.0 (2026-10-31)

- **Only what you asked for.** Coding work no longer runs the repository check-up before the first edit in a repository. The check-up could tidy or delete files nobody asked about, and in our first benchmark the agent mostly skipped it anyway and then reproduced the bug first less often in that session. It now runs only when you ask for `compound setup`, the skill tells the agent to change only what a request covers, and its startup is one step shorter. Tested side by side against 0.14.0: the same habits, at 1.02× the cost with Claude Opus 5.5 and 0.94× with Claude Sonnet 5.5 over 8 pairs per model; on a first bug fix in a repository it had not assessed, neither version's agent started the check-up (0 of 6 each), so the change removes a risk rather than a habit the agents had.
- **Measured against the alternatives.** The README now compares Compound with a five-sentence user rule asking for the same debugging habits and with Every's Compound Engineering and pstack on the same tasks, and adds eight real bugs from attrs, packaging and marshmallow, frozen before any run.
- **Tried and not shipped:** a shorter SKILL.md (29% fewer words) and Git guide (13% fewer). In 30 paired runs per model against 0.14.0 it kept every measured habit but did not lower cost (1.04× with Claude Opus 5.5, 95% interval 1.00–1.08; 0.99× with Claude Sonnet 5.5, 0.92–1.07), and Sonnet's five Flask reviews drew 10 incorrect statements from the judge against 2, so the 0.14.0 wording stays.
- **Benchmark:** other plugins can run as arms (`dir:` with `+rule:` and `+prefix:`), real bugs can be added without rebuilding the rest (`setup --real`), test ids that change with the clock are ignored, and grading compares test ids with sets (packaging's 62,000 tests took minutes per run). The reproduction detector now reads the short failure output of `pytest -q`, and a new habit, `failing_test_before_fix`, counts a failing test only when it ran before the first source edit: stock runs that showed one did so after fixing. `report` leaves out the first judged round's 40 complaints about a commit id the judge's copy got wrong, as the README does.

## 0.14.0 (2026-10-31)

- The always-on rule now asks agents to reproduce a reported bug and show its regression test failing before fixing it, and to pin current behavior with a test before a refactor. Against 0.13.0 in the same runs, Claude Sonnet 5.5 reproduced the bug first in 15 of 15 fixes instead of 1, and both Claude Opus 5.5 and Sonnet finished the refactor safely in 5 of 5 runs instead of 2 and 0, at 1.06× and 1.03× 0.13.0's cost.
- Rules saved by an earlier `setup` or `setup-global` keep the old text until you update and run it again.
- The benchmark is now tracked in `bench/`, with four real Flask and click bugs as harder tasks, so every guidance change can be measured before it ships.

## 0.13.0 (2026-10-31)

- The map query is now the first repository search of a coding task, before any other search, read, or edit.
- Focus ranking weighs distinctive query words in paths, symbols, and the text of the leading candidate files.

## 0.12.1 (2026-10-31)

- Code map viewer fixes for tablets and phones: the inspector docks beside the graph on tablets, drawers stay put when the window narrows, keyboard focus stays on the chosen row and panel, and long names stay inside their panels.

## 0.12.0 (2026-10-30)

- Symbol lookup, more language outlines, and an opt-in adapter for a trusted language server.
- Graph hover focus, live dragging, and smooth zoom in the code map viewer.
- Frontend work keeps every tooltip within two visible lines.
- Hardening from a full review of the map, lookup, audit, setup, and onboarding helpers: bounded Git inventories, CR-only line endings, JS and TS comments and regexes, repository names that are not UTF-8, Windows service startup, and clearer notes when a limit hides data.

## Earlier

0.1 to 0.11 built the plugin: activation for a session, project, or all projects across Claude Code, Codex, and Cursor; the one-time repository check-up; shared Git and pull request conventions; and the code map with its live viewer.
