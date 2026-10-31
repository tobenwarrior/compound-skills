# Benchmark

This folder holds the harness behind the results in the [main README](../README.md#benchmark). It runs headless Claude Code side by side on fixed engineering tasks, once per arm: no plugin, this checkout, or any other version of Compound. Then it grades what each run did and what it left behind. Rerun it whenever a change to the skills, references, rules or scripts could change how agents work.

Nothing here is loaded by Claude Code, Codex or Cursor. Results stay on your machine in the ignored `bench/results/` folder, and fetched sources stay in the ignored `bench/work/` folder.

## Requirements

- Linux, as root or with unprivileged user namespaces. Every run gets its own mount and PID namespace, through `unshare` and `taskset` from util-linux.
- The `claude` CLI, `git`, Python 3.11 or newer at `/usr/bin/python3` with `pip`, and network access for the first `setup`. `map-retrieval` also needs ripgrep (`rg`).
- Sign-in that works without your home directory. Runs can't see `/root` or `/home`, so pass a token with `BENCH_PASS_ENV=ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`). Alternatively, keep a folder visible read-only with `BENCH_KEEP=<dir>[:<dir>...]`. Folders that hold the proxy CA files named by `NODE_EXTRA_CA_CERTS` or `SSL_CERT_FILE` stay visible automatically.

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

- `setup` fetches the pinned sources and builds the fixtures. It checks each fixture against the frozen original and makes the template Claude config. Run it once; it reuses what it already fetched.
- `run` runs every arm on the same task at the same moment, each on its own CPU, and rotates the arm order and CPUs by repetition. Rerunning a label resumes it. If a group fails on an API or harness error, it runs once more. To stop after the groups already running, create `bench/results/<label>/STOP`. Runs also stop on their own when seven-day usage reaches 80% (`--max-seven-day`).
- `judge` blind-grades the review and investigation answers against frozen keys, with three votes per answer.
- `report` prints per-arm tables and paired tests against the baseline. It also writes `summary.json` and `summary.md` into the label's folder.

Add `--models opus,sonnet` to cover both models. Each model gets its own tables, because a change can help one and not the other.

## Arms

| Arm | What runs |
|---|---|
| `without` | No plugin and no rule |
| `with` | This checkout, including uncommitted changes |
| `rule` | No plugin; a short generic habits rule (reproduce, failing test first, full suite) instead |
| `name=worktree` | This checkout under another name |
| `name=ref:<revision>` | Any commit, tag or branch of this repository, such as `ref:v0.13.0` or `ref:main` |
| `name=dir:<path>` | A plugin folder on disk with `.claude-plugin/plugin.json` |
| `name=none` or `name=rule` | No plugin, under another name; `a=none,b=none` measures noise between identical arms |

Plugin arms run from a snapshot named by its content hash. The snapshot leaves out `bench/`, which holds the answer keys, along with `tests/` and `.git`. Before each run, the arm's own `project_setup.py enable --global --host claude` writes its always-on rule. Write tasks also record the one-time repository check-up as completed, so runs measure everyday use. The `first-use` task measures the check-up itself.

## Tasks

`python3 bench/bench.py tasks` lists them. `--tasks` takes names or tags.

| Task | Tag | What it checks |
|---|---|---|
| `bugfix-refund`, `bugfix-leap`, `bugfix-december` | `core`, `bugfix` | Fix a clearly reported bug in a small billing library and commit it |
| `refactor-rounding` | `core` | Remove duplicated rounding; the obvious version changes tax amounts |
| `review-flask` | `core`, `judged` | Review a Flask commit with three planted defects |
| `investigate-django` | `core`, `judged` | Find where Django treats the HTTP QUERY method differently |
| `flask-ipv6-run`, `flask-ipv6-session`, `click-pickle-option`, `click-progress-final` | `real` | Fix a real bug that Flask or click fixed upstream between July and September 2026, in the project's own code and test suite |
| `inactive` | `control` | A plain question where Compound should stay out of the way |
| `first-use` | `control` | The December fix in a repository with no check-up yet and the user's own uncommitted notes |

Each real-bug fixture is the project at the parent of the upstream fix, with its history up to that point. The bug report describes only the symptom. The hidden tests are the new tests from the upstream fix, and the project's whole suite must still pass. `setup` checks that these tests fail at the parent and pass on the upstream fix. It also installs each project's test dependencies, as pinned in its `uv.lock`, into `bench/work/pyenv`. Runs see them read-only on `PYTHONPATH`.

Prompts are the same in every arm and never mention Compound. Write tasks may run code and commit. Read tasks may read and search but never run the project's code. Web access, package installs and network commands are denied in every arm.

## What is measured

- **Habits**, from a `python3` shim that records the exact source and test state at every call, plus a watcher on the working tree:
  - the run reproduced the bug before its first source change;
  - a new test failed on the old code;
  - the final code passed the full suite.
- **Correctness**, graded outside the run:
  - hidden tests for each bug and for the refactor;
  - the original suite and the run's own suite on its final code;
  - for real bugs, the upstream fix's tests and the project's whole suite.
- **Test strength**: each run's tests are run against frozen wrong or partial fixes (mutants). A test counts as a regression test only if it fails on the buggy code and passes on the reference fix.
- **Commits**: whether the run committed, the author, AI co-author trailers and "generated by" lines, and the subject style.
- **Answers**: a blind judge with no tools grades each review or investigation answer against a frozen key. It quotes the answer verbatim for every item it marks as met, and quotes that don't match the answer are discarded. Tooling mentions and absolute paths are removed first, in every arm.
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
