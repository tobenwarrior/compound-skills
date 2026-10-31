<h1 align="center">Compound Skills</h1>

<p align="center"><strong>Good engineering habits for your coding agent, plus a live map of your code.</strong></p>

<p align="center">Free, open-source (MIT) plugin for Claude Code, Codex and Cursor<br>The code map runs locally with Python 3.11+ and Git</p>

<p align="center"><a href="#install">Install</a> · <a href="#use-it">Use it</a> · <a href="#nine-workflows">Workflows</a> · <a href="#the-code-map">Code map</a> · <a href="#benchmark">Benchmark</a> · <a href="#limits">Limits</a></p>

Turn it on once and it gives your agent the same guidance in every project: reproduce a bug before fixing it, show the new test failing on the unfixed code, pin current behavior before a refactor, and leave AI co-author lines out of commits.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-headline-dark.svg">
    <img src=".github/assets/benchmark-headline.svg" width="600" alt="With Compound, Claude Opus 5.5 reproduced the bug before changing code in 15 of 15 fixes and Claude Sonnet 5.5 in 14 of 15, against 0 of 15 each without, and both showed a test failing on the unfixed code just as often. Cost and limits follow in the text.">
  </picture>
</p>

Run with and without Compound on three clearly reported bugs, Claude Opus 5.5 and Claude Sonnet 5.5 went from never doing the first two to doing them in 15 and 14 of 15 fixes, and both finished a tricky refactor safely in every run. A median fix cost 1.37–1.56× as much with Opus and 1.14–1.75× with Sonnet, at list prices. [Benchmark](#benchmark) · [Limits](#limits)

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
<summary>What first use looked like in our first benchmark (3 Opus runs on 0.12.1)</summary>

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
- **Your agent can ask it too.** Before searching a repository, Compound has the agent query the map once, unless the task names its file, and offers lookups of where a symbol is defined and mentioned. With the 0.12.1 wording only 1 of the 96 benchmark runs queried the map, and none used the symbol lookup. After we reworded that step, 43 of 48 runs on questions and edits in Flask, Hono and Django did, against 0 of 48 with the old wording; compared with the old wording, questions took 1.38× the tokens and 1.16× the list-price cost per pair, edits cost about the same, and answers scored about the same (method below). In the 0.14.0 benchmark, all 60 runs with Compound queried it.
- **Languages.** Imports are linked for Python, JavaScript, TypeScript, Go, and Rust. Symbols are outlined for those plus Java, C, C++, C#, Ruby, PHP, Swift, and Kotlin.

<details>
<summary>How we measured the reworded map step</summary>

In 0.12.1 the skill offered the map only as a fallback when the host had no suitable index, and in 77 of 94 runs that loaded the skill the agent searched or read code in the same turn, before the skill's text arrived. The skill now asks for one map query before any further search, read or edit, unless the task names its file or supplies the code, and the routing rule says to run it before searching. We compared the two wordings in Claude Code 2.1.316, 4 pairs per task and model, on three questions (Flask error handlers, Hono routing, Django `select_for_update`), two edits that name the command or method to change, a cookie bug planted in Hono and reported only by its symptom, and a question about a named file; agents could read the code but not run it. The map was queried in 43 of 48 runs, once each and as the first search in 41, against 0 of 48: all 24 questions, all 12 Opus edits and 7 of 12 Sonnet edits. Neither wording queried it for the named file. Per pair, questions took 1.38× the tokens, 1.16× the list-price cost and 1.23× the time (geometric means); edits took 0.98×, 1.00× and 1.04×. A blind judge scored answers and fixes about the same. Rewording the skill alone, without the rule sentence, reached 30 of 48 (2 of 12 Sonnet edits). Rules saved by an earlier `setup-global` or `setup` keep the old text until you update to 0.14.0 and run it again, and both models know these repositories well; we have not measured unfamiliar code.

</details>

![Four views of the Compound code map on the Hono repository: Impact for url.ts, which counts 219 dependent files; Trace, showing the import path from hono.ts through the trie router to node.ts; Changed, with the two edited files ringed among the files wired to them; and the source preview of the smart router.](.github/assets/code-map-views.svg)

The map opens at `http://127.0.0.1:43127/` and keeps its data in your user cache, outside the repository. Coverage and limits: [code maps](skills/compound/references/map.md).

### How fast is it?

Median of 5 runs on 4 cores with Python 3.13.17, timed on 0.13.0; 0.14.0 did not change the map code.

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

We gave Claude Code the same six tasks with and without Compound 0.14.0: three bug reports, a refactor, a code review and a question about Django. Each ran 5 times per arm and model, side by side in isolated sandboxes, next to a third arm running 0.13.0 ([what changed](#what-changed-in-0140)). Four real bugs from Flask and click came after ([real bugs](#real-bugs)). The harness is in [bench/](bench/README.md), so you can rerun all of it ([how we measured](#how-we-measured)).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-habits-dark.svg">
  <img src=".github/assets/benchmark-habits.svg" alt="Scorecard for Claude Opus 5.5 and Claude Sonnet 5.5, without and with Compound. Reproducing the bug first rose from 0 to 15 of 15 with Opus and from 0 to 14 of 15 with Sonnet, and showing a failing test rose the same way. Every run fixed its bug in both arms. The tests each run left caught more planted regressions with Compound: 49 of 55 against 40 with Opus, 42 against 29 with Sonnet. On the refactor, both models with Compound kept tax rounding and removed both helpers in 5 of 5 runs. 29 of 30 bug fixes with Compound committed without an AI co-author line, against none without. Cost: 1.56 times the tokens and the list-price cost with Opus, 1.55 and 1.69 times with Sonnet.">
</picture>

- **Both models reproduced the bug before fixing it.** With Compound, Opus did in 15 of 15 bug fixes and Sonnet in 14 of 15, against 0 of 15 each without. They showed the new test failing on the unfixed code just as often: 15 and 14 of 15, against 0.
- **The refactor was finished safely.** It asked to remove two rounding helpers, but the tax helper rounded differently, so a plain swap changes some tax amounts. With Compound, both models removed both helpers and kept tax rounding in all 5 runs, each leaving a test that catches the plain swap. Without it, Opus did so in 2 of 5 runs and Sonnet in none, and no run left such a test.
- **Stronger tests.** The tests each run left behind caught more of the regressions planted for its task: 49 of 55 with Compound against 40 of 55 without on Opus, 42 against 29 on Sonnet.
- **The same fixes.** Every bug-fix run fixed its bug, with or without Compound.
- **Almost no AI co-author lines.** 29 of the 30 bug fixes with Compound committed without one (one Sonnet run kept it); stock Claude Code added one in all 30. Claude Code's own `attribution` setting can also remove it.
- **It costs more.** With the six tasks weighted equally, Compound used 1.56× the tokens and 1.56× the list-price cost with Opus, and 1.55× and 1.69× with Sonnet ([cost](#cost)).

<details>
<summary>Full results, with the statistics</summary>

- **Reproduced first and failing test shown.** Opus 15 of 15 bug fixes with Compound against 0 of 15 without, for both; Sonnet 14 of 15 against 0 for both. Exact McNemar tests on the 15 pairs per model: p < 0.001 each.
- **Test strength.** Per run, the share of its task's planted regressions that its own tests caught rose by 0.22 on average with Opus and 0.26 with Sonnet (20 pairs each, 3 regressions per bug and 2 for the refactor; sign-flip test p = 0.03 and p = 0.001). Sonnet without Compound left a test that fails on the buggy code in 13 of 15 bug fixes, against 15 of 15 with it; Opus did in all 15 in both arms.
- **Refactor.** Done safely, meaning both helpers removed, tax rounding kept and the suites passing: Opus 5 of 5 with Compound against 2 of 5 without, Sonnet 5 of 5 against 0 of 5. The 3 Opus and 5 Sonnet runs without Compound that changed tax rounding said so in their reports. With 5 pairs, Sonnet's difference gives p = 0.06.
- **Commits.** All 30 bug fixes in both arms committed. With Compound, 28 used Conventional Commits titles such as `fix: …`; stock Claude Code used none.
- **Cost.** Weighting the six tasks equally (the geometric mean of the 30 paired ratios per model, 5 per task), Compound used 1.56× the tokens with Opus (95% interval 1.47–1.65) and 1.55× with Sonnet (1.40–1.72), and cost 1.56× (1.48–1.64) and 1.69× (1.53–1.86) at list prices. Summed over each model's 30 pairs: 1.56× the tokens and 1.54× the cost with Opus ($6.04 against $3.91), 1.43× and 1.64× with Sonnet ($2.26 against $1.38).
- **Stopping.** We planned 6 repetitions and stopped after 5 to stay within our usage limit, a decision made after seeing interim results. No task, key, grader or detector changed during the runs.

</details>

### What changed in 0.14.0

0.14.0 adds one sentence to the always-on rule: reproduce a reported bug and show its regression test failing before fixing it, and pin current behavior with a test before a refactor. Its refactor guide now says to keep behavior and still finish the change, asking first only when no behavior-preserving path exists. Against 0.13.0 in the same runs:

| | 0.13.0 | 0.14.0 |
| --- | --: | --: |
| Opus: reproduced the bug before changing code | 11 of 15 | 15 of 15 |
| Opus: showed a test failing on the unfixed code | 14 of 15 | 15 of 15 |
| Sonnet: reproduced the bug before changing code | 1 of 15 | 14 of 15 |
| Sonnet: showed a test failing on the unfixed code | 6 of 15 | 14 of 15 |
| Refactor done safely, Opus and Sonnet | 2 and 0 of 5 | 5 and 5 of 5 |
| Cost, with the six tasks weighted equally | | 1.06× and 1.03× of 0.13.0 |

The same release also asks for fewer startup steps, a shorter final report and no retries of blocked commands in reviews; together they did not measurably cut cost. The always-loaded part grew from 378 to 418 tokens per request.

### Real bugs

Four bugs that Flask and click fixed upstream between July and September 2026: `app.run()` failing on an IPv6 `SERVER_NAME`, the test client losing the session with an IPv6 `base_url`, pickling a click option, and a click progress bar that stops at 14/20. Each run got the project at the fix's parent, with its history and test suite, and a report that describes only the symptom. The upstream fix's own new tests stayed hidden, and the project's whole suite had to pass. 3 runs per bug, arm and model.

| | Opus 5.5, without → with | Sonnet 5.5, without → with |
| --- | --: | --: |
| Reproduced the bug before changing code | 5 → 10 of 12 | 0 → 12 of 12 |
| Showed a test failing on the unfixed code | 8 → 12 of 12 | 3 → 12 of 12 |
| Ran the whole suite on the final code | 8 → 10 of 12 | 3 → 11 of 12 |
| Upstream's hidden tests pass | 9 → 9 of 12 | 9 → 9 of 12 |
| Left a test that fails on the buggy code | 12 → 11 of 12 | 10 → 12 of 12 |
| List-price cost, the four bugs weighted equally | 1.51× | 1.38× |

Both arms fixed the same bugs: every run fixed the two Flask bugs and the pickling bug, and none fully fixed the progress bar. Its report describes a loop over the bar, and every run fixed that path, but upstream's tests also cover the same bug through `bar.update()`. Stock Claude Code already reproduced some of these bugs first, since the reports quote the error: Opus in 5 of 12 runs, 10 with Compound; Sonnet went from 0 to 12.

### What it looks like

The same example slot as in the first benchmark: rep 1 of the December bug on Claude Opus 5.5. Both runs fixed the bug, added a test, noticed that plain EOM terms were wrong too and committed. The highlighted sentences appear only in the report with Compound.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-reports-dark.svg">
  <img src=".github/assets/benchmark-reports.svg" alt="The final reports from rep 1 of the December bug on Claude Opus 5.5. Both fixed the bug, added a test, noticed that plain EOM terms were wrong too and committed. Only the report with Compound says the new test failed before the fix, with 2023-12-31 != 2024-12-31, that it checked the example from the report directly, that it found no other code doing the same month arithmetic, and that the commit has no Claude co-author trailer.">
</picture>

Only the report with Compound says “Before the fix it failed (`2023-12-31 != 2024-12-31`)”, “Calling `due_date` directly with the example from your report now returns `2025-01-30`”, “I found no other code in `src` doing the same month arithmetic” and that the commit “has no Claude co-author trailer”. Medians over the December bug's 5 Opus pairs, with Compound against without: 1.49× the tokens, 1.56× the list-price cost and 1.47× the time.

### Every Opus bug-fix run, step by step

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-steps-dark.svg">
  <img src=".github/assets/benchmark-steps.svg" alt="Every Claude Opus 5.5 bug-fix run as a row of steps, lined up on its first source edit. Without Compound, 14 of 15 runs started by editing the source. With Compound, all 15 showed a failing test before their first source edit.">
</picture>

Without Compound, 14 of 15 runs started by editing the source; the other ran Python first, but only tried pytest, which this library does not have. With Compound, 15 of 15 ran the unfixed code or showed a failing test before their first source edit, 15 of them a failing test.

### Cost

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-cost-dark.svg">
  <img src=".github/assets/benchmark-cost.svg" alt="Tokens, list-price cost and time with Compound as a multiple of the paired run without it, for each task and model. With the six tasks weighted equally, Opus used 1.56 times the tokens and the cost, Sonnet 1.55 and 1.69 times; the largest task median was Sonnet's Flask review at 3.10 times the tokens, with single pairs from 1.61 to 4.98 times.">
</picture>

For each bug, the median Opus fix took 1.14–1.50× the tokens, 1.37–1.56× the cost ($0.05–0.07 more) and 4–14 seconds longer; single fixes ranged from 1.16× to 2.11× the cost. Reviews cost the most extra: Sonnet's Flask review took 3.10× the tokens, single pairs from 1.61 to 4.98 times. With Compound, every Sonnet review loaded the guides, queried the map and tried to run the code, which the benchmark blocks; without it, most answered after a single command. The always-loaded part is 418 tokens per request.

### How we measured

Claude Code 2.1.316 in headless mode with Claude Opus 5.5 and Claude Sonnet 5.5 at default effort, on 31 October 2026. **Without** was stock Claude Code; **With** added Compound 0.14.0 as a plugin plus the global rule its `setup-global` writes, and a third arm ran 0.13.0 the same way. The tasks, prompts, answer keys and graders are the ones frozen for our first benchmark, which ran 0.12.1 with 8 pairs per task. Everything is in [bench/](bench/README.md).

<details>
<summary>Method: setup, isolation, tasks, scoring and detectors</summary>

- **Agent.** Claude Code 2.1.316 in headless mode with Claude Opus 5.5 and Claude Sonnet 5.5 at default effort, on 31 October 2026. Tool approvals were granted the same way in every arm, and web access was off.
- **Arms.** **Without** was stock Claude Code. It ships its own debug, verify and code-review skills but used none of them in any run. **With** added Compound 0.14.0 as a plugin plus the global rule its `setup-global` writes; the one-time check-up was already recorded and the map cache started empty. A third arm ran Compound 0.13.0 the same way.
- **Isolation.** Every run got its own copy of the repository and of one shared Claude configuration, in a sandbox with identical paths in every arm that hid the other runs and the answer keys. The runs of a group started together, on one CPU each, and the arm order rotated.
- **Tasks.** Three bug reports and a refactor in a small Python billing library written for this test, whose own tests miss the bugs. A review of a Flask commit with three planted defects. A question about the HTTP QUERY support in Django's unreleased 6.2, across its 7,085 files. No prompt mentions tests, Compound or the map. The real bugs are described above.
- **Scoring.** Hidden tests; 11 planted regressions (3 for each bug, 2 for the refactor) run against the tests each agent left on that task; a logging wrapper around `python` in every arm that records what ran on which version of the code; and a blind automated judge (Claude Opus 5.5, the same model as one of the agents under test) for the review and the question, with three votes per answer for **Without** and **With** and one for 0.13.0. A point counts only with a quote from the answer.
- **Detectors.** The habit detectors are the ones two arm-blind AI labellers (Claude Opus 5.5 agents run by a labelling script, not people) checked in the first benchmark: after a second pass they agreed with them on 45 to 47 of 48 Opus traces and on all 48 Sonnet traces. The detectors' one known miss, a wrong refund total printed as `-$99.99`, is now matched too.
- **Corrections.** The rebuilt Flask fixture has a new commit id, but the judge's copy of the commit still showed the old one, so 40 judge votes called the commit id wrong; we dropped those complaints and fixed the harness. In the first benchmark, grading crashed on two Opus pairs and a faulty resume repeated three, so 12 finished Opus runs were left out; nothing was left out this time.

</details>

<details>
<summary>Results by task and model</summary>

| Task | Model | Without → with Compound | Tokens with ÷ without | Cost with ÷ without | Time added |
| --- | --- | --- | --- | --- | --- |
| Three bug fixes, 15 runs per arm | Opus 5.5 | fixed 15 → 15 · reproduced first 0 → 15 · failing test shown 0 → 15 | 1.14–1.50× | 1.37–1.56× | 4–14 s |
| | Sonnet 5.5 | fixed 15 → 15 · reproduced first 0 → 14 · failing test shown 0 → 14 | 1.01–1.36× | 1.14–1.75× | 6–9 s |
| Refactor, 5 runs per arm | Opus 5.5 | tax rounding kept 2 → 5 · both helpers removed 5 → 5 · both, safely 2 → 5 | 1.93× | 1.61× | 16 s |
| | Sonnet 5.5 | tax rounding kept 0 → 5 · both helpers removed 5 → 5 · both, safely 0 → 5 | 1.49× | 1.69× | 11 s |
| Review a Flask commit | Opus 5.5 | all 3 planted defects found 5 → 5 | 2.29× | 1.72× | 12 s |
| | Sonnet 5.5 | all 3 planted defects found 5 → 5 | 3.10× | 2.51× | 17 s |
| Question about Django, 11 key points | Opus 5.5 | all 11 covered 4 → 5 | 1.52× | 1.23× | 18 s |
| | Sonnet 5.5 | median 9 → 9 | 1.83× | 1.57× | 14 s |

Figures are medians over the 5 pairs of each task (for the bug fixes, the range across the three tasks). Cost is the API list price the client reported.

</details>

<details>
<summary>What else we found</summary>

- **Reviews and answers scored about the same.** The judge found all three planted defects in every review in both arms. All 11 Django key points were covered in 5 of 5 Opus answers with Compound and 4 of 5 without (the other covered 10); Sonnet's median was 9 of 11 in both arms. The judge counted as many incorrect statements with and without Compound for Opus (3 and 3, in the 10 reviews and Django answers per arm), but more with it for Sonnet (9 against 5), mostly in Django answers.
- **Reviews tried to run the code.** With Compound, every review tried to run the code, which the benchmark's tool permissions block: 21 blocked commands in the Opus reviews and 16 in the Sonnet ones. Without it, every Opus review tried too (15 blocked commands) but only one Sonnet review did (3).
- **The map was always used.** With 0.14.0, every run on the six tasks queried the code map, and none used the symbol lookup.
- **Little overhead on a general question.** For a general Python question (5 runs per model), the agent never invoked the Compound skill; only the always-loaded 418 tokens were added.
- **A plain rule, in the first benchmark.** On 0.12.1, a five-sentence rule asking for the same debugging and testing habits, without the plugin (Opus, 3 unpaired runs per task), reproduced the December bug first and showed a failing test in 3 of 3 runs, with about as many tokens as Compound used there. Its commits kept the AI co-author line, which the rule did not mention. We did not measure what Compound's other guides or the map add over such a rule.

</details>

## Limits

- **Run in Claude Code.** Codex and Cursor load the same guides, so we expect them to behave similarly; the numbers on this page come from Claude Code.
- **Mostly one small library.** The six-task bug fixes and the refactor used one small library written for this test, with clearly reported bugs, so both arms fixed them. The four real Flask and click bugs are closer to everyday work, but they are only four bugs.
- **Small samples.** Five pairs per task and three per real bug can miss small effects, and the general-question control ran 5 times per model.
- **Read, not run.** In the Flask review and the Django question, every arm could read the code but not run it.
- **The judge.** The automated judge for the review and the question was Claude Opus 5.5, the same model as one of the agents under test.
- **A plain rule might do much of this.** In our first benchmark, a five-sentence rule without the plugin matched the debugging habits on one bug, and 0.14.0's always-on rule now asks for them directly. We have not measured what Compound's guides and map add over such a rule alone.
- **Not every result favors Compound.** It costs more with both models, reviews cost the most extra ([cost](#cost)), and with Sonnet the judge counted more incorrect statements with Compound, 9 against 5, mostly in Django answers.
- **Measured on 0.14.0.** The six tasks ran on 0.14.0 and 0.13.0; the map's ranking and the reworded map step were measured separately ([the code map](#the-code-map)). Rules saved by an earlier `setup-global` or `setup` keep the old text until you update to 0.14.0 and run it again.
- **The code map.** Its ranking was tuned on other commits of Flask, Click and Hono (Gin was used only for the check); the newer ranking made later queries 0.03 to 0.09 seconds and a coding task's first query 0.04 to 1.19 seconds slower than 0.12.1; the reworded step was measured on repositories both models know well, not on unfamiliar code; and we have not measured how much seeing how files connect helps. Coverage and limits: [code maps](skills/compound/references/map.md).
- **The check-up.** We have not measured the one-time check-up itself.

## Credits

Adapted selectively from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), with lineage from earlier Karpathy-inspired guidelines. See [SOURCES.md](SOURCES.md), [third-party notices](THIRD_PARTY_NOTICES.md), and the [MIT license](LICENSE).
