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

#### Fresh dispatchkit sequence

[Dispatchkit](data/dispatchkit/tasks.json) is a small, dependency-free Python workload with two consecutive changes. The first reports a webhook routing symptom without naming a file or function. The second asks for a shared helper while preserving two caller policies. Each mode starts from the same clean fixture. Its code and conversation carry forward between tasks, with opposite mode order on the second task.

The grader runs both tasks' hidden checks after the refactor, runs the original tests against the changed source, and checks the agent's final test suite and retained original tests. It also reruns the added bug regression on the original source and requires a failure. Only the fixture goes into either agent workspace. The hidden checks and the preserving and wrong variants stay outside the agent workspaces.

Run the fixture and grading preflight without a model or Docker:

```sh
python3 -B bench/yharness_dispatch.py --validate bench/data/dispatchkit
```

The preflight requires the original bug, an unfixed refactor, a behavior-changing extraction and a lost earlier fix to fail. It requires the independently written fixes to pass. Any live run uses the same settings and one repair or recovery opportunity per task in both modes. The verdict uses every recorded attempt and requires both modes to finish both tasks before comparing allowance, list-price usage and cash charges.

In a prepared run directory, copy `yharness_verdict.py` beside the runner and use `python3 -B run.py --summary` to evaluate saved usage and grades. It does not dispatch requests. The fixture preflight needs neither a run directory nor a provider key.

[The 0.16.31 Dispatchkit comparison](diagram_sources/comparison_dispatch_v01631.json) uses the same tasks and reverses the mode order from the [0.16.15 run](diagram_sources/comparison_dispatch_v01615.json). Its ledger includes all four first-pass attempts, both task grades and the provider-reported cache and usage totals.

The [saved Dispatchkit trace audit](diagram_sources/work_review_dispatch_v01615.json) separates the two stages. The bug-fix runs reported 25.5% versus 85.9% cached input without and with Compound. On the follow-up refactor, cached input shares were closer at 90.8% and 94.0%. Compound used 13 versus 9 requests on the refactor, with 2,479 versus 6,762 reported reasoning tokens and lower billed allowance. The audit identifies extra searches and generated-file cleanup in that run, retains every charge and makes no estimate for a different cache state.

#### Scoped refactor replay

In the [0.16.31 Dispatchkit comparison](diagram_sources/comparison_dispatch_v01631.json), the Compound refactor spent its first two requests loading the skill and refactor guide. Its baseline and extraction checks passed by request 8. Requests 9–14 searched for more context, rewrote the helper signature and reran checks. Those six requests used $0.00505071 of Go allowance.

An offline replay reversed the three saved signature-related edits in a copy of the final artifact. The same network-disabled grader accepted both states. Both preserved the earlier routing fix, passed the hidden refactor checks, kept the original tests and passed all six final tests. The 0.16.32 saved rule routes this kind of scoped extraction directly and gives it a finish point after the required checks and diff review. The replay measures the saved work and checks the two artifacts. The new routing has no live cost measurement.

#### Checkout scope in saved refactors

Two saved Compound refactors searched outside their checkouts after the relevant source was available. The slug refactor spent requests 6 and 7 on a surrounding directory and instruction search, using $0.00395534 of Go allowance. The Dispatchkit refactor had passed its checks before requests 10–12 searched parent directories and the benchmark tree, using $0.00163497. These searches returned no new implementation evidence. The figures describe the five recorded requests. [Slug comparison](diagram_sources/comparison_v0169.json) · [Dispatchkit comparison](diagram_sources/comparison_dispatch_v01631.json)

The 0.16.37 saved rule keeps discovery for scoped extractions in the checkout. The full guide starts with named files and expands only for a concrete external caller or dependency. The next matched comparison used this rule.

#### Direct routing and edit reads

The saved 0.16.37 Dispatchkit comparison used 27 requests with Compound and 15 without. Both modes passed both tasks on their first attempts. Go allowance was $0.00610678 with Compound and $0.00405995 without.

The Compound bug fix used 15 requests for 14 tool calls. The baseline used nine requests for 14 calls. The first edit failed the editor's read prerequisite after a shell read, so the agent read the test again through the native tool. On the scoped refactor, the first two requests loaded the skill and its refactor guide before opening the named files. Those two requests used $0.00027731 of allowance. Two more requests searched the fixture and its Git history before opening the named callers. Those searches used $0.00073959 and found no new implementation evidence.

