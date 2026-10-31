<h1 align="center">Compound Skills</h1>

<p align="center"><strong>Good engineering habits for your coding agent, plus a live map of your code.</strong></p>

<p align="center">Free, open-source (MIT) plugin for Claude Code, Codex and Cursor<br>The code map runs locally with Python 3.11+ and Git</p>

<p align="center"><a href="#install">Install</a> · <a href="#use-it">Use it</a> · <a href="#nine-workflows">Workflows</a> · <a href="#the-code-map">Code map</a> · <a href="#benchmark">Benchmark</a> · <a href="#limits">Limits</a></p>

Turn it on once and it gives your agent the same guidance in every project: reproduce a bug before fixing it, show the new test failing on the unfixed code, and leave AI co-author lines out of commits.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-headline-dark.svg">
    <img src=".github/assets/benchmark-headline.svg" width="600" alt="With Compound, Claude Opus 5.5 reproduced the bug before changing code in 17 of 24 fixes (0 of 24 without) and showed a test failing on the unfixed code in 23 of 24 (1 of 24 without). Cost and limits follow in the text.">
  </picture>
</p>

In our Claude Code benchmark of three clearly reported bugs, Claude Opus 5.5 went from almost never doing the first two to doing them in most fixes, at about 1.4× the tokens and 1.45–1.97× the list-price cost per fix (medians for each bug; single fixes ranged from 1.27× to 2.47× the cost). Claude Sonnet 5.5 rarely did them either way. Only Claude Code was measured, not Codex or Cursor. [Benchmark](#benchmark) · [Limits](#limits)

## Install

1. Install the plugin at **User** scope in each app you use (below).
2. Start a new chat (`/reload-plugins` also works in Claude Code) and turn Compound on for every project, once, from any app:<br>
   `/compound-skills:setup-global` in Claude Code<br>
   `$setup-global` in Codex<br>
   `/setup-global` in Cursor
3. Start a new chat and just ask for what you want.

### Claude Code

```text
/plugin marketplace add tobenwarrior/compound-skills
/plugin install compound-skills@compound-skills
```

### Codex

```sh
codex plugin marketplace add tobenwarrior/compound-skills
codex plugin add compound-skills@compound-skills
```

### Cursor

1. Open **Customize → Plugins → Add → From GitHub Repository**.
2. Enter `https://github.com/tobenwarrior/compound-skills`, choose **User** scope, then **Import**.
3. Click **Add** or **Install** beside `compound-skills`, and keep its `compound-default` rule set to **Always** in **Customize → Rules** (set it to **Manual** to turn Compound off). See [Cursor's plugin docs](https://cursor.com/docs/plugins).

> [!IMPORTANT]
> Before its first edit in a project, Compound asks the agent for a one-time check-up: review the structure and tests, apply only high-confidence cleanup (which can include deleting source, docs and tests it finds obsolete or redundant), verify it, and leave your uncommitted work alone. Its guide tells the agent not to stage or commit the cleanup just because the check-up ran. We have not measured the check-up itself. Details: [activation](skills/compound/references/activation.md) and [check-up](skills/compound/references/onboarding.md).

<details>
<summary>What first use looked like in our runs (3 Opus runs)</summary>

In 3 first-use runs with Opus where the first request was a bug fix, the agent read the check-up guide but skipped the check-up as going beyond the request, and said so in its report. It fixed the bug and left the uncommitted work alone, as stock Claude Code also did. In that first session it reproduced the bug first in 1 of 3 runs and showed a failing test in 2 of 3, against 7 and 8 of 8 on the same bug once set up, and used 1.46× the tokens of stock Claude Code.

</details>

## Use it

Each command takes your app's prefix, for example `/compound-skills:map` in Claude Code, `$map` in Codex and `/map` in Cursor.

| What you want | Command |
| --- | --- |
| Turn it on for every project (once, from any app) | `setup-global` |
| Check that it is on | `status-global` |
| Review and tidy the current project | `setup` |
| Open the code map | `map` |
| Use it in this chat only | `compound` |
| Remove the global setting | `compound disable global` |

<details>
<summary>Exact command for each app</summary>

| What you want | Claude Code | Codex | Cursor |
| --- | --- | --- | --- |
| Turn it on for every project (once, from any app) | `/compound-skills:setup-global` | `$setup-global` | `/setup-global` |
| Check that it is on | `/compound-skills:status-global` | `$status-global` | `/status-global` |
| Review and tidy the current project | `/compound-skills:setup` | `$setup` | `/setup` |
| Open the code map | `/compound-skills:map` | `$map` | `/map` |
| Use it in this chat only | `/compound-skills:compound` | `$compound` | `/compound` |
| Remove the global setting | `/compound-skills:compound disable global` | `$compound disable global` | `/compound disable global` |

</details>

Questions and reviews are meant to stay read-only, and in our runs no review or question changed the repository, with or without Compound (23 of the 32 reviews wrote scratch files in /tmp while trying to run the code).

## Nine workflows

Compound has one short guide for each kind of work and tells the agent to read the one that fits. In our runs the agent read the matching guide in 78 of 96 runs with Compound; Opus skipped it in 7 of 8 Django questions and Sonnet in 6 of 8 refactors. The table says what each guide asks for; the benchmark below measured only some of it.

| Workflow | What the guide asks for |
| --- | --- |
| [Investigate](skills/compound/references/investigate.md) | Trace how the code really behaves before answering |
| [Design and implement](skills/compound/references/design.md) | Start from how callers will use it and make states and ownership explicit |
| [Debug](skills/compound/references/debug.md) | Reproduce the bug, find the cause, and add a regression test |
| [Refactor](skills/compound/references/refactor.md) | Record current behavior, then prove it did not change |
| [Performance](skills/compound/references/performance.md) | Measure before and after on the same workload |
| [Review](skills/compound/references/review.md) | Report concrete problems with location, trigger, and impact |
| [Verify](skills/compound/references/verify.md) | Run checks that could prove the change wrong and say what is unverified |
| [Repository hygiene](skills/compound/references/repo-hygiene.md) | Flag clutter, oversized files, unused scripts, and `.gitignore` gaps |
| [Git and pull requests](skills/compound/references/git.md) | Write clear commits and PRs with real check results and human authorship |

## The code map

![The Compound code map of the open-source Hono repository. Hovering context.ts lights up the 8 files it imports and the 73 files that import it, and fades the rest of the graph.](.github/assets/code-map.svg)

- **Explore it.** Hover a file to light up its connections, drag it to pull its neighbors along, and scroll or pinch to zoom.
- **See what a change touches.** **Impact** shows the files that import the one you picked, directly or through other files, as far as the map resolves imports. **Trace** finds how two files connect, and **Changed** shows your Git edits and their neighbors.
- **Read without switching apps.** Search files, folders, and symbols, preview source, and copy a compact summary into your chat.
- **Your agent can ask it too.** Before searching a repository, Compound has the agent query the map once, unless the task names its file, and offers lookups of where a symbol is defined and mentioned. With the 0.12.1 wording only 1 of the 96 benchmark runs queried the map, and none used the symbol lookup. After we reworded that step, 43 of 48 runs on questions and edits in Flask, Hono and Django did, against 0 of 48 with the old wording; compared with the old wording, questions took 1.38× the tokens and 1.16× the list-price cost per pair, edits cost about the same, and answers scored about the same (method below).
- **Languages.** Imports are linked for Python, JavaScript, TypeScript, Go, and Rust. Symbols are outlined for those plus Java, C, C++, C#, Ruby, PHP, Swift, and Kotlin.

<details>
<summary>How we measured the reworded map step</summary>

In 0.12.1 the skill offered the map only as a fallback when the host had no suitable index, and in 77 of 94 runs that loaded the skill the agent searched or read code in the same turn, before the skill's text arrived. The skill now asks for one map query before any further search, read or edit, unless the task names its file or supplies the code, and the routing rule says to run it before searching. We compared the two wordings in Claude Code 2.1.316, 4 pairs per task and model, on three questions (Flask error handlers, Hono routing, Django `select_for_update`), two edits that name the command or method to change, a cookie bug planted in Hono and reported only by its symptom, and a question about a named file; agents could read the code but not run it. The map was queried in 43 of 48 runs, once each and as the first search in 41, against 0 of 48: all 24 questions, all 12 Opus edits and 7 of 12 Sonnet edits. Neither wording queried it for the named file. Per pair, questions took 1.38× the tokens, 1.16× the list-price cost and 1.23× the time (geometric means); edits took 0.98×, 1.00× and 1.04×. A blind judge scored answers and fixes about the same. Rewording the skill alone, without the rule sentence, reached 30 of 48 (2 of 12 Sonnet edits). Rules saved by an earlier `setup-global` or `setup` keep the old text until you update to 0.13.0 and run it again, and both models know these repositories well; we have not measured unfamiliar code.

</details>

![Four views of the Compound code map on the Hono repository: Impact for url.ts, which counts 219 dependent files; Trace, showing the import path from hono.ts through the trie router to node.ts; Changed, with the two edited files ringed among the files wired to them; and the source preview of the smart router.](.github/assets/code-map-views.svg)

The map opens at `http://127.0.0.1:43127/` and keeps its data in your user cache, outside the repository. Coverage and limits: [code maps](skills/compound/references/map.md).

### How fast is it?

Median of 5 runs on 4 cores with Python 3.13.17, timed on 0.13.0.

**Building the map**

| Repository | Files (indexed) | First build | Nothing changed | One file edited |
| --- | --: | --: | --: | --: |
| Gin · Go | 130 (113) | 0.42 s | 0.05 s | 0.06 s |
| Click · Python | 178 (114) | 0.61 s | 0.09 s | 0.11 s |
| ripgrep · Rust | 226 (126) | 2.48 s | 0.10 s | 0.19 s |
| Flask · Python | 236 (125) | 0.41 s | 0.12 s | 0.14 s |
| Hono · TypeScript | 583 (531) | 0.97 s | 0.23 s | 0.19 s |
| Vue core · TypeScript | 703 (612) | 1.24 s | 0.27 s | 0.26 s |
| Django · Python | 7,085 (3,496) | 8.20 s | 2.29 s | 2.38 s |

**Agent queries**

| Repository | Coding task, first query | Coding task, later queries | Question or review |
| --- | --: | --: | --: |
| Gin · Go | 1.09 s | 0.38 s | 0.64 s |
| Click · Python | 1.20 s | 0.42 s | 0.70 s |
| ripgrep · Rust | 3.17 s | 0.43 s | 2.61 s |
| Flask · Python | 1.09 s | 0.40 s | 0.47 s |
| Hono · TypeScript | 1.74 s | 0.41 s | 1.11 s |
| Vue core · TypeScript | 2.00 s | 0.42 s | 1.40 s |
| Django · Python | 10.90 s | 0.97 s | 8.78 s |

One file edited: the file most other files import. Coding task: the command the skill gives the agent when edits are allowed; the first query starts the local service and indexes. Question or review: the read-only command, which starts no service and writes no cache; timed here with no cache yet. The newer ranking (below) made queries slower than in 0.12.1 timed the same way: later queries by 0.03 to 0.09 seconds, a coding task's first query by 0.04 to 1.19 seconds, and a question or review by up to 0.97 seconds.

### Does it find the files a change touches?

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/map-retrieval-dark.svg">
  <img src=".github/assets/map-retrieval.svg" alt="Share of each commit's changed source files in the map's top 4, on 60 held-out commits each from Flask, Click, Hono and Gin: the current map 74% on average, against 48% for the map in 0.12.1, 51% for word-count search and 4% at random.">
</picture>

Usually, and more often than a word-count search. For 240 real commits that were not used to tune the map, 60 each from Flask, Click, Hono and Gin, we queried the map with each commit's title and checked whether the source files the commit changed came near the top. On average it put 74% of them in its top 4, against 51% for word-count search and 4% at random, and it was ahead on 73 commits to the search's 11; on Click the gap was small enough to be noise. The map in 0.12.1 put 48%. Part of the gain comes from listing tests lower: a word search that also skips common words and lists tests last put 67% in its top 4, about level with the map on Click and Gin. The map is built to show how files connect, which a word search does not; we have not measured how much that helps.

<details>
<summary>How the ranking works and how we tested it</summary>

It was clearly ahead on Flask (60% against 35%, ahead on 21 commits to the search's 4), Hono (75% against 34%, 27 commits to 0) and Gin (81% against 63%, 15 commits to 2). On Click it was slightly ahead (81% against 73%, 10 commits to 5), a gap small enough to be noise.

The map weighs the query's rarer words in file paths, symbols and the text of its 50 leading candidates, favors larger and widely imported code files, and lists tests lower unless the query mentions tests. We tuned it on the 60 most recent such commits of Flask, Click and Hono; Gin, a Go project, was used only for this check. Part of the gain comes from listing tests lower, since only non-test files were scored: a word search that also skips common words and lists tests last put 67% in its top 4, about level with the map on Click and Gin. Each commit's parent was copied into a fresh repository without history, so the map's co-change hints played no part. The newer ranking costs a little time: timed back to back on the seven repositories above, later queries took 0.03 to 0.09 seconds longer than in 0.12.1 and a coding task's first query 0.04 to 1.19 seconds longer, slower on every repository, while repeat runs of the same version differed by up to 0.14 seconds (0.42 on Django). First builds took 0.10 to 0.43 seconds longer on five repositories and 0.06 and 0.18 seconds less on Gin and Django; only on Flask and Hono did the five runs of the two versions not overlap.

Share of the changed source files in the top 4 · top 12:

| Repository | Commits | Code files to choose from | Code map | Map in 0.12.1 | Word-count search | Random |
| --- | --- | --: | --: | --: | --: | --: |
| Flask · Python | 60, 2023-03-04 to 2024-10-18 | 82 | 60% · 96% | 24% · 37% | 35% · 74% | 5% · 15% |
| Click · Python | 60, 2025-05-25 to 2026-05-23 | 63 | 81% · 95% | 49% · 71% | 73% · 92% | 6% · 19% |
| Hono · TypeScript | 60, 2026-07-21 to 2026-08-22 | 388 | 75% · 90% | 57% · 74% | 34% · 55% | 1% · 3% |
| Gin · Go (not used for tuning) | 60, 2025-10-08 to 2026-10-10 | 98 | 81% · 92% | 64% · 75% | 63% · 81% | 4% · 12% |

Word-count search ranks files by how many words of the title they contain. Nothing from the repositories was executed.

</details>

## Benchmark

We gave Claude Code the same six tasks with and without Compound: three bug reports, a refactor, a code review and a question about Django. Each ran 8 times per arm and model, in pairs started together in isolated sandboxes ([how we measured](#how-we-measured)).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-habits-dark.svg">
  <img src=".github/assets/benchmark-habits.svg" alt="Scorecard for Claude Opus 5.5 and Claude Sonnet 5.5, without and with Compound. With Opus, reproducing the bug first rose from 0 to 17 of 24 and showing a failing test from 1 to 23 of 24; with Sonnet there was no clear difference. Fixes, final-code testing and planted regressions caught stayed about the same. On the refactor, Opus with Compound kept tax rounding in 8 of 8 runs but removed both helpers in none, against 5 of 8 without. No bug fix with Compound put an AI co-author line in its commits. Cost: 1.28 times the tokens and 1.38 times the list-price cost with Opus, 1.37 and 1.60 times with Sonnet.">
</picture>

- **With Opus, it usually reproduced the bug before fixing it:** in 17 of 24 bug fixes with Compound, against 0 of 24 without. It showed the new test failing on the unfixed code in 23 of 24, against 1 of 24 (13 before writing the fix, the rest by undoing the fix briefly).
- **With Sonnet, no clear difference.** Claude Sonnet 5.5 read the same debugging guide in every bug fix but did these only 4 and 5 times out of 24, against 0 without.
- **No clear difference in fixes or test strength.** Every run fixed its bug, with or without Compound. The tests each run left behind caught about as many planted regressions: 63 of 88 with Compound and 62 of 88 without on Opus, 42 of 88 in both arms on Sonnet.
- **On the refactor, Opus with Compound stopped to ask instead of finishing.** The tax helper rounded differently, so a plain swap changes some tax amounts. With Compound, Opus kept tax rounding in all 8 runs but none removed both helpers; without it, 5 of 8 removed both, 2 of them keeping tax rounding, and the other 3 also stopped to ask. Sonnet removed both and changed tax rounding in all 16 runs, saying so each time.
- **No AI co-author line.** None of the 48 bug-fix runs with Compound, from either model, put an AI co-author line in its commits; stock Claude Code did in all 48. Claude Code's own `attribution` setting can also remove it.
- **It costs more.** With the six tasks weighted equally, Compound used 1.28× the tokens with Opus and 1.37× with Sonnet; at list prices, computed the same way but added after the runs, it cost 1.38× and 1.60× ([cost](#cost)).

<details>
<summary>Full results, with the statistics</summary>

- **With Opus, it usually reproduced the bug before fixing it.** With Compound, Claude Opus 5.5 ran the failing case before touching the code in 17 of 24 bug fixes, against 0 of 24 without. It showed its new test failing on the unfixed code in 23 of 24, against 1 of 24; in 13 of them before writing the fix, in the rest by undoing the fix briefly. Claude Sonnet 5.5 read the same debugging guide in every bug fix but did these only 4 and 5 times out of 24, against 0 without: no clear difference (for reproducing first, the pre-registered test gave Holm-adjusted p = 0.25; the failing-test count was not tested).
- **No clear difference in fixes or test strength.** Every run fixed its bug, with or without Compound, and stock Claude Code also tested its final code. On the four coding tasks, the tests each run left behind caught about as many of the regressions planted for its task (3 for each bug, 2 for the refactor; 88 checks over the 32 runs per arm): with Opus 63 of 88 with Compound, 62 of 88 without; with Sonnet 42 of 88 in both arms.
- **On the refactor, Opus played it safe and stopped short.** The refactor asked to remove two rounding helpers so all rounding goes through one shared function, but the tax helper rounded differently, so a plain swap changes some tax amounts. With Compound, Opus kept tax rounding in all 8 runs but stopped to ask instead of finishing: none removed both helpers. Without it, 5 of 8 removed both: 2 kept tax rounding and 3 changed it, saying so; the other 3 stopped to ask. Sonnet removed both helpers and changed tax rounding in all 16 runs, and said so each time. No run in either arm left a test that would catch the change.
- **No AI co-author line.** In all 48 bug-fix runs with Compound, from either model, the commit had no AI co-author line, and 45 used Conventional Commits titles such as `fix: …`. Stock Claude Code added a co-author line in all 48 and used such titles in none; Claude Code's own `attribution` setting can also remove the line.
- **It costs more.** Weighting the six tasks equally (the geometric mean of all 48 paired ratios, 8 per task), Compound used 1.28× the tokens with Opus (95% interval 1.22–1.34) and 1.37× with Sonnet (1.29–1.45). At list prices, computed the same way but added after the runs, it cost 1.38× with Opus (1.33–1.44) and 1.60× with Sonnet (1.50–1.70). Summed over each model's 48 pairs, that was 1.28× the tokens and 1.34× the cost with Opus ($8.00 against $5.96), and 1.27× and 1.53× with Sonnet ($3.33 against $2.17).

</details>

### What it looks like

The pair chosen before the runs: rep 1 of the December bug on Claude Opus 5.5. Both fixed the bug, added a test, noticed that plain EOM terms were wrong too and gave the corrected due date for the example. The highlighted sentences appear only in the report with Compound.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-reports-dark.svg">
  <img src=".github/assets/benchmark-reports.svg" alt="The final reports from the pair chosen before the runs, rep 1 of the December bug on Claude Opus 5.5. Both fixed the bug, added a test, noticed that plain EOM terms were wrong too and gave the corrected due date for the example. Only the report with Compound says the new test failed before the fix, with 2023-12-31 != 2024-12-31, that it found no other place with the same month arithmetic, and that it left the AI co-author line out.">
</picture>

Only the report with Compound says “Before the fix it failed with `2023-12-31 != 2024-12-31`, and now it passes”, “I found no other place in `src` that does the same month arithmetic” and “I left the AI co-author line out of the commit message because your Compound Skills git rules say not to add one”. Medians over the December bug's 8 Opus pairs, with Compound against without: 1.45× the tokens, 1.97× the list-price cost and 1.60× the time.

### Every Opus bug-fix run, step by step

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-steps-dark.svg">
  <img src=".github/assets/benchmark-steps.svg" alt="Every Claude Opus 5.5 bug-fix run as a row of steps, lined up on its first source edit. Without Compound, 23 of 24 runs started by editing the source. With Compound, 20 of 24 first ran the unfixed code or showed a failing test.">
</picture>

Without Compound, 23 of 24 runs started by editing the source. With Compound, 20 of 24 ran the unfixed code or showed a failing test before their first source edit, 13 of them a failing test. The scorecard counts 17 because its pre-registered detector missed three refund runs that printed the wrong total as `-$99.99`; the two arm-blind AI labellers counted the same 20 (Detector check, under [how we measured](#how-we-measured)).

### Cost

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-cost-dark.svg">
  <img src=".github/assets/benchmark-cost.svg" alt="Tokens, list-price cost and time with Compound as a multiple of the paired run without it, for each task and model. With the six tasks weighted equally, Opus used 1.28 times the tokens and 1.38 times the cost, Sonnet 1.37 and 1.60 times; the largest task median was Sonnet's Flask review at 3.91 times the tokens, with single pairs from 1.60 to 4.87 times.">
</picture>

For each bug, the median Opus fix took about 1.4× the tokens, 1.45–1.97× the cost ($0.05–0.08 more) and 9–12 seconds longer; single fixes ranged from 1.27× to 2.47× the cost and from 3 seconds faster to 33 seconds slower. The always-loaded part was 369 tokens per request; naming the map step in the routing rule later added 9.

### How we measured

Claude Code 2.1.314 in headless mode with Claude Opus 5.5 and Claude Sonnet 5.5 at default effort, on 31 October 2026. **Without** was stock Claude Code; **With** added Compound 0.12.1 as a plugin plus the global rule its `setup-global` writes. The plan, prompts, answer keys and analysis were frozen before the runs; the six-task list-price cost figures were added after them, and the logged deviations are under Method below.

<details>
<summary>Method: setup, isolation, tasks, scoring and detector check</summary>

- **Agent.** Claude Code 2.1.314 in headless mode with Claude Opus 5.5 and Claude Sonnet 5.5 at default effort, on 31 October 2026. Tool approvals were granted the same way in both arms, and web access was off.
- **Without** was stock Claude Code. It ships its own debug, verify and code-review skills but used none of them in any run. **With** added Compound 0.12.1 as a plugin plus the global rule its `setup-global` writes; the one-time check-up was already recorded and the map cache started empty.
- **Isolation.** Every run got its own copy of the repository and of one shared Claude configuration, in a sandbox with identical paths in both arms that hid the other run and the answer keys. Both runs of a pair started together, on one CPU each.
- **Tasks.** Three bug reports and a refactor in a small Python billing library written for this test, whose own tests miss the bugs. A review of a Flask commit with three planted defects. A question about the HTTP QUERY support in Django's unreleased 6.2, across its 7,085 files. No prompt mentions tests, Compound or the map.
- **Scoring.** Hidden tests; 11 planted regressions (3 for each bug, 2 for the refactor) run against the tests each agent left on that task; a logging wrapper around `python` in both arms that records what ran on which version of the code; and a blind automated judge (Claude Opus 5.5, the same model as one of the agents under test) for the review and the question (three votes per answer, and a point counts only with a quote from the answer). The plan, prompts, answer keys and analysis were frozen before the runs. Two harness bugs found during the runs were fixed and logged without changing any task or key. Grading crashed on the first two Opus leap-year pairs, so those 4 finished runs were never scored and both pairs ran again. A faulty resume then repeated 3 finished pairs and was stopped during a fourth; a rule that ignores results set aside its 7 recorded runs, and that pair's other finished run was never scored. In all, 12 finished Opus runs were left out. After the analysis we corrected one descriptive count, which guides each agent read, for 3 runs that read a guide through a shell variable.
- **Detector check.** Two AI labellers per trace (Claude Opus 5.5 agents run by a labelling script, not people), each shown the trace with the arm hidden, labelled every bug-fix trace. On the first pass they agreed with the automated habit detectors on 44 (reproduced first), 44 (failing test shown) and 35 (final code tested) of 48 Opus traces, mostly because hiding the arm had also hidden test output. The 15 Opus traces with a disagreement were regenerated with that output kept and labelled again, after which agreement was 45, 47 and 46 of 48; on Sonnet's fuller traces they agreed on all 48 the first time. The six remaining disagreements came from five Opus runs with Compound. In three refund runs, the labellers saw the bug reproduced first where the detector's frozen pattern missed output printed as `-$99.99`; by the labels, Opus with Compound reproduced first in 20 of 24 runs. The other three came from two runs in which a test command was chained with a read of a Compound file, so hiding the arm removed it from the trace; the full logs show the failing test and the final passing run, so there the detector was right.

</details>

<details>
<summary>Results by task and model</summary>

| Task | Model | Without → with Compound | Tokens with ÷ without | Cost with ÷ without | Time added |
| --- | --- | --- | --- | --- | --- |
| Three bug fixes, 24 runs per arm | Opus 5.5 | fixed 24 → 24 · reproduced first 0 → 17 · failing test shown 1 → 23 | 1.42–1.45× | 1.45–1.97× | 9–12 s |
| | Sonnet 5.5 | fixed 24 → 24 · reproduced first 0 → 4 · failing test shown 0 → 5 (no clear difference) | 1.02–1.32× | 1.15–1.56× | 0–5 s |
| Refactor, 8 runs per arm | Opus 5.5 | tax rounding kept 5 → 8 · both helpers removed 5 → 0 · both, safely 2 → 0 | 1.05× | 1.04× | 2 s |
| | Sonnet 5.5 | both helpers removed 8 → 8 · tax rounding kept 0 → 0 | 1.06× | 1.34× | 1 s |
| Review a Flask commit | Opus 5.5 | all 3 planted defects found 8 → 8 | 1.60× | 1.58× | 10 s |
| | Sonnet 5.5 | all 3 planted defects found 7 → 8 | 3.91× | 3.30× | 13 s |
| Question about Django, 11 key points | Opus 5.5 | median 11 → 11 | 0.84× (2 of 8 pairs higher) | 0.88× | −2 s |
| | Sonnet 5.5 | median 9 → 9 | 1.40× | 1.46× | 5 s |

Figures are medians over the 8 pairs of each task (for the bug fixes, the range across the three tasks). Cost is the API list price the client reported.

</details>

<details>
<summary>What else we found</summary>

- **On one bug, a plain rule matched the debugging habits.** A five-sentence rule asking for the same debugging and testing habits, but nothing about commits, without the plugin (Opus, 3 unpaired runs per task), reproduced the December bug first and showed a failing test in 3 of 3 runs (Compound: 7 and 8 of 8), with about as many tokens as Compound used there (medians 176k and 192k). Its 3 commits kept the AI co-author line, which the rule did not mention. On the refactor it kept tax rounding in 3 of 3 runs and finished the change safely in 1, the only refactor run in the benchmark that also left a test catching a change to tax rounding. We did not measure what Compound's other guides, the map or its Codex and Cursor setups add over such a rule.
- **Reviews and answers scored about the same.** The judge found all three planted defects in 8 of 8 Opus reviews in both arms, and in 8 of 8 Sonnet reviews with Compound against 7 of 8 without. All 11 Django key points were covered in 8 of 8 Opus answers without Compound and 7 of 8 with (the other covered 10); Sonnet's median was 9 of 11 in both arms. The judge's count of incorrect statements went opposite ways by model, though neither gap is clear at this sample size: Opus made 10 with Compound against 17 without (in 8 and 13 of the 16 reviews and Django answers in each arm), Sonnet 14 against 7 (in 11 and 6 of 16). With Compound, every Sonnet review tried to run the code, which the benchmark's tool permissions blocked (27 blocked commands, against 3 in the one Sonnet review without Compound that tried); every Opus review tried in both arms (28 blocked commands with Compound, 23 without).
- **Sonnet's tests were weaker either way.** Sonnet left a regression test that fails on the buggy code in 20 of 24 bug fixes without Compound and 19 of 24 with; Opus did in all 24 in both arms.
- **Little overhead on a general question.** For a general Python question (Opus, 3 runs), the agent never invoked the Compound skill; only the always-loaded 369 tokens were added.
- **Noise.** In two pairs of identical runs without Compound (Opus, refund bug), one run used up to 1.30× the tokens and 1.12× the time of its twin. Per-task token medians inside that band, such as Opus's 0.84× on Django or Sonnet's 1.02× and 1.06×, are not clear differences in tokens. Cost varied less between the twins, at most 1.12×, and every Sonnet December pair cost more with Compound (median 1.56×).

</details>

## Limits

- **Only Claude Code was measured**, not Codex or Cursor.
- **One small library, clearly reported bugs.** The bug fixes and the refactor used one small library written for this test, and the bugs were clearly reported, so both arms solved them; larger or vaguer work could differ in either direction.
- **Small samples.** Eight pairs per task can miss small effects, and the controls (the rule, the general question, the first use and the noise check) ran only on Opus with 2 or 3 runs or pairs each.
- **Read, not run.** In the Flask and Django tasks both arms could read the code but not run it.
- **The judge.** The automated judge for the review and the question was Claude Opus 5.5, the same model as one of the agents under test.
- **A plain rule matched the habits on one bug.** A five-sentence rule without the plugin (Opus, 3 unpaired runs per task) reproduced the December bug first and showed a failing test in 3 of 3 runs, with about as many tokens as Compound used there; it said nothing about commits, and its commits kept the AI co-author line. We did not measure what Compound's other guides, the map or its Codex and Cursor setups add over such a rule.
- **Not every result favors Compound.** With Sonnet the debugging habits showed no clear difference, Opus with Compound stopped short on the refactor, and it costs more with both models ([cost](#cost)).
- **Measured on 0.12.1.** The benchmark ran on 0.12.1. Version 0.13.0 then reworded the map step and changed the map's ranking; each change was measured separately ([the code map](#the-code-map)). Rules saved by an earlier `setup-global` or `setup` keep the old text until you update to 0.13.0 and run it again.
- **The code map.** Its ranking was tuned on other commits of Flask, Click and Hono (Gin was used only for the check); the newer ranking made later queries 0.03 to 0.09 seconds and a coding task's first query 0.04 to 1.19 seconds slower than 0.12.1; the reworded step was measured on repositories both models know well, not on unfamiliar code; and we have not measured how much seeing how files connect helps. Coverage and limits: [code maps](skills/compound/references/map.md).
- **The check-up.** We have not measured the one-time check-up itself.

## Credits

Adapted selectively from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), with lineage from earlier Karpathy-inspired guidelines. See [SOURCES.md](SOURCES.md), [third-party notices](THIRD_PARTY_NOTICES.md), and the [MIT license](LICENSE).
