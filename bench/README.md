# Benchmark

This folder holds the harness behind the results in the [main README](../README.md#benchmark). It runs headless Claude Code side by side on fixed engineering tasks, once per arm: no plugin, this checkout, any other version of Compound, or another plugin. Then it grades what each run did and what it left behind. Rerun it whenever a change to the skills, references, rules or scripts could change how agents work.

Nothing here is loaded by Claude Code, Codex or Cursor. Results stay on your machine in the ignored `bench/results/` folder, and fetched sources stay in the ignored `bench/work/` folder.

## Requirements

- Linux, as root or with unprivileged user namespaces. Every run gets its own mount and PID namespace, through `unshare` and `taskset` from util-linux.
- The `claude` CLI, `git`, Python 3.11 or newer at `/usr/bin/python3` with `pip`, and network access for the first `setup`. `map-retrieval` also needs ripgrep (`rg`).
- Sign-in that works without your home directory. Runs can't see `/root` or `/home`, so pass a token with `BENCH_PASS_ENV=ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`). Alternatively, keep a folder visible read-only with `BENCH_KEEP=<dir>[:<dir>...]` or `--keep <dir>` before the command. Folders that hold the proxy CA files named by `NODE_EXTRA_CA_CERTS` or `SSL_CERT_FILE` stay visible automatically.

Every run is a real agent session billed to your account. Cost grows with arms × tasks × models × repetitions, and `report` shows the measured cost per task.

### Y Harness completion comparisons

The [0.16.12 comparison](diagram_sources/comparison_v01612_completion.json) records the fixed schedule, source hashes, accepted changes and provider-reported costs for all seven attempts. The runner and meter used for that result are pinned at commit `cf2cc41fdd6ba9c84853768eb6b1fe2d1396c4d6`. Their SHA-256 hashes match the public record.

The current `yharness_completion.py` is a launcher for a prepared run directory with a frozen plan, Y Harness profile, isolated workspaces, grader and meter. The repository alone does not contain those run directories or private transcripts. Before dispatching a later attempt, the launcher checks prior attempts for complete grading and usage. It rejects duplicate or missing dispatch numbers and does not turn unreported usage into a zero charge.

In a prepared run directory, place the two profiles in `with.yml` and `without.yml`, the corresponding guidance in `instructions/<mode>/AGENTS.md`, and the exact treatment package in `plugin/`. Run `python3 -B run.py --launch-input-hashes` and merge its fields into the plan before hashing the plan. The hashes cover the profiles, guidance, package, runner, meter and verdict module. `python3 -B run.py --preflight` verifies those inputs, checks existing attempts and skips, and prints the next schedule index without starting Y Harness. A dispatch accepts only the next contiguous batch of indices and rechecks the frozen inputs before each attempt, including repairs. Historical ledgers remain readable through `--summary`.

The runner allows one active launcher per run directory. The OpenCode Go meter checks the model and output cap against the frozen plan and waits for the previous response’s final usage before sending another request. A transport failure or an unverifiable response stops dispatch. The dollar guard is checked before each request. A response already in flight can cross it.

#### Fresh dispatchkit sequence

[Dispatchkit](data/dispatchkit/tasks.json) is a small, dependency-free Python workload with two consecutive changes. The first reports a webhook routing symptom without naming a file or function. The second asks for a shared helper while preserving two caller policies. Each mode starts from the same clean fixture. Its code and conversation carry forward between tasks, with opposite mode order on the second task.

The grader runs both tasks' hidden checks after the refactor, runs the original tests against the changed source, and checks the agent's final test suite and retained original tests. It also reruns the added bug regression on the original source and requires a failure. Only the fixture goes into either agent workspace. The hidden checks and the preserving and wrong variants stay outside the agent workspaces.

Run the fixture and grading preflight without a model or Docker:

```sh
python3 -B bench/yharness_dispatch.py --validate bench/data/dispatchkit
```

The preflight requires the original bug, an unfixed refactor, a behavior-changing extraction and a lost earlier fix to fail. It requires the independently written fixes to pass. Any live run uses the same settings and one repair or recovery opportunity per task in both modes. The verdict uses every recorded attempt and requires both modes to finish both tasks before comparing allowance, list-price usage and cash charges.

In a prepared run directory, copy `yharness_verdict.py` beside the runner and use `python3 -B run.py --summary` to evaluate saved usage and grades. It counts metered requests from failed attempts and labels totals as lower bounds when usage is unverified. Interrupted grading stops the comparison and preserves its recorded charges. The fixture preflight needs neither a run directory nor a provider key.

[The 0.16.31 Dispatchkit comparison](diagram_sources/comparison_dispatch_v01631.json) uses the same tasks and reverses the mode order from the [0.16.15 run](diagram_sources/comparison_dispatch_v01615.json). Its ledger includes all four first-pass attempts, both task grades and the provider-reported cache and usage totals.

The [saved Dispatchkit trace audit](diagram_sources/work_review_dispatch_v01615.json) separates the two stages. The bug-fix runs reported 25.5% versus 85.9% cached input without and with Compound. On the follow-up refactor, cached input shares were closer at 90.8% and 94.0%. Compound used 13 versus 9 requests on the refactor, with 2,479 versus 6,762 reported reasoning tokens and lower billed allowance. The audit identifies extra searches and generated-file cleanup in that run, retains every charge and makes no estimate for a different cache state.

#### Scoped refactor replay

In the [0.16.31 Dispatchkit comparison](diagram_sources/comparison_dispatch_v01631.json), the Compound refactor spent its first two requests loading the skill and refactor guide. Its baseline and extraction checks passed by request 8. Requests 9–14 searched for more context, rewrote the helper signature and reran checks. Those six requests used $0.00505071 of Go allowance.

An offline replay reversed the three saved signature-related edits in a copy of the final artifact. The same network-disabled grader accepted both states. Both preserved the earlier routing fix, passed the hidden refactor checks, kept the original tests and passed all six final tests. The 0.16.32 saved rule routes this kind of scoped extraction directly and gives it a finish point after the required checks and diff review. The replay measures the saved work and checks the two artifacts. The new routing has no live cost measurement.

In the saved 0.16.75 Codex Dispatchkit refactor, the first patch added the shared packager and left both retired helper definitions and their calls. Replaying that patch passed all three public tests but failed the hidden structural check. Combining the saved changes into one patch produced the same accepted files and passed all six public and hidden checks. The later cleanup consumed a separate model response with 15,966 reported tokens, including cached input. The refactor guide checks retirement before the final suite. This replay measures the saved patch and its tests.

#### Checkout scope in saved refactors

Two saved Compound refactors searched outside their checkouts after the relevant source was available. The slug refactor spent requests 6 and 7 on a surrounding directory and instruction search, using $0.00395534 of Go allowance. The Dispatchkit refactor had passed its checks before requests 10–12 searched parent directories and the benchmark tree, using $0.00163497. These searches returned no new implementation evidence. The figures describe the five recorded requests. [Slug comparison](diagram_sources/comparison_v0169.json) · [Dispatchkit comparison](diagram_sources/comparison_dispatch_v01631.json)

The 0.16.37 saved rule keeps discovery for scoped extractions in the checkout. The full guide starts with named files and expands only for a concrete external caller or dependency. The next matched comparison used this rule.

#### Direct routing and edit reads

The saved 0.16.37 Dispatchkit comparison used 27 requests with Compound and 15 without. Both modes passed both tasks on their first attempts. Go allowance was $0.00610678 with Compound and $0.00405995 without.

The Compound bug fix used 15 requests for 14 tool calls. The baseline used nine requests for 14 calls. The first edit failed the editor's read prerequisite after a shell read, so the agent read the test again through the native tool. On the scoped refactor, the first two requests loaded the skill and its refactor guide before opening the named files. Those two requests used $0.00027731 of allowance. Two more requests searched the fixture and its Git history before opening the named callers. Those searches used $0.00073959 and found no new implementation evidence.

The 0.16.38 rule puts the editor's required read tool first, asks the agent to batch independent calls and search for unknowns, and routes scoped extractions directly through the saved guidance. Offline checks verify rule delivery. Total cost on the revised rule remains unmeasured.

The same saved bug fix ran two passing tests before adding the regression and later removed generated bytecode in a separate request. Those requests used $0.00033881 of Go allowance. In a network-disabled replay, the targeted regression still failed with 404 versus 200 on the original source, and the final artifact passed its three-test suite, diff check and independent grade. Writable copies produced bytecode with the original Python command and none with `python -B`. The 0.16.45 rule separates the bug regression from the extraction baseline and names that option. The replay verifies the checks and artifacts. It has no new model-cost measurement.

#### Consecutive upstream Flask fixes

This sequence starts both modes at Flask commit `514fc6b`. Fix the IPv6 test-client session bug first and the IPv6 development-server parsing bug second. The existing real-bug benchmark used the individual tasks separately. This sequence keeps the same checkout and conversation within each mode, then checks that the second change preserves the first.

After building the frozen Flask fixtures and test dependencies, validate the sequence offline:

```sh
python3 -B bench/bench.py setup --real flask-ipv6-session,flask-ipv6-run
python3 -B bench/yharness_flask_sequence.py preflight
```

Setup fetches pinned inputs if needed. Preflight uses local copies and prints the starting revision, fixture hash, prompts and grades. The starting repository has one branch, no remotes and neither upstream fix. Keep the preflight report, upstream repository and grading files outside the agent workspaces. Both modes receive the same prompt for each stage. Each prompt states that edits are limited to the source and tests needed for the fix. Reverse the order of the modes between stages.

Grade each candidate in a disposable, network-disabled runner with read-only inputs and the matching Python environment. Mount the fixture and reference tests there with the benchmark work layout. Save the accepted first-stage snapshot outside the agent workspace before the next task.

```sh
python3 -B bench/yharness_flask_sequence.py grade 1 /input/project
python3 -B bench/yharness_flask_sequence.py grade 2 /input/project --previous /input/accepted-stage-1
```

To use the existing Y Harness completion runner, set `grader` to `flask-sequence` in the frozen plan. Use the preflight fixture and task list for the sequence. Copy `yharness_flask_sequence.py`, `flask_server_name_probe.py`, `common.py`, `fixtures.py`, `tasks.py` and `probe_pytest.py` into the prepared run's `grader/`. Place the two `refs/real/flask-ipv6-*` directories and the pinned `pyenv/flask` under `grader/work/`. The scrubbed fixture belongs in `fixtures/flask-ipv6-session`. Run `python3 -B run.py --flask-input-hashes` in the prepared directory and save its JSON as `flask_input_hashes` in the plan before hashing the plan. Use Python 3.11 with current security updates or newer on the runner host.

The runner checks these inputs before each attempt and checks the two starting copies against the frozen fixture. The meter checks the delivered task or repair prompt before the first request of each attempt. The ledger verifies those prompt hashes, routing and tool lists before comparing costs. It grades each archived source and test snapshot in the separate container. Before task two, it verifies the accepted snapshot from the same mode, checks the entire live checkout against the expected state, and resumes that mode's session. At both stages it records the changed paths and rejects changes outside the two files for that fix. The check compares file contents, executable bits, and symlink targets, and skips Git metadata, pytest caches, and Python bytecode caches. Both task-two attempts use the same read-only baseline. Repair prompts give feedback without private grader output. Keep the grader bundle and run records off the model's mounts.

The grader runs the cumulative hidden checks and the original, previous and final test suites where applicable. The second stage also checks that a host-only `SERVER_NAME` keeps the configured host with both the default port and explicit port zero. At each stage it requires an added or changed regression to fail on the preceding source and pass on the current source. In preflight, the full reference passes 493 tests. The grader rejects a missing fix, a second fix that drops the first, a missing second regression and removal of the first regression. These preflight checks run offline. The [0.16.45 Flask comparison](diagram_sources/comparison_flask_v01645.json) records the metered Y Harness run with DeepSeek V4.1 Flash. Its ledger includes all four attempts, usage, artifact hashes and cumulative grades.

In the 0.16.45 Compound runs, both fixes passed narrower post-fix checks and then passed the full suite without intervening edits. The second run also tried to edit a file it had read through the shell. Y Harness required its native Read tool before accepting the edit. After the final suite passed, separate mypy and Ruff calls reported that the tools were unavailable. The 0.16.46 rule names native Read and reserves extra checks for project requirements or gaps in evidence. The comparison ledger includes those charges.

In both 0.16.54 Compound attempts, a focused post-fix regression run and the full suite passed on the same edits. The first attempt also ran a passing module baseline before adding its failing regression and tried unavailable Ruff after the full suite. A network-disabled replay of all four saved artifacts passed the independent cumulative grades. The 0.16.55 rule uses the failing regression as baseline and the full suite as confirmation. The replay verifies the artifacts and test coverage. It does not measure adherence to the revised rule or model-cost savings.

The saved 0.16.45, 0.16.54 and 0.16.60 Flask runs contain six rejected edits after the target had been viewed through the shell. Four occurred without Compound and two with Compound. The request containing the 0.16.60 Compound rejection used $0.00028602 of Go allowance. The 0.16.70 rule makes the native read prerequisite apply to each edit target when the host requires it. The saved usage records include those requests. No model run measured adherence or savings under the revised rule.

The 0.16.60 Compound test-client trace spent five requests inspecting Werkzeug, running standalone probes and searching history after it had opened the relevant source and test. The development-server trace spent one request searching adjacent CLI code after finding the matching `app.run` test. These six requests used $0.00199995 of Go allowance and included 1,428 reasoning tokens. The 0.16.72 routing rule tells agents to write and run the regression first, and the debug guide names the nearest test as the starting point. The offline replay checks the saved fixes and their regressions against the original sources. Adherence and total model cost under the revised rule remain unmeasured.

The corrected-scope 0.16.72 rerun passed both fixes in both modes. Compound used 78,277 uncached input tokens versus 45,420 without it. The first four requests on the session fix accounted for 19,794 of the 32,857 extra uncached tokens. The provider reported zero cached tokens on those four Compound requests. The saved trace shows a 6,919-byte skill result, the 1,813-byte debug guide and two broad source and test reads before the fourth request. The meter reports cache counts, while the trace shows the context carried into those requests. The provider's reason for the cache misses is unknown. The 0.16.74 rule keeps local bug fixes on the short route when conventions are clear, trims the skill entrypoint and asks for relevant source ranges and concise check output. Offline verification covers delivery and the saved artifacts. Cost on the new guidance remains unmeasured.

An offline replay of the two accepted 0.16.72 Compound patches used the saved successful edits and source excerpts around their known locations. The excerpts totaled 3,315 bytes versus 19,165 bytes of native-read output in the trace. The replay omitted one edit rejected by the host before a native read, plus the discovery and duplicate checks outside the patch-and-grade sequence. It recreated both source and test trees byte-for-byte. The independent grader confirmed both regressions against their preceding sources and passed the cumulative checks and 493 final tests. The replay measures source excerpt size with edit locations supplied. It does not measure discovery, model behavior or billed savings.

#### Final suite replay on the Codex Flask fixes

In the [clean Git comparison](diagram_sources/comparison_codex_flask_luna.json), the Compound runs passed a 26-test module after the session fix and a 133-test module after the corrected server fix. Each was immediately followed by a passing full suite on the same code. In an offline replay, both added IPv6 regressions failed before their fixes, and the full suite caught the intermediate `localhost:0` regression. After correction, the full suites passed all 492 and 493 tests for the two stages. The updated rule asks for one final suite per edited state and a separate regression check when that suite omits it. The published token totals include both original module checks.

Using those same saved Flask patches, an offline replay ran each added regression on its unfixed and fixed source. The default failing pytest reports totaled 9,358 bytes. With `--tb=line`, they totaled 1,012 bytes (89% less) and retained the selected tests, failure exit statuses, missing session key and invalid port conversion. The fixed suites passed 492 and 493 tests. The guidance uses the short traceback for a known failure and expands it when the result leaves a diagnostic question. This replay measures emitted test output.

In the saved eight-task GPT-6 Luna comparison, Compound 0.16.75 edited source, reverted the fix, and reapplied it around the failing regression on each Flask task. An offline replay ran each saved test on the original source before applying the fix. Source edits fell from three to one per task. The final source and test trees matched the accepted artifacts, and the full suites passed 492 and 493 tests. The default rule puts the regression before source edits. The replay measures source edits and test outcomes.

In the clean Git eight-task GPT-6 Luna run, the candidate Flask server fix sent `[::1]` to the server and added a test that expected the same value. All 493 visible tests passed, while the independent check expected `::1`. The saved repair used six model responses and 158,754 reported tokens. An offline replay of both patches checked numeric address resolution at the receiver and reproduced the rejection of `[::1]`. The repair passed that check, the explicit-host and port-zero controls, and all 493 visible tests. The default rule asks agents to verify changed arguments against the receiving API before setting test expectations.

## Compare a change with main

```bash
python3 bench/bench.py setup
```

```bash
python3 bench/bench.py run --label my-change --arms main=ref:main,new=worktree --tasks core --reps 3
```

```bash
python3 bench/bench.py judge --label my-change
```

```bash
python3 bench/bench.py report --label my-change --baseline main
```

- `setup` fetches the pinned sources and builds the fixtures. It checks each fixture against the frozen original and makes the template Claude config. Run it once; it reuses what it already fetched. `setup --real <name>[,<name>...]` builds and checks only those real bugs, so new ones can be added while other runs go on.
- `run` runs every arm on the same task at the same moment, each on its own CPU, and rotates the arm order and CPUs by repetition. Rerunning a label resumes it. If a group fails on an API or harness error, it runs once more. To stop after the groups already running, create `bench/results/<label>/STOP`. Runs also stop on their own when seven-day usage reaches 80% (`--max-seven-day`).
- `run --permissions strict` runs every task in Claude Code's default permission mode with only edits pre-approved, so each Read or Bash call that would ask a user is recorded as a denial; `--permissions setup` grants exactly the rules `setup-global` gives Claude Code, and nothing else of Compound's, so loading the skill is not pre-approved; `--permissions helpers` also pre-approves the skill tool and all of Compound's helper scripts. A label keeps one profile.
- `judge` blind-grades the review and investigation answers against frozen keys, with three votes per answer. `judge --regrade` checks the stored votes' quotes again after a change to the quote check, without asking the judge again.
- `report` prints per-arm tables and paired tests against the baseline. It also writes `summary.json` and `summary.md` into the label's folder.
- `rescore` recomputes the habits from the saved transcripts after you change a detector, so older runs are scored the same way.

Add `--models opus,sonnet` to cover both models. Each model gets its own tables, because a change can help one and not the other.

## Installed plugin smoke test

With Codex CLI, Claude Code and Python 3.11 on your path:

```sh
python3.11 -B bench/smoke_plugin_install.py --ref HEAD
```

The check installs a Git archive through each host's local marketplace in a temporary home. From the installed copy it checks the five skill files, global setup, status, idempotence and removal, plus a read-only map and the local viewer's HTML and CSS. It preserves an existing instruction and checks paths containing spaces. It also corrupts the temporary metadata, runtime and registry files, verifies a read-only query, then checks recovery through the live viewer. It calls the installed helpers directly and uses no model calls. On macOS, add `--fresh-chat` for a separate Codex CLI check. It launches three fresh chats in the temporary home with a scripted loopback provider and outbound access limited to that provider. The first two check the skill catalog and the saved rule before and after setup. The third invokes `$compound-skills:map` and checks that Codex injects the guide. The setup and status shortcuts remain installed for explicit use. Use the [first task in the quick start](../README.md#quick-start) to check model behavior. Claude Code and Cursor fresh chats are untested. Pass `--host codex` or `--host claude` for one host. The 0.16.30 check used Codex CLI 0.162.1, Claude Code 2.1.312 and Python 3.11.15.

## Audit costs without new runs

```bash
python3 bench/bench.py cost-audit --label <saved-label>
```

This command only reads saved records and works without Linux or Claude Code. It makes no model or judge calls. Each task, model and arm reports recorded spend, accepted results (`outcome.success`), unresolved valid attempts, ungraded results, invalid attempts and superseded attempts, plus token and tool-call totals. Recorded spend includes invalid and superseded attempts rather than dropping their cost when the benchmark retries a group. Missing costs or a run without a final usage record leave spend per accepted result unknown; ungraded answers are not counted as failed fixes. Judge costs are excluded.

Spend per accepted result is the batch's recorded spend divided by accepted results, including spend on unsuccessful attempts. Existing runs do not link agent correction sessions or sequences of project changes, so this is an audit of first-attempt batches, not a measurement of long-term savings. It does not estimate how many retries would succeed.

### Source-first review trace replay

In the saved second-round Flask review, four runs per mode found all three planted defects. Both stock Sonnet runs used one diff read each. Across all four runs per mode, Compound used 28 tool calls in 21 assistant messages, versus 11 calls in nine messages without Compound. Each Compound run attempted runtime setup after reading the diff. After the first denial in each run, they made 11 more denied Bash calls and five successful scratch writes or edits.

The added hunk itself shows all three mechanisms. The closure shares the loop's directory binding, the cache fallback treats zero as unset, and the file-serving call joins an unchecked filename. The 0.16.52 rule starts from the diff and limits further reads to relevant callers and tests. The review guide asks which finding a reproduction could change and requires permission before setup. These are saved counts and source checks. Review costs on the revised rule remain unmeasured. [Historical review comparison](historical-comparisons.md#where-it-doesnt-help-reviews).

## Arms

| Arm | What runs |
|---|---|
| `without` | No plugin and no rule |
| `with` | This checkout, including uncommitted changes |
| `rule` | No plugin; instead, a five-sentence user rule asking for the habits the benchmark scores: reproduce the bug, show a failing test first, run the full suite, record behavior before a refactor, and report what was and was not verified |
| `name=worktree` | This checkout under another name |
| `name=ref:<revision>` | Any commit, tag or branch of this repository, such as `ref:v0.13.0` or `ref:main` |
| `name=dir:<path>` | A plugin folder on disk with `.claude-plugin/plugin.json`: another Compound, or any other Claude Code plugin |
| `name=none` or `name=rule` | No plugin, under another name; `a=none,b=none` measures noise between identical arms |
| `name=<source>+rule:<file>` | Also installs `<file>` as an always-on user rule, for a plugin whose setup asks for one, or `none+rule:<file>` for a rule alone |
| `name=<source>+prefix:<text>` | Starts every prompt with `<text>`, such as the slash command another plugin asks its users to type (`+prefix:/pstack:poteto-mode`) |
| `name=<source>+variant:nomap` | Compound with the map query removed from its startup and its always-on rule, to measure what the map adds (`VARIANTS` in `common.py` lists the exact edits) |
| `name=<source>+variant:noreview` | Compound 0.16.0 without loading its skill for reviews, to measure what the skill adds to a review |

The no-map arm decides whether the startup map query stays. Fixed before label `v016` ran: Compound drops the startup query if, over the real bugs and the held-out refactors together, the no-map arm (1) fixes no fewer bugs and finishes no fewer refactors correctly beyond noise (a paired McNemar test against it with p < 0.1 counts as fewer), (2) stays within two runs of Compound on reproducing first and on showing a failing test before the fix, and (3) costs less, with the paired cost ratio's 95% upper bound at or below 1.0. Otherwise the query stays.

The no-review arm decides whether reviews keep loading the skill. Fixed before label `v016r` ran: reviews stop loading the skill if, on `review-shopkit` over both models, the no-review arm (1) finds no fewer planted defects than 0.16.0 beyond noise (a paired sign-flip test of the judge's scores with p < 0.1 and fewer found counts as fewer) and (2) costs less, with the paired cost ratio's 95% upper bound at or below 1.0. Otherwise reviews keep loading it.

Plugin arms run from a snapshot named by its content hash. The snapshot leaves out `bench/`, which holds the answer keys, along with `tests/` and `.git`. Before each run of a Compound arm, the arm's own `project_setup.py enable --global --host claude` writes its always-on rule. Before 0.15.0, coding work also ran a one-time repository check-up; for those versions, write tasks record it as completed, so runs measure everyday use, and the `first-use` task runs without that record. From 0.15.0 the check-up runs only on an explicit project `setup`.

Another plugin is mounted under its manifest name and gets none of Compound's setup: only its own files and the `+rule:` file, if given. In read tasks it may run any file from its own folder, as Compound may run its map helpers. A run is invalid if any plugin other than the arm's own loads, apart from Claude Code's bundled `cc-plugin-*` plugins. Plugins from elsewhere are code you run: read one before you benchmark it, and pin it by commit.

## Multi-step navigation preflight

Replay three read-only navigation prompts on the pinned Flask and Django sources. The tasks trace ASGI disconnect cleanup, row-lock handling in and out of a test transaction, and Flask streaming teardown. The prompts name behavior and public APIs. The grader's file paths, symbols and source witnesses stay outside the agent's checkout.

```sh
python3 -B bench/map_navigation.py
```

The local preflight checks that each witness occurs within its named symbol at the source pin. For each case, it runs the same fixed lookup query in both tools. Without Compound, it uses literal `git grep` counts, ranks Python files by distinct terms in their path or source, and lists top-level tests last. With Compound, it takes the first four complete file paths from the normal 2,500-character summary. Counts use distinct rubric files. Import hints are available to the reader and excluded from the first-four score.

At 0.16.49, without and with Compound found 1/3 and 1/3 on disconnect cleanup, 1/3 and 0/3 on row locks, and 3/3 and 2/3 on streaming. In 0.16.50, the map puts the exact `TestCase` and `select_for_update` definitions first for the row-lock query, raising its first-four count from 0/3 to 2/3. Both modes now surface 5 of 9 rubric files across the three cases. The map also puts `stream_with_context` first on the Flask query, with the same first-four count. The explicit `tests for select_for_update` control keeps the test file first. Recall at ranks 1, 4 and 12 and recall in the visible summary stayed the same on each of the 96 saved commit-title queries used for the lowercase-symbol replay.

In 0.16.54, the map shows the response implementation in the Django disconnect shortlist and matches Flask's `ctx.py` when the query says “context.” Keyword search shows 5 of 9 rubric files across the three cases, and the map shows 7 of 9. The row-lock and explicit test controls retain their results. The three tasks informed the change. A separate replay of 132 commit-title queries preserved every previously found target at ranks 1, 4 and 12 and in the visible summary. One Packaging query gained a target in the top four, and two more gained a target in the top 12. This replay includes 36 previously unused queries drawn from the next 12 qualifying commits per repository after the 0.16.48 validation set in attrs, Packaging and marshmallow.

In 0.16.59, the complete visible summaries show 8 of 9 rubric files across the three pinned queries, up from 7 of 9. The Django disconnect summary now lists `django/db/__init__.py` as a ranked result with `close_old_connections` at line 57. The first four paths and the 2,500-character cap stayed the same. The renderer prioritizes whole paths over some signatures and import details when space is limited.

In 0.16.60, the row-lock query treats `TestCase` as a named class and keeps production matches competitive. The complete summary now includes `django/db/models/sql/compiler.py` alongside the queryset and test case definitions. All 9 rubric files are visible across the three summaries. The first-four score stays at 7 of 9. An explicit search for tests still puts a test file first.

These are starting points for navigation. They measure neither the agent's completed trace nor model cost.

The [0.16.57 matched navigation comparison](diagram_sources/comparison_navigation_v01657.json) records all six metered attempts. Both modes passed all ten source citations. The two arms matched on every field of the initial provider request outside the task message.

On Django disconnect handling, the map arm used fewer requests and tool calls but had 10,688 uncached input tokens versus 5,805 without the map. Its first three tool results retained 17,925 bytes of source excerpts. A keyless replay used the terms from its later scoped search across the 22 complete Python paths and import hints in the original map. The search returned 1,874 bytes and found all four cited lines, which passed the source grader. Compound 0.16.58 directs agents to search listed files and read nearby lines. The replay verifies the source evidence. Agent behavior and cost under the revised prompt remain unmeasured.

In the saved eight-task GPT-6 Luna comparison, all six Flask streaming answers cited the teardown line under `RequestContext.pop`. The source defines it in `AppContext.pop`. Replaying the 15 saved navigation answers with one batch lookup per answer verified the enclosing symbols at their supplied paths and lines. The lookup corrected six Flask answers and four Django answers and preserved all four already-correct answers. One Django answer still failed with its supplied locations. The default rule now directs exact Python citations to the read-only map lookup. The replay measures citation verification on saved answers.

Prepare the common task prompts and the treatment's initial map context from the pinned sources:

```sh
mkdir -p bench/results
python3 -B bench/map_navigation.py --prepare > bench/results/navigation-plan.json
python3 -B bench/map_navigation.py --grade flask-streaming bench/results/flask-answer.json
```

Each task records the source revision and a hash of the generated map. Give each arm the common prompt and its own orientation field, with identical read-only checkouts, model settings and native navigation tools. Keep the benchmark code and the other arm's context outside both workspaces. The grader checks the ordered path, symbol and line for each requested statement at the pinned source. A partial or malformed answer fails. This grades source citations. It does not judge narrative explanations.

The prepared data and grader work offline. To use the metered Y Harness launcher, set `grader` to `map-navigation`. Put the prepared tasks in `sequences[0].tasks` with each `id` also used as its `name`. Schedule one entry per task and mode, alternating which mode goes first. Use identical read-only profiles with native Bash, Read, Glob and Grep. Keep the default instruction files and the `plugin/` directory empty. Mount the pinned Git checkouts at `workspace/django` and `workspace/flask` with read-only access confined to the current checkout. Copy `map_navigation.py`, `common.py`, `fixtures.py` and `map_retrieval.py` to the host-side `grader/`, outside agent workspaces.

Run `python3 -B run.py --navigation-input-hashes` and save the output as `navigation_input_hashes` in the plan. Merge the output of `--launch-input-hashes`, hash the plan and run `--preflight`. This checks frozen inputs without starting Y Harness. The launcher uses a fresh session for each task and resumes that session only for a repair. Before each attempt's first request, the meter requires one user message matching the frozen task or repair prompt and the read-only tool set. It records a hash of the remaining request. All billed attempts and repairs contribute to `--summary`, which withholds a cost claim when the initial request context outside the task prompt differs between arms. Live dispatch requires the explicit `--dispatch-navigation` flag before the frozen indices. Verify the runtime profile and both arms' read-only isolation offline before live dispatch.

## Index completion wait

Compare warm local summary calls on pinned Flask and Django checkouts. Run from the 0.16.28 checkpoint:

```sh
python3 -B bench/map_index_wait.py --baseline-ref 8477c8a
```

The replay warms each service once and repeats its query seven times. It measures elapsed time for the live summary function, including the Git and file checks, with interpreter startup outside the measurement. Flask used two to three status requests before the change and Django used four to six. Each updated query used one request. Median elapsed times were 149.19 ms versus 110.39 ms on Flask and 410.11 ms versus 354.87 ms on Django. Both versions returned byte-identical summaries. [Samples, source pins and hashes](diagram_sources/map_index_wait_v01628.json).

## Saved viewer focus

Compare distinct warm CLI text queries on pinned Flask and Django checkouts. Run from the 0.16.27 checkpoint:

```sh
python3 -B bench/map_registry_replay.py --baseline-ref 9ecfd4f
```

Each arm opens a viewer with a saved query, warms its index and requests three different summaries per repository. Every baseline request changed the registry. None of the six updated requests changed registry contents, inode or modification time, and every summary matched its baseline byte for byte. Both arms save an explicit change to the viewer query. The replay measures local persistence with zero model calls. [Results and pins](diagram_sources/map_registry_replay_v01627.json).

## Exact-path queries

Compare exact-path ranking on clean, pinned Flask and Django checkouts under `bench/work/sources/`. Run from the 0.16.24 checkpoint:

```sh
python3 -B bench/map_exact_path.py --baseline-ref efe0a7a
```

Both rankers use the same map metadata and source checkout. The replay selects 24 evenly spaced paths from each sorted Python file list and adds the two paths that exposed the issue. The requested file ranked first for 19 of 50 queries before the fix and 50 of 50 afterward. The full ranking for one topic query per repository stayed the same. [Paths, ranks and pins](diagram_sources/map_exact_path_v01624.json).

## Exact-path agent summaries

The original 0.16.34 replay compares 50 exact paths from pinned Flask and Django checkouts using the same index for both renderers. Run it from commit `ad89f69`:

```sh
python3 -B bench/map_exact_path.py --baseline-ref 5357032 --summary
```

Ranking probes fell from 2,500 to zero, avoiding 53,672,632 source bytes in the summary phase. Total emitted text fell from 113,688 to 39,925 bytes, a 64.9% reduction. The summaries kept the same indexed record for each target. Three grew because the single-file layout could show more of the target outline. Four topic and miss controls stayed byte-identical with the same reads. These counts exclude Git and indexing work.

A direct CLI replay against `b9db91b` queried `./src/flask/wrappers.py` and `./django/urls/base.py` at the same repository pins with `--max-files 3 --max-chars 500`. Each path ran with `--no-cache`, `--cache-read-only` after priming, and a simulated unavailable service after priming. Across the six commands, query ranking went from 300 source probes and 5,564,763 bytes read to zero. All six responses were byte-identical, indexing parse counts matched, and read-only and no-cache state stayed unchanged. The replay used local files and no model requests.

A local regression replay gave the in-process map two files with the same name and reduced either the inventory cap or the source budget to one file. Before 0.16.47, the inventory cap returned the archived copy and the source budget left the requested file without symbols. With 0.16.47, both cases return the requested file and its symbol, with and without a leading `./`. Coverage remains partial in all four cases. The same failures and fixes reproduced at the shipped limits with 20,000 archive files plus the target for inventory and 64 one-MiB archive files plus the target for source reads. Six exact-path and topic comparisons on the pinned Flask and Django checkouts returned the same results, excluding JSON generation timestamps.

Compare declaration visibility against 0.16.55 on the same 50 paths:

```sh
python3 -B bench/map_exact_path.py --baseline-ref 8a54318 --summary
```

The 0.16.56 summaries retain every previously visible declaration and show more on 23 paths, increasing the total from 120 to 218. Total text grew from 39,925 to 42,944 bytes. All 50 responses still show one file and make zero source-ranking probes. Four topic and miss controls are byte-identical. The replay excludes indexing and makes no model calls.

## Lowercase symbol queries

On the parent of Flask commit `2a8a38b051fc248865730bf3511bf2e2ea325e81`, the query `support query in methodview` did not show `src/flask/views.py` in the 0.16.47 agent summary. The file was outside the first 12 ranked paths. In 0.16.48, the file ranks second and the summary includes its `MethodView` symbol. The ranker now keeps the lowercase spelling of an alphanumeric symbol alongside its component words.

The replay used one unchanged index per commit parent, the cleaned commit title, and the default 2,500-character summary. This was the only changed file ranking or visible path list in 24 development queries from Flask and Click. A separate 72-query check used the first 24 qualifying non-merge commits in attrs at `c8bb9bf`, Packaging at `78d8673`, and marshmallow at `b762ea2d`, using the selection rules in [map_retrieval.py](map_retrieval.py) and each project's source directory. All 72 kept their first 12 paths and visible path lists. No model calls were needed for the replay.

## Exact-symbol agent summaries

Compare bare structured symbol names on one unchanged index per pinned Flask and Django checkout:

```sh
python3 -B bench/map_exact_path.py --baseline-ref 0d62a9d --symbols
```

The replay selects 12 evenly spaced names with one indexed defining file per repository, then adds `stream_with_context` on Flask and `select_for_update` on Django. Across all 26 queries, source probes during ranking fell from 1,300 to zero, avoiding 27,070,622 source bytes. Emitted context fell from 59,931 to 21,790 bytes (63.6% less). Every response shows its target declaration and keeps the previously visible matching declarations. The 8 ordinary, multiword, ambiguous and missing-name controls returned identical summaries and read counts. Indexing was outside this measurement, and model usage remains unmeasured.

## Warm map query work

Compare against `c83939a` with `python3 -B bench/map_warm_work.py --baseline-ref c83939a` to measure reuse of the viewer's initial Git status. On both pinned checkouts, a cold query used 14 Git processes instead of 17 and two directory walks instead of three. Warm queries used seven Git processes in each build. All focused summaries matched byte for byte. The final freshness check still detects source or index changes during the build.

From 0.16.53, the live freshness check uses the complete Git inventory to cover untracked paths and asks Git status for tracked changes only. Reproduce the change with:

```sh
python3 -B bench/map_warm_work.py --baseline-ref 8b37ae8
```

Git Trace2 reported one directory walk instead of two on each of three warm queries per pinned Flask and Django checkout. Each query returned the same summary bytes and used six Git processes in both versions. The full status walk remains available when the inventory is capped. Separate local checks covered untracked additions, edits, renames and removals, and a staging change with identical worktree contents.

Compare live CLI queries on clean, pinned Flask and Django checkouts under `bench/work/sources/`. Run from the 0.16.21 checkpoint:

```sh
python3 -B bench/map_warm_work.py --baseline-ref 85f2616
```

Each version warms an isolated local map service once per checkout and then repeats the same focused query three times. Git Trace2 counts processes started by both the CLI and the service. Every warm query used 6 Git subprocesses, down from 12, and both versions printed the same summary bytes. The remaining file inventory and status checks keep the map fresh. This measures local subprocess work with zero model calls. [Counts and source pins](diagram_sources/map_warm_work_v01621.json).

A recovery replay primed an isolated cache on each pinned Flask and Django checkout, simulated one Git inventory failure, then queried the unchanged checkout. Against `ddb1b8f`, Flask recovery went from 125 file parses to zero, and Django from 3,497 to one. The recovered file records matched exactly. A valid empty inventory still removes old entries. The simulation used local files and no model requests.

A second replay failed only the untracked-file enumeration on the same clean pins. Against `72c710d`, the partial map returned 125 Flask and 3,496 Django records where both previously returned zero. The exact target was visible in each summary, with an explicit untracked-coverage warning. Both full caches stayed byte-identical and recovery used the same number of parses as the baseline.

## Source-only map lookups

Compare the default agent summary and local source reads on pinned Flask, Click and packaging snapshots:

```sh
python3 -B bench/map_content_fallback.py --baseline-ref 0ffac77
```

Four selected queries exercise terms found only in file contents beyond the initial scan. All four targets appear with the fallback. The three normal symbol controls preserve their focus and source probes. The three no-hit controls retain their ranking and probe 92 to 125 files instead of 50. Across those misses, the extra reads total about 52 to 195 KiB per query. The fallback retains an 8 MiB read budget and a 200-file cap. [Probe results and pins](diagram_sources/map_content_fallback_v01619.json).

## Mixed-keyword lookups

Replay selected two-keyword lookups against the same pinned source and map index in both versions:

```sh
python3 -B bench/map_content_fallback.py --baseline-ref 9dae2d0 --mixed
```

All three selected lookups show the previously missing file in the default summary and keep their first three ranked paths. The extra scan took 1, 17 and 42 source probes. Six exact-path and ordinary topic controls kept their original focus and probe counts. Three partial misses used 42 to 50 additional probes and preserved focus. The 36 saved commit titles were also queried on the pinned trees. All 36 kept their focus and 35 kept their probe counts. The remaining title took 50 extra probes. The scan shares the existing 8 MiB cap. [Probe counts, bytes and pins](diagram_sources/map_mixed_keywords_v01625.json).

With `--baseline-ref 1d7696d --mixed`, the replay also checks each source-only query prefixed with its repository name. All three targets went from absent to visible. Flask, Click and Packaging used 11, 17 and 42 additional probes, respectively. The first three ranked paths stayed the same. The 36 commit-title controls kept identical focus. Three took 50 extra probes each, with no additional match. In a separate replay of 24 recent Flask and Click titles on their actual parent checkouts, both versions showed 25 of the 27 touched source files in the agent summary and ranked 22 in the top four. These are offline navigation checks.

## Unicode map queries

On a 65-file local fixture, five focused queries missed their expected file with the previous ranker. The revised ranker put all five first, including a single-character CJK symbol, a decomposed accented spelling and a Devanagari word found only in a source comment. The source-only match used the existing bounded fallback after the first 50 files.

To replay the existing exact-path, topic, partial-miss and commit-title controls against the prior ranker:

```sh
python3 -B bench/map_content_fallback.py --baseline-ref 518e581 --mixed
```

All 48 controls kept their focus and number of source probes on pinned Flask, Click and packaging checkouts. These checks measure local lookup behavior.

## Focused summary coverage

Replay focused summaries on commit parent snapshots from pinned Flask, Click and packaging histories already present under `bench/work/sources/`:

```sh
python3 -B bench/map_text_coverage.py --baseline-ref 2b96ffa
```

The replay selects 12 qualifying commit subjects per repository and renders each ranked map with both versions at 500 and 2,500 characters. It counts whole paths that were present in the parent and touched by the commit. At 500 characters, visibility rose from 22 to 29 of 41 changed-file paths. At 2,500 characters, both renders showed 38 of 41. This checks what the summary exposes before source inspection. [Raw counts and source pins](diagram_sources/map_text_coverage_v01618.json).

## Offline release regression gate

```sh
python3 -B bench/regression_gate.py --historical
```

The gate checks five workloads independently. Use a small edit, an upstream bug fix, a behavior-preserving refactor, a review with verified findings, and source-grounded navigation. Use the established fixtures as regression controls and freeze separate held-out tasks before evaluating a prompt change. For review and navigation, require the planted findings or expected citations and an unchanged worktree. For edits, use the task's independent tests and patch-scope checks.

The controls are stock with no plugin and the pinned Compound 0.16.45 build at `3ab9db8a2e159a91a24aad006dee5e96c627c98a`. That build passed both upstream Flask fixes at lower measured allowance than stock. The historical audit recomputes saved results from their recorded attempts. It keeps older builds, different models and the pstack comparison in separate cohorts. Saved review costs cover the agent runs. The independent historical judge's charges are unavailable. Offline replays check deterministic behavior and contribute no estimate of candidate model cost.

For a candidate, supply one saved ledger per workload in an ignored `bench/results/` directory. Freeze the task set, three build identities, grader and protocol before any requests. Use the same checkout, prompt, tools and repair opportunity across arms. Verify the delivered inputs and reconcile every attempt against the runner’s receipts. Keep raw transcripts and ledgers local.

```sh
python3 -B bench/regression_gate.py --evidence bench/results/my-gate --candidate "$CANDIDATE_TREE" --historical
```

Use filenames `small-edit.json`, `upstream-fix.json`, `refactor.json`, `review.json` and `navigation.json`. Each ledger contains `workload`, `plan` and `attempts`. Use one provider per invocation.

- In `plan.builds`, set `stock` to `none` and set `last-good` and `candidate` to their frozen revisions. In `plan.protocol`, record `provider`, `runtime`, `model`, `reasoning_effort` and `repair_limit` of one per task.
- `plan.sequences` contains one object with a `tasks` array. Each task has a `name` and the SHA-256 fields `fixture_sha256`, `prompt_sha256` and `grader_sha256`. The grader hash identifies the grader that produced the recorded outcomes. `plan.schedule` lists `[0, stage, arm]` once per task and arm, in stage order within each arm.
- Every attempt has `index`, `stage`, `task`, `arm`, `attempt`, `attempt_kind`, `accepted`, `grade.success`, `valid_usage`, `requests`, `meter_sha256`, the actual `build`, `served_model` and the three delivered task hashes. `plan_sha256` is the SHA-256 of the frozen plan encoded as sorted-key JSON with separators `(',', ':')`. Include failures, semantic repairs and interruption recoveries. Retain known usage on incomplete attempts and set `valid_usage` to false.
- For a Python refactor trial that requires observed test execution, freeze `plan.protocol.refactor_verification` as `unittest-discover` and record each task's byte-based `original_source_digest` from [the Python shim](shim/devtrace.py). Include each attempt's shim records in `test_observations`. The independent grade records `own_suite_tests` and `verification_state` with the final `cwd`, `src` and `tests` digests. Every arm needs passing `python -m unittest discover -s tests` observations on the original and final source in that order, using the same final test bytes and matching the grader's positive test count. A baseline can carry across a repair. Missing observations block the comparison while the report retains accepted artifacts and all measured usage. The gate lists verified stages under `verified_refactor_stages`.

**OpenCode Go.** Set `provider` to `opencode-go`. Add the frozen `output_cap`, `request_cap` per arm, and decimal-string `allowance_guard` to the protocol. Use reconciled decimal `allowance`, `list_cost` and `cost` in each attempt’s `costs` object. A passing gate requires all three measures to stay at or below each control on every workload. `savings_claim_ready` additionally requires strictly lower aggregate allowance and list cost than both controls.

**Codex sign-in.** Set `provider` to `codex-chatgpt`. Add the actual `wall_timeout_seconds` and integer `weekly_allowance_guard_percent` to the protocol. Record the runtime as `Codex CLI <version>` and use one model, runtime and reasoning setting across workloads. Freeze each task’s `repair_prompt_sha256` and `recovery_prompt_sha256`. A follow-up attempt records the hash of the prompt it actually received.

- Add `session_id`, `turn_id`, `model_rerouted` and `meter` to each Codex attempt. Export the served model and reroute status from the saved session. An incomplete attempt with no observed model may record a null `served_model`. `meter.receipts` contains the ordered `token_usage_record` payload fields `response_id`, `session_id`, `turn_id`, `usage`, `turn_token_usage` and `thread_token_usage`. `meter.terminal_usage` holds the matching terminal event’s usage or null when absent. Hash the `meter` object the same way as the plan. The gate checks this digest, unique response IDs, request counts and cumulative counters. Start each workload’s sessions fresh and include their turns from the first receipt. The raw audit checks that each Compound session received both the core skill listing and the saved rule before its first task prompt. Stock sessions must contain neither Compound skill listings nor a saved rule in their host context. The gate reconciles each session’s thread counters across the workload’s attempts. The exporter binds each attempt to the delivered build, fixture and grader.
- Pass `--codex-rollouts <directory>` with the complete logs from the dedicated benchmark profiles. Place each profile’s `sessions` directory or a symlink under that directory as `stock`, `last-good` or `candidate`. The gate checks every started turn and receipt against the ledgers and verifies the delivered prompt, runtime, model, reasoning setting and completion for fully metered turns. It records a fingerprint of the audited files in `raw_rollouts_sha256`.
- A graded initial failure with a repair still pending blocks the Codex workload and retains the initial usage. A graded failure after the repair counts as a correctness regression. A passing Codex gate requires this raw audit and the candidate’s reported total tokens to stay at or below both controls on every workload. `usage_claim_ready` additionally requires strictly lower aggregate total tokens than both controls. `known_usage` keeps the token breakdown for recorded attempts, including partial evidence. Ledgers without raw logs still report these known totals for diagnosis. These are token measurements. Dollar savings require a separate metered comparison.

Exit code 0 requires every workload to pass independent grading in all three arms and clear the provider’s regression check. Exit code 1 identifies a candidate correctness or usage regression. Exit code 2 means evidence is missing, invalid or insufficient for the comparison. The per-control aggregates can be lower even if a workload regresses. Use the matching claim flag before publishing. A later offline grade can explain a false rejection. Keep the grades that governed live repairs and their receipts in the original ledger. The historical audit is informational. This command launches no model or judge.

## Tasks

`python3 bench/bench.py tasks` lists them. `--tasks` takes names or tags.

| Task | Tag | What it checks |
|---|---|---|
| `bugfix-refund`, `bugfix-leap`, `bugfix-december` | `core`, `bugfix` | Fix a clearly reported bug in a small billing library and commit it |
| `refactor-rounding` | `core` | Remove duplicated rounding; the obvious version changes tax amounts |
| `refactor-slugs`, `refactor-retry`, `refactor-money` | `heldout` | Merge two near-duplicate helpers in shopkit, a second small library written after Compound's refactor guide and frozen before any agent ran it; the obvious merge changes one caller (product URLs or facet keys, retrying a charge after a lost connection, or the API's validation and rounding) |
| `review-flask` | `core`, `judged` | Review a Flask commit with three planted defects |
| `review-shopkit` | `judged`, `review-heldout` | Review a shopkit commit that merges all three helper pairs the obvious way: it passes shopkit's own suite, and each merge changes one caller |
| `investigate-django` | `core`, `judged` | Find where Django treats the HTTP QUERY method differently |
| `flask-ipv6-run`, `flask-ipv6-session`, `click-pickle-option`, `click-progress-final` | `real` | Fix a real bug that Flask or click fixed upstream between July and September 2026, in the project's own code and test suite |
| `attrs-evolve-name`, four `packaging-*` and three `marshmallow-*` bugs | `real`, `real-new` | The same, for eight bugs fixed upstream between August and October 2026, frozen on 31 October 2026 before any run; a ninth, from werkzeug, was dropped before any run because its suite starts dev servers that hang in the sandbox |
| `inactive` | `control` | A plain question where Compound should stay out of the way |
| `first-use` | `control` | The December fix in a repository with no check-up yet and the user's own uncommitted notes |

Each real-bug fixture is the project at the parent of the upstream fix, with its history up to that point. The bug report describes only the symptom. The hidden tests are the new tests from the upstream fix, and the project's whole suite must still pass. `setup` checks that these tests fail at the parent and pass on the upstream fix. It also installs each project's test dependencies into `bench/work/pyenv`: as pinned in its `uv.lock` for Flask and click, as resolved on the freeze date for the others, and never the project itself, which runs from its `src/`. Runs see them read-only on `PYTHONPATH`.

Each held-out refactor has a right reference, a naive one that passes shopkit's own suite but changes one caller, and three mutants. The benchmark credits a new or edited test for catching the naive refactor when that same test passes on the original and final source and fails on the naive source. `setup` checks that each hidden test fails only on its naive refactor and that every mutant passes shopkit's suite but fails its hidden test. `review-shopkit` reviews a single commit that applies all three naive refactors; `setup` checks that shopkit's suite passes on it.

Prompts are the same in every arm, apart from a `+prefix:` an arm asks for, and never mention Compound. Write tasks may run code and commit. Read tasks may read and search but never run the project's code. Web access, package installs and network commands are denied in every arm.

## What is measured

- **Habits**, from a `python3` shim that records the exact source and test state at every call, plus a watcher on the working tree:
  - the run reproduced the bug before its first source change;
  - a new test failed on the old code, at any point (some runs check this after fixing, with the fix set aside);
  - a new test failed on the old code before the first source change took effect, the order the habit asks for (an edit counts from when it was applied, so a test run issued in the same step just before it counts as before);
  - the final code passed the full suite.
- **Correctness**, graded outside the run:
  - hidden tests for each bug and for the refactor;
  - the original suite and the run's own suite on its final code;
  - for refactors, existing test IDs and assertion counts are retained;
  - for real bugs, the upstream fix's tests and the project's whole suite.
- **Test strength**: each run's tests are run against frozen wrong or partial fixes (mutants). A test counts as a regression test only if it fails on the buggy code and passes on the reference fix.
- **Commits**: whether the run committed, the author, AI co-author trailers and "generated by" lines, and the subject style.
- **Answers**: a blind judge with no tools grades each review or investigation answer against a frozen key. It quotes the answer verbatim for every item it marks as met, and quotes that don't match the answer are discarded; line breaks and list, heading and bold markers don't count, so a quote that runs across two bullet points still matches, and a quote that elides words with "..." matches when every part of it is in the answer. Tooling mentions and absolute paths are removed first, in every arm.
- **Cost and time**: list-price cost and tokens as Claude Code reports them, wall time, tool calls, map and skill use.
- **Validity**, decided before grading: the model served, the plugin loaded only in plugin arms, the control never seeing Compound, no leftover processes or held ports.

For a native Python trial, launch test commands through [the Python shim](shim/python3) using the trial's Python interpreter. Set `COMPOUND_BENCH_TRACE_ROOT` to the absolute checkout path and `COMPOUND_BENCH_TRACE_LOG` to a fresh absolute log path outside that checkout for each attempt. The shim observes `python -m pytest` and `python -m unittest` when run from the checkout. It records the exit code and hashes the bytes of `.py` files under `src/` and `tests/` before and after each observed command. For unittest, it forwards stderr and records the test count from the suite summary. Missing records leave the verification steps unobserved. Independent grading still evaluates the final artifacts.

## Add a task for a new feature

1. Pick or build a fixture. Small synthetic projects go in `data/` and are built in `fixtures.py`, with a frozen tree and commit metadata so rebuilds stay identical. Upstream projects get a pin in `fixtures.PINS`.
2. Add the task to `TASKS` in `tasks.py`: `fixture`, `kind` (`write` or `read`), a `prompt` written the way a user would write it, a `timeout`, `tags`, and a `grade(project, record, prep)` function that returns outcome fields. Give bug reports a `symptom` regex so the reproduction habit can be detected.
3. Keep answer keys out of the fixture. Hidden tests go in `data/hidden/`, reference fixes and mutants in `fixtures.py`, judge keys in `tasks.JUDGE_KEYS`.
4. Check the grader on known-good and known-bad results. `setup` does this for the existing tasks: every hidden test must fail on the fixture and pass only on its reference fix, and every mutant must survive the fixture's own suite.
5. Include a task where the feature should stay inactive, and compare the old and new plugin in the same run with `--arms old=ref:main,new=worktree`.

## Map benchmarks

```bash
python3 bench/bench.py setup --map
```

```bash
python3 bench/bench.py map-speed --plugin worktree
```

```bash
python3 bench/bench.py map-retrieval --plugin ref:main
```

- `map-speed` times builds and agent queries on Django, Vue core, Gin and ripgrep at pinned commits: cold, unchanged, after a one-file edit, and through the local service.
- `map-retrieval` checks whether the map ranks the files that real Flask, click and Hono commits touched, against a word-count search and chance. Use `--retain-history` to measure ranking with the real parent and its Git ancestry. The report records the fixture mode and the real parent revision for each history-enabled query. The default uses one-commit snapshots for comparison with prior runs.

Neither benchmark runs an agent or executes repository code. For a quick offline check that needs no setup, `python3 scripts/benchmark_code_map.py` builds a small synthetic repository in every supported language. It checks that the map and symbol lookup find each planted definition, and times them.

## Reading results

Compare arms only within one run. Models, Claude Code and its feature flags change over time, so the report records the Claude Code version and the models it served. Each run's folder keeps the full stream transcript (`.stream`), the record (`.json`), the diff, the final `src/` and `tests/`, and the judge's votes.

## Offline summary comparison

`python3 -B bench/map_context.py --baseline-ref 890022e` compares that trusted local plugin revision’s text renderer with the working copy’s renderer on identical map metadata. It makes no model or network calls and reads the five existing source checkouts pinned in `fixtures.py`; it refuses a different revision or a dirty checkout. The 15 fixed queries are listed in the script. `--sources` chooses an existing source directory and `--baseline-repo` chooses a local plugin checkout containing the baseline revision.

On 2 November 2026, the full query outlines totalled 97,350 UTF-8 bytes before and 76,283 after (21.6% fewer). Inside the same 2,500-character cap, the median number of complete file entries increased from 3 to 4; none of the 15 pairs displayed fewer complete entries. Full outlines exceed the default cap: this byte reduction is not a measurement of fewer billed tokens. The renderer leaves ranking and JSON metadata unchanged; it retains up to eight query-matching symbols per file and otherwise includes two symbols for orientation. This is a presentation comparison within Compound, not an agent navigation or task-quality comparison against stock.

## Compare saved costs

```bash
python3 -B bench/bench.py cost-audit --label v016b --baseline without --candidate final --tasks heldout
```

This reads saved results only. `without` is stock and `final` is the recorded 0.16.0 Compound arm. The comparison requires the same tasks, repetitions, pair IDs, fixture revisions, prompt hashes, permission settings and served models, and includes recorded unsuccessful, invalid and superseded spend. Missing usage or ungraded outcomes remain unknown. Judge spend is excluded.

`saved_batch_cost_target_met` is true only when the candidate costs strictly less per task with no fewer accepted results in the matched saved cohort. It is unknown when costs or graded outcomes are incomplete. This is an observed batch check, not a statement about future work or lifetime cost. Changes to prompts do not change historical records.

## Replay saved navigation queries

```bash
python3 -B bench/replay_map_queries.py --results bench/results/v016b --fixtures bench/work/fixtures --baseline-ref e2e3ae3
```

This parses the saved arm's map commands as data, checks that each existing fixture is clean at its recorded revision, and renders the same map metadata with the trusted local baseline and current renderer. It never executes a saved shell command, runs project code, fetches sources or calls a model. It rejects loss of a ranked path, a previously visible matching declaration, or complete file entries, and checks that rendering leaves metadata unchanged.

For the seven saved 0.16.0 `final` map calls on the frozen shopkit fixture, the 0.16.3 renderer emits 15,741 UTF-8 bytes and the query-only renderer emits 12,200 (22.5% fewer). All twelve ranked paths remain visible in every replay; imports, coverage and matching declarations are retained. Only unrelated symbol outlines are left unexpanded. The full JSON and viewer retain all outlines. This measures actual renderer output on saved queries, not a new agent run or a billed-cost reduction.

The same traces contain refactor baselines before characterization cases followed by another baseline after adding them, test-command retries, and longer source reads. The guides now put needed cases before one baseline, reuse fixtures and current passing evidence, batch independent lookups, and start with narrow source ranges. Their effect on later model actions has not been measured. The discovery descriptions are unchanged; the core entrypoint shrinks from 4,929 to 4,575 bytes by deferring optional navigation details, and the always-on rule stays at 633 bytes.

## Generate README diagrams

All README visuals are generated by [render_readme_diagrams.py](render_readme_diagrams.py) from the [shared theme, historical vector scenes and saved pilot measurements](diagram_sources/README.md). Regenerate them without model or network calls:

```sh
python3 -B bench/render_readme_diagrams.py
python3 -B bench/render_readme_diagrams.py --check
```

The historical scenes preserve their original numbers and measurement scope. The current pilot uses exact saved provider usage fields; it does not reprice historical Claude Code runs or establish long-term savings.

## Cumulative Y Harness workflow

The [completed six-change comparison](../README.md#completed-workflow-six-changes-with-repairs) uses the existing `bugfix-refund`, `bugfix-leap`, `bugfix-december`, `refactor-slugs`, `refactor-retry` and `refactor-money` prompts and fixtures in `tasks.py`. Each mode keeps its repository state and native conversation across each three-task group. A reproduction uses an isolated Y Harness headless profile configured for the same provider/model, reasoning, output cap and instructions:

```sh
yharness --profile <isolated-profile> --json "<first task prompt>"
yharness --profile <isolated-profile> --session-id <session-id> --json "<next task prompt>"
```

Verify the actual model-facing read, search, write, edit and shell tools without a model first. Both modes must see their fixture and required tools while host benchmark plans, graders and opposite-mode states stay unavailable. After each attempt, independently check all tasks completed so far, the original suite on the changed source, the final suite, test removal/weakening and the refactor duplicate-removal requirement. A failing check supplies the same kind of feedback and repair opportunity to either mode. Retain every implementation, repair and provider-recovery attempt.

The [public numeric source](diagram_sources/workflow.json) includes the completed sequence's pins, prompt hashes, attempt grades, request counts, known usage and missing-usage flags. Exact cost fields remain `null` when usage is unreported; recorded amounts are lower bounds. The renderer verifies attempt, stage and sequence totals before drawing. The 3 November continuation follows the original task list and preserves the interrupted conversations; it is recorded separately from the initial plan. Raw transcripts and private runner configuration remain local under ignored `results/`.

## Profile local map queries

The 0.16.8 query implementation reuses one safely opened repository directory for the candidate content reads. The [saved offline profile](diagram_sources/map_query_profile.json) compares 15 identical query/repository pairs over five pinned Python repositories: **9,403 → 2,083 file-open calls**, including **747 → 15 walks from the filesystem root**. All 15 complete ranked-path hashes match. Candidate budgets and content freshness remain unchanged; no source bytes are cached by this optimization.

This removes 480–490 repeated directory opens per query in these source locations, about 78% of open calls in total. Ancestor depth affects the saving. Wall-time medians improved in 9/15 pairs and worsened in 6/15 on the shared macOS host; timings are retained, and no latency multiplier or model-cost saving is claimed. This is an implementation profile, separate from the README's without/with task and retrieval comparisons.

To reproduce without model calls, export the pre-change scripts and run the same profiler against both directories. Use the pinned source revisions in the JSON, the same query strings, and an idle host if interpreting latency:

```sh
mkdir -p bench/work/query-before
git archive 97865fbdcd22498d39f8746121154b1b07859879 skills/compound/scripts | tar -x -C bench/work/query-before
python3 -B bench/profile_map_query.py --repo /path/to/flask --scripts bench/work/query-before/skills/compound/scripts --query "how are requests routed to handlers" --query "configuration load defaults" --query "error handling exceptions"
python3 -B bench/profile_map_query.py --repo /path/to/flask --query "how are requests routed to handlers" --query "configuration load defaults" --query "error handling exceptions"
```

The profiler separates index construction and three warmups from the timed ranking loop, reports median/minimum/p95 wall time and median process CPU time, counts opens separately from timing, and hashes all ranked paths. Different hashes invalidate a behavior-preserving speed comparison. It reads source text without executing repository code. Raw source and private traces remain outside the published data.

A paired offline replay against `4fe07d3` alternated the two rankers over the same warmed index, with 21 repetitions for each query. On Flask (125 indexed files), median ranking CPU fell 2–9% across five queries. On Django (3,496 files), it fell 17–32% across five queries. Full ranked paths, matching files, and source-read counts and bytes matched in every query. The reuse is bounded to path classifications and symbol-name terms in memory. These measurements cover local ranking after indexing.

A paired replay against `426c835` used the same five queries per repository and alternated the rankers for 21 repetitions. In 0.16.57, median ranking CPU fell 6–12% on Django and changed by less than 2% on Flask. Full ranked paths, matching files, and source-read counts and bytes matched in all ten cases. The ranker reuses test-path classifications and scores metadata only when it matches a query term. This measures local ranking with a warm index.

A 0.16.64 paired replay against `68b1beb` alternated rankers for 25 repetitions per query. On five Django queries, median ranking CPU fell 17–26%. On five Flask queries, it fell 15–23%. Ranked paths, match sets, every scanned file and the source bytes read matched in all ten cases. The scanner splits ASCII identifiers directly from bytes and retains normalized Unicode processing when the query and file need it. This measures local warm-index ranking.

## Semantic lookup inventory

0.16.66 reuses the repository inventory for both source validation and result filtering. A local replay against `4918876` alternated the adapters for 15 lookups per repository with the deterministic LSP server from the local tests. Git subprocesses fell from eight to four on pinned Flask and Django checkouts, with identical definition, reference, and coverage JSON. Median adapter time including server startup fell from 125 to 76 ms on Flask and 325 to 179 ms on Django. The server fixture measures adapter overhead independently of language-server analysis.

0.16.67 also validates each URI once per response. In 11 alternating pairs per repository, a fixture server returned 2,000 locations in one file. Safe file opens fell from 2,002 to three per lookup. Median adapter time fell from 398 to 81 ms on Flask and from 498 to 178 ms on Django. Sparse responses used three opens in both versions, and every lookup returned identical JSON. These timings include local server startup and measure adapter work with a synthetic response.

## Saved model-work audit

The [saved call audit](diagram_sources/work_audit.json) reads the completed Y Harness / DeepSeek V4.1 Flash sequence as data: 72 model requests and 116 tools with Compound, 61 and 92 without. Slugs account for eight of the eleven extra requests. Three treatment edits and one control edit were rejected by read prerequisites. Both modes' initial Git identity failures remain counted; they are an environment limitation, not evidence of a Compound prompt defect. The annotations identify the relevant saved steps and resulting prompt/code changes without deducting hypothetical future savings.

```sh
python3 -B bench/trace_work_audit.py --runs bench/results/deepseek-sequence-20261102/clean/runs
```

The auditor checks event counts against each record, includes failed implementations, repairs and transport recovery, and emits hashes and counts without command bodies or private paths. It never runs a recorded command, invokes Y Harness, contacts a provider or substitutes a model. Raw saved events are local and ignored; the sanitized audit is public.

The [navigation replay](diagram_sources/navigation_replay.json) feeds the saved slug map query to the previous and current local implementations on the exact clean `shopkit` revision. Complete `files` metadata and ranked `focus` paths must match. The current text lists only candidates with path, symbol/declaration or scanned-content evidence; content-only matches survive, and an empty result directs the agent to native search rather than arbitrary files. JSON and the viewer retain the full index. Lexical evidence is not a semantic dependency: the retained payment/webhook hits still need task relevance before reading.

```sh
python3 -B bench/replay_navigation_scope.py --events bench/results/deepseek-sequence-20261102/clean/runs/06-refactor-slugs-with-0/events.jsonl --fixture bench/work/fixtures/shopkit --fixture-head cdd6e88a0e51b7b6c46e7920404dbc44b2af28b4 --baseline-ref f1a916f
```

This replay rebuilds metadata without a cache or service; it is not the original agent execution. It verifies presentation behavior and preserved index data, not future calls, repairs, billed costs or prompt compliance. No new DeepSeek requests were made. Correctness checks remain required; a check is redundant only when an existing passing assertion covers the same behavior. The new guide asks for a named coverage gap before extra probes, rather than treating every old probe as deletable.

## Inspect saved request steps

```sh
python3 -B bench/trace_work_audit.py --runs bench/results/deepseek-v0169-small-20261103/runs --steps
```

`--steps` reads the saved request meter alongside native events. Each request retains tool names, recorded allowance, completion tokens and reported reasoning tokens, including responses without tools. Native turn-end reasons remain visible; a billed reasoning-only response ending at the output cap is retained. Missing reasoning breakdowns stay unknown, and invalid or inconsistent token counts fail validation. Missing usage stays unknown; duplicate/out-of-range responses and invalid allowance values fail validation. Commands and model text are not emitted or executed. Output without `--steps` is unchanged.

The [0.16.9 work review](diagram_sources/work_review_v0169.json) links observed scope hunts, duplicated baseline work and post-check cosmetic edits to the 0.16.10 guidance changes. It distinguishes mixed steps and necessary functional corrections from optional work. The [original comparison](diagram_sources/comparison_v0169.json) remains unchanged: 42.1% more allowance with Compound, both modes correct after repairs. Annotated step spend is not subtracted from the bill or treated as forecast savings. No new model runs were made; whether the revised guidance reduces requests or total cost remains unmeasured.

## Saved 0.16.10 work review

The [0.16.10 comparison](diagram_sources/comparison_v01610.json) retains all 47 requests: control completed three refactors; Compound completed one and stopped at the common 8,192-token response cap on the second. Its smaller aggregate spend covers less completed work. On the completed first task, Compound consumed $0.02319515 allowance versus $0.01397918 including control's repair. The [work review](diagram_sources/work_review_v01610.json) links saved request numbers and numeric usage to the changes in 0.16.11. It separates necessary behavior correction from speculative design and late test/comment work; annotated response costs are never subtracted as hypothetical savings. No new model runs have tested the revised guidance, so neither cheaper completion nor prevention of future output-cap failures is established.

## Saved 0.16.11 work review

The [0.16.11 comparison](diagram_sources/comparison_v01611.json) used 38 requests with Compound versus 29 without, with 3/3 accepted tasks and one repair in each mode. Compound consumed 75.5% more Go allowance. The [work review](diagram_sources/work_review_v01611.json) links the nine extra requests and the larger reasoning total to invalid characterization baselines, changed caller expectations, rejected repair edits and an unused helper default added after passing checks. It distinguishes useful coverage from mixed or discretionary work and preserves every recorded charge.

0.16.12 delivers caller-preserving extraction semantics through generated project/global rules, Cursor and chat activation. Its refactor guide characterizes existing callers before a passing baseline, retains those expectations, satisfies host-required read grants before repair edits, and excludes unused helper APIs and duplicate probe scripts. Offline fixture checks reproduce the missing-helper import failure, pass caller characterization on original source, and reject the naive behavior-changing extraction. Setup migration checks verify that old rules are flagged and refreshed without touching unrelated configuration. No new model runs establish prompt compliance or lower total cost; the main README benchmark claims and graphics remain unchanged.

## Reusing final checks

In the [saved Dispatchkit bug-fix comparison](diagram_sources/comparison_dispatch_v01615.json), the control's suite passed at request 8. Diff inspection and bytecode cleanup followed, then request 11 repeated the suite with bytecode disabled and no intervening source or test edits. Compound ran its final suite after its last edit. In the [older failed Compound slug attempt](diagram_sources/work_audit.json), requests 12 and 13 both ran the same seeded 5,000-input product check. The second probe investigated a facet mismatch, so only its repeated product check was redundant.

The 0.16.23 default rule is 754 UTF-8 bytes, down from 804, at 100 words in both versions. It directs agents to reuse passing checks on unchanged inputs and environments. The bug guide counts the final suite as the regression confirmation when it includes that test. The refactor guide reruns only the unresolved part of a combined probe. The saved comparison keeps every attempt and charge.

## Grouping source edits

```sh
python3 -B bench/replay_refactor_patch.py
```

The accepted Sonnet retry refactor in `v016b` sent six replacements and one file creation in a single assistant message. The replay combines those literal edits into one patch against the frozen fixture and checks all three resulting files against the saved artifact byte for byte. The earlier test edit, pre-edit baseline and final suite are separate phases. This checks patch equivalence and tool operations. It uses no model calls or recorded shell commands and makes no estimate of billed savings. [Replay counts and hashes](diagram_sources/refactor_patch_replay_v01626.json).

The global setup and status shortcuts also link directly to the activation reference. Their explicit instruction path no longer includes the previous 5,278-byte engineering skill body. This is a source-size measurement.