The 0.16.38 rule puts the editor's required read tool first, asks the agent to batch independent calls and search for unknowns, and routes scoped extractions directly through the saved guidance. Offline checks verify rule delivery. Total cost on the revised rule remains unmeasured.

#### Consecutive upstream Flask fixes

This sequence starts both modes at Flask commit `514fc6b`. Fix the IPv6 test-client session bug first and the IPv6 development-server parsing bug second. The existing real-bug benchmark used the individual tasks separately. This sequence keeps the same checkout and conversation within each mode, then checks that the second change preserves the first.

After building the frozen Flask fixtures and test dependencies, validate the sequence offline:

```sh
python3 -B bench/bench.py setup --real flask-ipv6-session,flask-ipv6-run
python3 -B bench/yharness_flask_sequence.py preflight
```

Setup fetches pinned inputs if needed. Preflight uses local copies and prints the starting revision, fixture hash, prompts and grades. The starting repository has one branch, no remotes and neither upstream fix. Keep the preflight report, upstream repository and grading files outside the agent workspaces. Both modes receive the same prompt for each stage. Reverse the order of the modes between stages.

Grade each candidate in a disposable, network-disabled runner with read-only inputs and the matching Python environment. Mount the fixture and reference tests there with the benchmark work layout. Save the accepted first-stage snapshot outside the agent workspace before the next task.

```sh
python3 -B bench/yharness_flask_sequence.py grade 1 /input/project
python3 -B bench/yharness_flask_sequence.py grade 2 /input/project --previous /input/accepted-stage-1
```

To use the existing Y Harness completion runner, set `grader` to `flask-sequence` in the frozen plan. Use the preflight fixture and task list for the sequence. Copy `yharness_flask_sequence.py`, `common.py`, `fixtures.py`, `tasks.py` and `probe_pytest.py` into the prepared run's `grader/`. Place the two `refs/real/flask-ipv6-*` directories and the pinned `pyenv/flask` under `grader/work/`. The scrubbed fixture belongs in `fixtures/flask-ipv6-session`. Run `python3 -B run.py --flask-input-hashes` in the prepared directory and save its JSON as `flask_input_hashes` in the plan before hashing the plan. Use Python 3.11 with current security updates or newer on the runner host.

The runner checks these inputs before each attempt and checks the two starting copies against the frozen fixture. It grades each archived source and test snapshot in the separate container. Before task two, it verifies the accepted snapshot from the same mode, checks that the live source and tests still match it, and resumes that mode's session. Both task-two attempts use the same read-only baseline. Repair prompts give feedback without private grader output. Keep the grader bundle and run records off the model's mounts.

The grader runs the cumulative hidden checks and the original, previous and final test suites where applicable. At each stage it requires an added or changed regression to fail on the preceding source and pass on the current source. In preflight, the full reference passes 493 tests. The grader rejects a missing fix, a second fix that drops the first, a missing second regression and removal of the first regression. These are offline correctness checks. Usage and cost require a separate metered comparison.

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

The check installs a Git archive through each host's local marketplace in a temporary home. From the installed copy it checks the five skill files, global setup, status, idempotence and removal, plus a read-only map and the local viewer's HTML and CSS. It preserves an existing instruction and checks paths containing spaces. It also corrupts the temporary metadata, runtime and registry files, verifies a read-only query, then checks recovery through the live viewer. It uses no model calls. Pass `--host codex` or `--host claude` for one host. The 0.16.30 check used Codex CLI 0.162.1, Claude Code 2.1.312 and Python 3.11.15.

## Audit costs without new runs

```bash
python3 bench/bench.py cost-audit --label <saved-label>
```

This command only reads saved records and works without Linux or Claude Code. It makes no model or judge calls. Each task, model and arm reports recorded spend, accepted results (`outcome.success`), unresolved valid attempts, ungraded results, invalid attempts and superseded attempts, plus token and tool-call totals. Recorded spend includes invalid and superseded attempts rather than dropping their cost when the benchmark retries a group. Missing costs or a run without a final usage record leave spend per accepted result unknown; ungraded answers are not counted as failed fixes. Judge costs are excluded.

