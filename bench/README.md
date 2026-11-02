# Benchmark

This folder holds the harness behind the results in the [main README](../README.md#benchmark). It runs headless Claude Code side by side on fixed engineering tasks, once per arm: no plugin, this checkout, any other version of Compound, or another plugin. Then it grades what each run did and what it left behind. Rerun it whenever a change to the skills, references, rules or scripts could change how agents work.

Nothing here is loaded by Claude Code, Codex or Cursor. Results stay on your machine in the ignored `bench/results/` folder, and fetched sources stay in the ignored `bench/work/` folder.

## Requirements

- Linux, as root or with unprivileged user namespaces. Every run gets its own mount and PID namespace, through `unshare` and `taskset` from util-linux.
- The `claude` CLI, `git`, Python 3.11 or newer at `/usr/bin/python3` with `pip`, and network access for the first `setup`. `map-retrieval` also needs ripgrep (`rg`).
- Sign-in that works without your home directory. Runs can't see `/root` or `/home`, so pass a token with `BENCH_PASS_ENV=ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`). Alternatively, keep a folder visible read-only with `BENCH_KEEP=<dir>[:<dir>...]` or `--keep <dir>` before the command. Folders that hold the proxy CA files named by `NODE_EXTRA_CA_CERTS` or `SSL_CERT_FILE` stay visible automatically.

Every run is a real agent session billed to your account. Cost grows with arms × tasks × models × repetitions, and `report` shows the measured cost per task.

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

## Audit costs without new runs

```bash
python3 bench/bench.py cost-audit --label <saved-label>
```

This command only reads saved records and works without Linux or Claude Code. It makes no model or judge calls. Each task, model and arm reports recorded spend, accepted results (`outcome.success`), unresolved valid attempts, ungraded results, invalid attempts and superseded attempts, plus token and tool-call totals. Recorded spend includes invalid and superseded attempts rather than dropping their cost when the benchmark retries a group. Missing costs or a run without a final usage record leave spend per accepted result unknown; ungraded answers are not counted as failed fixes. Judge costs are excluded.

Spend per accepted result is the batch's recorded spend divided by accepted results, including spend on unsuccessful attempts. Existing runs do not link agent correction sessions or sequences of project changes, so this is an audit of first-attempt batches, not a measurement of long-term savings. It does not estimate how many retries would succeed.

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

## Compare saved costs and recovery scenarios

These commands read a saved label and never start an agent, judge, source setup or network request:

```bash
python3 -B bench/bench.py cost-audit --label v016b --baseline compound --candidate final --tasks real
python3 -B bench/bench.py cost-audit --label v016b --baseline without --candidate final --tasks heldout
```

In this label, `without` is stock, `compound` is Compound before selective routing, and `final` is 0.16.0 as shipped. `--tasks` accepts the same names and tags as the benchmark. The comparison refuses missing tasks, unmatched repetitions, duplicate active attempts, different pair IDs, fixture revisions, prompt hashes, permission settings or served models. It includes recorded costs from invalid and superseded attempts in the selected cohort. Missing usage, invalid active attempts or ungraded outcomes prevent an accepted-cost or failure-rate scenario from being established; ungraded answers are not treated as failed fixes. Judge spend is excluded.

Mean cost per task is cohort spend divided by active task repetitions. Cost per accepted result is the same spend divided by valid accepted results; unsuccessful spend stays in the numerator. These arithmetic summaries are distinct from `report`’s task-weighted geometric means of paired ratios. For the README’s saved refactor cohort, Opus spend is $0.9730812 stock versus $1.6040212 Compound, with 4 versus 6 accepted results; Sonnet spend is $0.3947231 versus $0.606608, also with 4 versus 6. The tests left behind detect 0/36 versus 36/36 planted wrong refactors across both models.

The recovery scenario divides the extra mean initial cost by the difference in observed failure rates. It returns no threshold when Compound has no observed failure-rate advantage. Opus’s threshold is $0.31547 and Sonnet’s is $0.10594245 per avoided failure. This calculation assumes the observed rates recur and a common recovery cost per failure. It measures no corrections, human time, future failures or lifetime savings. The small batch has six refactor attempts per mode and model. Newer instruction wording is not evaluated by these saved runs.
