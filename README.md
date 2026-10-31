# Compound Skills

**Good engineering habits for your coding agent, plus a live map of your code.**

Compound Skills is a free, open-source plugin for **Codex, Cursor, and Claude Code**. Turn it on once and your agent works the same careful way in every project: it reproduces a bug before fixing it, shows the new test failing first, and leaves AI co-author lines out of your commits. With Claude Opus 5.5 we measured the first two going from almost never to most bug fixes.

![The Compound code map of the open-source Hono repository. Hovering context.ts lights up every file it connects to and fades the rest.](.github/assets/code-map.svg)

## Why use it

![Scorecard with and without Compound. Claude Opus 5.5 reproduced the bug before changing code in 17 of 24 bug fixes with Compound against 0 of 24 without, and showed a failing test on the unfixed code in 23 of 24 against 1 of 24. Claude Sonnet 5.5: 4 and 5 of 24 against 0 of 24. Both models fixed every bug and tested the final code in both arms, the tests they left caught the same planted regressions, and no commit made with Compound carried an AI co-author line](.github/assets/benchmark-habits.svg)

We gave Claude Code the same six tasks with and without Compound: three bug reports, a refactor, a code review and a question about Django. Each ran 8 times per arm and model, in pairs started together in isolated sandboxes ([how we measured](#how-we-measured)).

- **It reproduces the bug before fixing it.** With Compound, Claude Opus 5.5 ran the failing case before touching the code in 17 of 24 bug fixes, against 0 of 24 without. It showed its new test failing on the unfixed code in 23 of 24, against 1 of 24. Claude Sonnet 5.5 loaded the same guidance but followed it far less often: 4 and 5 of 24, against 0 of 24 for both without.
- **The fixes were equally good.** Every run fixed its bug, with or without Compound. The tests each run left behind caught the same share of 11 planted regressions: with Opus 63 of 88 with Compound, 62 of 88 without; with Sonnet 42 and 42.
- **Your name on your commits.** With Compound, none of the 48 bug-fix commits from either model carried an AI co-author line, and 45 had conventional titles. Stock Claude Code added a co-author line to all 48; its own `includeCoAuthoredBy` setting can also turn that off.
- **It costs some tokens and time.** Over the six tasks Opus used 1.28× the tokens (95% interval 1.22–1.34) and 1.37× with Sonnet (1.29–1.45). With Opus that is about 1.4× and 9–12 seconds more per bug fix and 1.6× on the review, but 0.84× on the Django question. The always-loaded part is 369 tokens per request.
- **Local, one setup, three apps.** The code map runs on your machine with Python 3.11+ and Git, and the same habits apply in Codex, Cursor, and Claude Code.

## Install

Install once at **User** scope in each app you use, then start a new chat (or run `/reload-plugins` in Claude Code).

**Codex**

```sh
codex plugin marketplace add tobenwarrior/compound-skills
codex plugin add compound-skills@compound-skills
```

**Claude Code**

```text
/plugin marketplace add tobenwarrior/compound-skills
/plugin install compound-skills@compound-skills
```

**Cursor**

1. Open **Customize → Plugins → Add → From GitHub Repository**.
2. Enter `https://github.com/tobenwarrior/compound-skills`, choose **User** scope, then **Import**.
3. Click **Add** or **Install** beside `compound-skills`, and keep its `compound-default` rule set to **Always** in **Customize → Rules** (set it to **Manual** to turn Compound off). See [Cursor's plugin docs](https://cursor.com/docs/plugins).

## Use it

| What you want | Codex | Cursor | Claude Code |
| --- | --- | --- | --- |
| Turn it on for every project (once, from any app) | `$setup-global` | `/setup-global` | `/compound-skills:setup-global` |
| Check that it is on | `$status-global` | `/status-global` | `/compound-skills:status-global` |
| Review and tidy the current project | `$setup` | `/setup` | `/compound-skills:setup` |
| Open the code map | `$map` | `/map` | `/compound-skills:map` |
| Use it in this chat only | `$compound` | `/compound` | `/compound-skills:compound` |
| Remove the global setting | `$compound disable global` | `/compound disable global` | `/compound-skills:compound disable global` |

After that, just ask for what you want. The first time your agent edits a project, Compound offers a short check-up: it reviews the structure and tests, applies only high-confidence cleanup, verifies it, and leaves your uncommitted work alone. When the first request was a bug fix in our tests, the agent fixed the bug, left the check-up for later and kept the uncommitted work intact (3 of 3 runs). Questions and reviews stay read-only. Details: [activation](skills/compound/references/activation.md) and [check-up](skills/compound/references/onboarding.md).

## The code map

![The Impact view for url.ts in Hono: the 220 files that depend on it, drawn as a graph.](.github/assets/code-map-impact.svg)

- **Explore it.** Hover a file to light up its connections, drag it to pull its neighbors along, and scroll or pinch to zoom.
- **See what a change touches.** **Impact** shows the files that import the one you picked, directly or through other files. **Trace** finds how two files connect, and **Changed** shows your Git edits and their neighbors.
- **Read without switching apps.** Search files, folders, and symbols, preview source, and copy a compact summary into your chat.
- **Your agent can ask it too.** The skill offers the same map to the agent, plus lookups of where a symbol is defined and mentioned. In our benchmark Claude Code preferred its own search tools: only 1 of the 96 runs with Compound queried the map, including those on Django's 7,085 files.
- **Languages.** Imports are linked for Python, JavaScript, TypeScript, Go, and Rust. Symbols are outlined for those plus Java, C, C++, C#, Ruby, PHP, Swift, and Kotlin.

![Four views of the Compound code map on the Hono repository: Trace showing the import path from hono.ts to the trie router's node.ts, Changed showing uncommitted edits and the files wired to them, the source preview, and the tablet layout at 1024 by 768](.github/assets/code-map-views.svg)

![Code map timings on seven real repositories, median of 5 runs. A first build takes 0.26 seconds on Flask, 0.69 on Hono and 8.13 on Django with 7,085 files. With nothing changed it takes 0.04 to 0.23 seconds, and 1.96 on Django. The agent's warm query takes 0.31 to 0.34 seconds, and 0.89 on Django](.github/assets/map-speed.svg)

![For 60 recent commits each in Flask, click and Hono, the share of changed files the map put in its top 4: 34, 54 and 48 percent, against 57, 64 and 43 percent for plain text search and 5, 6 and 1 percent at random](.github/assets/map-retrieval.svg)

**Is it a better search than grep?** Not on every repository. For 180 recent real commits we queried the map with each commit's title and checked whether the files the commit changed came near the top. The map found them far more often than chance. Plain word-count search did better on Flask and click, and the map did better on Hono, the largest of the three. Its strength is showing how files connect, which a word search cannot.

The map opens at `http://127.0.0.1:43127/` and keeps its data in your user cache, outside the repository. Coverage and limits: [code maps](skills/compound/references/map.md).

## Nine workflows

Compound loads one short guide for each stage of the work.

| Workflow | What your agent does |
| --- | --- |
| [Investigate](skills/compound/references/investigate.md) | Traces how the code really behaves before answering |
| [Design and implement](skills/compound/references/design.md) | Starts from how callers will use it and makes states and ownership explicit |
| [Debug](skills/compound/references/debug.md) | Reproduces the bug, finds the cause, and adds a regression test |
| [Refactor](skills/compound/references/refactor.md) | Records current behavior, then proves it did not change |
| [Performance](skills/compound/references/performance.md) | Measures before and after on the same workload |
| [Review](skills/compound/references/review.md) | Reports concrete problems with location, trigger, and impact |
| [Verify](skills/compound/references/verify.md) | Runs checks that could prove the change wrong and says what is unverified |
| [Repository hygiene](skills/compound/references/repo-hygiene.md) | Flags clutter, oversized files, unused scripts, and `.gitignore` gaps |
| [Git and pull requests](skills/compound/references/git.md) | Writes clear commits and PRs with real check results and human authorship |

## How we measured

![Every Claude Opus 5.5 bug-fix run as a row of colored steps in the order they happened. Without Compound, runs start by editing the source and run the tests afterwards. With Compound, most runs first run the unfixed code or show a failing test, then edit the source, pass the tests and commit](.github/assets/benchmark-steps.svg)

- **Agent.** Claude Code 2.1.314 in headless mode with Claude Opus 5.5 and Claude Sonnet 5.5 at default effort, on 31 October 2026. Tool approvals were granted the same way in both arms, and web access was off.
- **Without** was stock Claude Code, which ships its own debug, verify and code-review skills. **With** added Compound 0.12.1 as a plugin plus the global rule its `setup-global` writes; the one-time check-up was already recorded and the map cache started empty.
- **Isolation.** Every run got its own copy of the repository and of one shared Claude configuration, in a sandbox that hid the other run, the answer keys and which arm it was in. Both runs of a pair started together, on one CPU each.
- **Tasks.** Three bug reports and a refactor in a small Python billing library written for this test, whose own tests miss the bugs. A review of a Flask commit with three planted defects. A question about the HTTP QUERY support in Django's unreleased 6.2, across its 7,085 files. No prompt mentions tests, Compound or the map.
- **Scoring.** Hidden tests; 11 planted regressions run against the tests each agent left behind; a logging wrapper around `python` in both arms that records what ran on which version of the code; and a blind judge for the review and the question. The plan, prompts, answer keys and analysis were fixed before the runs, and no run was dropped for its result.

| Task | Model | Without → with Compound | Tokens with ÷ without | Time added |
| --- | --- | --- | --- | --- |
| Three bug fixes, 24 runs per arm | Opus 5.5 | fixed 24 → 24 · reproduced first 0 → 17 · failing test shown 1 → 23 | 1.42–1.45× | 9–12 s |
| | Sonnet 5.5 | fixed 24 → 24 · reproduced first 0 → 4 · failing test shown 0 → 5 | 1.02–1.32× | 0–5 s |
| Refactor, 8 runs per arm | Opus 5.5 | tax rounding kept 5 → 8 · full change done 2 → 0 | 1.05× | 2 s |
| | Sonnet 5.5 | full change done 8 → 8, tax rounding changed and reported in every run | 1.06× | 1 s |
| Review a Flask commit | Opus 5.5 | all 3 planted defects found 8 → 8 | 1.60× | 10 s |
| | Sonnet 5.5 | all 3 planted defects found 7 → 8 | 3.91× | 13 s |
| Question about Django, 11 key points | Opus 5.5 | median 11 → 11 | 0.84× | −2 s |
| | Sonnet 5.5 | median 9 → 9 | 1.40× | 5 s |

Token and time figures are medians over the 8 pairs of each task; for the bug fixes, the range across the three tasks.

![The final reports from the pair chosen before the runs, rep 1 of the December bug on Claude Opus 5.5. Both fixed the bug and added a test. Only the report with Compound says the new test failed before the fix, with 2023-12-31 != 2024-12-31, checks the example from the request, and says it found no other place with the same month arithmetic](.github/assets/benchmark-reports.svg)

![Tokens and time per task with Compound, as a multiple of the paired run without it, for Claude Opus 5.5: bug fixes 1.42 to 1.45 times the tokens and 1.37 to 1.60 times the time, refactor 1.05 and 1.07, review 1.60 and 1.31, the Django question 0.84 and 0.92. Overall 1.28 times the tokens](.github/assets/benchmark-cost-opus.svg)

![Tokens and time per task with Compound, as a multiple of the paired run without it, for Claude Sonnet 5.5: bug fixes 1.02 to 1.32 times the tokens and 1.02 to 1.30 times the time, refactor 1.06 and 1.05, review 3.91 and 1.81, the Django question 1.40 and 1.34. Overall 1.37 times the tokens](.github/assets/benchmark-cost-sonnet.svg)

**What else we found**

- **A plain rule gets part of the way.** A five-line rule asking for the same habits, without the plugin, reproduced the December bug first in 3 of 3 Opus runs, with fewer tokens than Compound used on that task (medians 176k and 192k). Compound adds maintained guides for nine kinds of work, the code map and one setup for three apps.
- **The refactor.** With Compound, all 8 Opus runs kept tax rounding unchanged and asked before switching it, so none finished the full change. Without it, 2 runs did the full refactor safely, 3 asked, and 3 changed how tax rounds; each of those 3 said so. Every Sonnet run in both arms changed tax rounding and said so.
- **Reviews and answers were as good either way.** A blind judge found all three planted defects in every Opus review in both arms, and in 8 of 8 Sonnet reviews with Compound against 7 of 8 without. On the Django question the median answer covered 11 of 11 key points with Opus and 9 of 11 with Sonnet, in both arms.
- **It stays out of the way.** For a general Python question, Compound did not load (0 of 3 runs).
- **Noise.** In two pairs of identical runs without Compound, the runs differed by up to 23% in tokens and 11% in time, so compare the per-task ranges rather than single runs.

**Limits.** Only Claude Code was measured, not Codex or Cursor. The bug fixes were small and clearly reported, so both arms solved them; larger or vaguer work could differ in either direction. Eight pairs per task can miss small effects. In the Flask and Django tasks both arms could read the code but not run it.

## Credits

Adapted selectively from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), with lineage from earlier Karpathy-inspired guidelines. See [SOURCES.md](SOURCES.md), [third-party notices](THIRD_PARTY_NOTICES.md), and the [MIT license](LICENSE).