Spend per accepted result is the batch's recorded spend divided by accepted results, including spend on unsuccessful attempts. Existing runs do not link agent correction sessions or sequences of project changes, so this is an audit of first-attempt batches, not a measurement of long-term savings. It does not estimate how many retries would succeed.

### Source-first review trace replay

In the saved second-round Flask review, four runs per mode found all three planted defects. Both stock Sonnet runs used one diff read each. Across all four runs per mode, Compound used 28 tool calls in 21 assistant messages, versus 11 calls in nine messages without Compound. Each Compound run attempted runtime setup after reading the diff. After the first denial in each run, they made 11 more denied Bash calls and five successful scratch writes or edits.

The pinned source exposes the three mechanisms in the changed method. The closure shares the loop's directory binding, the cache fallback treats zero as unset, and the file-serving call joins an unchecked filename. The 0.16.36 saved rule asks reviews to probe only when source evidence is insufficient and execution is permitted. The explicit review guide also limits scratch reproductions to required work or a concrete gap that needs a permitted probe. These are saved counts and source checks. Review costs on the revised rule remain unmeasured. [Historical review comparison](historical-comparisons.md#where-it-doesnt-help-reviews).

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

Replay the default text response for 50 exact paths from pinned Flask and Django checkouts, using the same index for both renderers:

```sh
python3 -B bench/map_exact_path.py --baseline-ref 5357032 --summary
```

Ranking probes fell from 2,500 to zero, avoiding 53,672,632 source bytes in the summary phase. Total emitted text fell from 113,688 to 39,925 bytes, a 64.9% reduction. The summaries kept the same indexed record for each target. Three grew because the single-file layout could show more of the target outline. Four topic and miss controls stayed byte-identical with the same reads. These counts exclude Git and indexing work.

A direct CLI replay against `b9db91b` queried `./src/flask/wrappers.py` and `./django/urls/base.py` at the same repository pins with `--max-files 3 --max-chars 500`. Each path ran with `--no-cache`, `--cache-read-only` after priming, and a simulated unavailable service after priming. Across the six commands, query ranking went from 300 source probes and 5,564,763 bytes read to zero. All six responses were byte-identical, indexing parse counts matched, and read-only and no-cache state stayed unchanged. The replay used local files and no model requests.

## Warm map query work

Compare live CLI queries on clean, pinned Flask and Django checkouts under `bench/work/sources/`. Run from the 0.16.21 checkpoint:

```sh
python3 -B bench/map_warm_work.py --baseline-ref 85f2616
```

Each version warms an isolated local map service once per checkout and then repeats the same focused query three times. Git Trace2 counts processes started by both the CLI and the service. Every warm query used 6 Git subprocesses, down from 12, and both versions printed the same summary bytes. The remaining file inventory and status checks keep the map fresh. This measures local subprocess work with zero model calls. [Counts and source pins](diagram_sources/map_warm_work_v01621.json).

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

Each held-out refactor has a right reference, a naive one that passes shopkit's own suite but changes one caller, and three mutants. `setup` checks that each hidden test fails only on its naive refactor and that every mutant passes shopkit's suite but fails its hidden test. `review-shopkit` reviews a single commit that applies all three naive refactors; `setup` checks that shopkit's suite passes on it.

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
  - for real bugs, the upstream fix's tests and the project's whole suite.
- **Test strength**: each run's tests are run against frozen wrong or partial fixes (mutants). A test counts as a regression test only if it fails on the buggy code and passes on the reference fix.
- **Commits**: whether the run committed, the author, AI co-author trailers and "generated by" lines, and the subject style.
- **Answers**: a blind judge with no tools grades each review or investigation answer against a frozen key. It quotes the answer verbatim for every item it marks as met, and quotes that don't match the answer are discarded; line breaks and list, heading and bold markers don't count, so a quote that runs across two bullet points still matches, and a quote that elides words with "..." matches when every part of it is in the answer. Tooling mentions and absolute paths are removed first, in every arm.
- **Cost and time**: list-price cost and tokens as Claude Code reports them, wall time, tool calls, map and skill use.
- **Validity**, decided before grading: the model served, the plugin loaded only in plugin arms, the control never seeing Compound, no leftover processes or held ports.

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
- `map-retrieval` checks whether the map ranks the files that real Flask, click and Hono commits touched, against a word-count search and chance.

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
