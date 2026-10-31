<h1 align="center">Compound Skills</h1>

<p align="center"><strong>Make your coding agent show its work.</strong><br>It reproduces the bug, shows the new test failing before the fix, keeps behavior through refactors, and commits without AI co-author lines. Plus a live map of your code.</p>

<p align="center">Free, open-source (MIT) plugin for Claude Code, Codex and Cursor · needs Python 3.11+ and Git<br>Version 0.15.0 · measured on 31 October 2026 in Claude Code 2.1.316 · not affiliated with Every's Compound Engineering plugin</p>

<p align="center"><a href="#should-you-use-it">Should you use it?</a> · <a href="#install">Install</a> · <a href="#benchmark">Benchmark</a> · <a href="#compared-with-other-plugins">Compared</a> · <a href="#the-code-map">Code map</a> · <a href="#limits">Limits</a></p>

Turn it on once and your agent follows the same instructions in every project: query a local map of the code before searching, reproduce a reported bug and show a test failing on the unfixed code before fixing it, pin current behavior before a refactor, run the whole suite, commit without AI co-author lines, and report what it verified and what it did not.

On 12 real bugs that Flask, click, attrs, packaging and marshmallow fixed upstream between July and October 2026, with each fix's own tests hidden from the agent, Compound did not change which bugs got fixed: upstream's tests passed in 23 and 23 of 28 runs with Opus and 23 and 21 of 28 runs with Sonnet, without and with it. It changed the evidence. With Claude Opus 5.5 the agent reproduced the bug before touching the code in 28 of 28 runs against 5 without, and with Claude Sonnet 5.5 in 26 against 0. A median fix cost 19¢ → 28¢ with Opus and 7.1¢ → 9.7¢ with Sonnet, at API list prices; reviews cost the most extra. [Should you use it?](#should-you-use-it) · [Limits](#limits)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-real-dark.svg">
    <img src=".github/assets/benchmark-real.svg" width="700" alt="12 real bugs, fixed upstream in 2026. Flask, click, attrs, packaging and marshmallow at the commit before each fix, with the fix's own tests hidden; the report describes only the symptom. Stock Claude Code against Compound Skills 0.14.0, side by side. Fixed the bug (upstream's tests pass): Opus stock 23 of 28, Opus with Compound 23 of 28, Sonnet stock 23 of 28, Sonnet with Compound 21 of 28. Fixed it and the project's whole suite passes: Opus stock 23 of 28, Opus with Compound 23 of 28, Sonnet stock 23 of 28, Sonnet with Compound 21 of 28. Left a test that fails on the buggy code: Opus stock 28 of 28, Opus with Compound 27 of 28, Sonnet stock 26 of 28, Sonnet with Compound 28 of 28. Reproduced the bug before changing code: Opus stock 5 of 28, Opus with Compound 28 of 28, Sonnet stock 0 of 28, Sonnet with Compound 26 of 28. Showed a new test failing before the fix: Opus stock 0 of 28, Opus with Compound 28 of 28, Sonnet stock 0 of 28, Sonnet with Compound 26 of 28. Ran the whole suite on the final code: Opus stock 19 of 28, Opus with Compound 22 of 28, Sonnet stock 8 of 28, Sonnet with Compound 25 of 28. Committed without an AI co-author line: Opus stock 0 of 28, Opus with Compound 28 of 28, Sonnet stock 0 of 28, Sonnet with Compound 28 of 28. Median cost of a fix: Opus stock 19¢, Opus with Compound 28¢, Sonnet stock 7.1¢, Sonnet with Compound 9.7¢. The first four bugs (Flask and click, fixed July to September) ran 3 times per arm and model; eight more (attrs, packaging, marshmallow, fixed August to October) were frozen before any run and ran twice. Without Compound, the new test was shown failing on the unfixed code only after the fix, with the fix set aside: in 20 Opus runs and 4 Sonnet runs.">
  </picture>
</p>

## Should you use it?

Compound Skills 0.15.0, measured on 31 October 2026 in headless Claude Code 2.1.316 with Claude Opus 5.5 and Claude Sonnet 5.5 at default effort. Every number comes from [bench/](bench/README.md) and says how many runs it rests on.

**What you get**

- **The same fixes, with the evidence attached.** On the 12 real bugs, upstream's hidden tests passed about equally often without and with Compound (23 and 23 of 28 runs with Opus; 23 and 21 of 28 runs with Sonnet). With Compound, a new test was shown failing before the fix in 28 of 28 runs with Opus and 26 with Sonnet, against none without (stock Opus checked its test against the unfixed code after fixing, in 20), and the whole suite ran on the final code in 19 → 22 and 8 → 25. [Real bugs](#real-bugs)
- **Safe refactors and stronger tests**, on six tasks written for this benchmark that Compound was partly tuned on (10 runs per task, arm and model). A refactor whose obvious version silently changes tax rounding kept it in 10 of 10 runs with each model, against 5 of 10 with Opus and 0 of 10 with Sonnet without Compound. The tests each run left behind caught 96 of 110 planted regressions against 81 with Opus, and 83 against 57 with Sonnet.
- **Clean commits.** With Compound, 0 of 30 bug-fix commits with Opus and 1 of 30 with Sonnet had an AI co-author line, against all 30 without; subjects followed Conventional Commits in 57 of 60.
- **A map of your code.** On 240 commits not used to tune it, the map put 74% of each commit's changed files in its top 4, against 51% for a word-count search, and answers in about 0.4 seconds once running. Whether it improves the agent's results is not measured.

**What it costs**

- **Per bug fix**, the median run at API list prices: 9–12¢ → 16–19¢ and 5–16 seconds longer with Opus; 3.5–5.4¢ → 4.8–7.3¢ and 5–8 seconds longer with Sonnet. Across the six tasks, weighted equally, paired runs cost 1.55× with Opus and 1.68× with Sonnet. On a subscription, the extra comes out of your usage limits.
- **Reviews and questions cost the most, for no measured gain:** a Flask review cost 1.8× with Opus and 2.8× with Sonnet and found the same planted defects. [Where it doesn't help](#where-it-doesnt-help-reviews-and-questions)
- **A plain question** costs the same: the skill did not load on any of 20 general Python questions, and the always-on rule adds about 420 tokens to each request.

**What it changes**

- **Only what you asked for.** From 0.15.0, Compound tells the agent to change only what a request covers, and the repository check-up, which may tidy or delete files, runs only when you ask for `compound setup`. In our runs, given a first bug fix in a repository it had not assessed, with the user's uncommitted notes, 0.14.0's agent started the check-up in 0 of 6 runs and 0.15.0's in 0 of 6, and the notes survived in all 12; 0.15.0 removes the instruction itself.
- **Commits** follow your project's conventions, defaulting to subjects such as `fix: …`, and leave out AI co-author trailers and generated-by lines; required AI-use disclosures stay.
- **Your machine** gets a rule for each app, a cache folder that setup adds to Codex's and Cursor's sandbox write paths, and a map service on `127.0.0.1:43127`. There are no hooks and no MCP servers, and Compound's scripts connect to nothing but 127.0.0.1. [What it writes and how to remove it](#what-it-changes-on-your-machine)

**Skip it, or use it in one chat only, if** most of your agent work is reviews and questions, you are close to your plan's usage limit, or you need evidence outside Python projects in Claude Code.

**Alternatives.** A five-sentence rule in CLAUDE.md asking for the same debugging habits did as well on them in our tasks, at 1.35× (Opus) and 1.41× (Sonnet) the stock cost against Compound's 1.54× and 1.68× in the same run; but it kept the AI co-author line in every commit, and with Sonnet it broke the refactor in all 5 runs where Compound broke none. [The rule, and the comparison](#isnt-this-just-a-rule-in-claudemd). Every's Compound Engineering and pstack are broader suites driven by commands you type: with plain prompts their skills did not run, and started with their own commands they also reproduced bugs first, at 2–11× Compound's cost per Opus bug fix. [Compared](#compared-with-other-plugins)

For bug fixes and refactors in projects with tests, Compound returns the same fixes with the bug reproduced, a failing test shown first and the suite run, and keeps refactors safe, for a few cents and seconds more per task; for reviews and questions it adds cost without a measured gain.

## Install

1. Install the plugin at **User** scope in each app you use (below).
2. Start a new chat (`/reload-plugins` also works in Claude Code) and turn Compound on for every project, once, from any app:<br>
   `/compound-skills:setup-global` in Claude Code<br>
   `$setup-global` in Codex<br>
   `/setup-global` in Cursor
3. Start a new chat and just ask for what you want.

To try it first without saving any setting, type `compound` in one chat (`/compound-skills:compound` in Claude Code, `$compound` in Codex, `/compound` in Cursor). After updating the plugin, run `setup-global` again: rules saved by an earlier version keep their old text.

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

### What it changes on your machine

- **Claude Code:** `setup-global` writes the rule `~/.claude/rules/compound-skills.md` (it respects `CLAUDE_CONFIG_DIR`).
- **Codex:** `setup-global` adds a marked section to `$CODEX_HOME/AGENTS.md`, and to an existing nonempty `AGENTS.override.md`.
- **Cursor:** the plugin carries its own `compound-default` rule.
- **State folder:** `~/.cache/compound-skills` (`COMPOUND_SKILLS_STATE_DIR` moves it) holds the map's cache and a record of which repositories `compound setup` assessed. `setup-global` adds its path to Codex's `sandbox_workspace_write.writable_roots` in `config.toml` and to Cursor's `additionalReadwritePaths` in `~/.cursor/sandbox.json`, keeping every other setting.
- **The map service** listens on `127.0.0.1:43127` (`COMPOUND_MAP_PORT` changes the port). It starts on the first map query of a task that may edit files, or on `map`, and runs until `map stop` or you log out. It accepts only requests from its own page, but any program on your machine can read its maps and source previews while it runs.
- **A project `setup`** adds a marked section to that project's `AGENTS.md`, a file you would commit, and assesses the project.
- **Not included:** hooks, MCP servers, other background processes, or network access. Compound's scripts connect to nothing but 127.0.0.1, and the map page loads nothing from elsewhere. Your code still goes to your model provider, as with any coding agent.

These are instructions to the agent, not enforcement; project instructions and your explicit requests take priority ([activation](skills/compound/references/activation.md)).

### Remove it

1. Run `compound disable global` from any app. It removes only the sections and rule files setup wrote.
2. In Cursor, set `compound-default` to **Manual**, or remove the plugin.
3. Run `map stop` if the map service is running.
4. Uninstall the plugin in each app (in Claude Code, `/plugin uninstall compound-skills@compound-skills`).
5. Delete `~/.cache/compound-skills`, and its entry in Codex's `writable_roots` and Cursor's `additionalReadwritePaths` if you want them gone too.

## Use it

Each command takes your app's prefix, for example `/compound-skills:map` in Claude Code, `$map` in Codex and `/map` in Cursor.

| What you want | Command |
| --- | --- |
| Turn it on for every project (once, from any app) | `setup-global` |
| Check that it is on | `status-global` |
| Assess and tidy the current project (the only time it changes files you did not name) | `setup` |
| Open the code map | `map` |
| Check or stop the map service | `map status`, `map stop` |
| Use it in this chat only | `compound` |
| Remove the global setting | `compound disable global` |

<details>
<summary>Exact command for each app</summary>

| What you want | Claude Code | Codex | Cursor |
| --- | --- | --- | --- |
| Turn it on for every project (once, from any app) | `/compound-skills:setup-global` | `$setup-global` | `/setup-global` |
| Check that it is on | `/compound-skills:status-global` | `$status-global` | `/status-global` |
| Assess and tidy the current project | `/compound-skills:setup` | `$setup` | `/setup` |
| Open the code map | `/compound-skills:map` | `$map` | `/map` |
| Use it in this chat only | `/compound-skills:compound` | `$compound` | `/compound` |
| Remove the global setting | `/compound-skills:compound disable global` | `$compound disable global` | `/compound disable global` |

</details>

## Benchmark

Every result comes from [bench/](bench/README.md), which runs headless Claude Code side by side in isolated sandboxes, once per arm, and grades what each run did and left behind:

- **Real bugs:** 12 bugs fixed upstream in 2026, stock against Compound. The first four ran 3 times per arm and model; eight more were frozen before any run and ran twice.
- **Six controlled tasks** written for this benchmark (three bug reports and a refactor in a small billing library, a Flask review and a Django question), plus a plain question: stock against Compound in two runs of 5 per task, the second adding a plain-rule arm.
- **Other plugins**, on the same tasks: Every's Compound Engineering and pstack, with plain prompts (3 runs per task) and with their own commands (2 runs).

Outcome measures are hidden tests, upstream's own tests, planted regressions and a blind judge. The habit measures check Compound's own instructions, so read them as compliance with its checklist. All agent tasks are Python projects run in Claude Code. The runs used Compound's 0.14.0 skill text; 0.15.0 changes only when the repository check-up runs, measured [separately](#cost-and-time).

### Real bugs

Each run got the project at the commit before the upstream fix, with its history and test suite, and a report that describes only the symptom. The fix's own new tests stayed hidden, and the project's whole suite had to pass. The chart above pools all 12. On the first four (3 runs each per arm and model), Opus reproduced the bug first in 12 of 12 runs with Compound against 5 without, showed a new test failing before the fix in 12 against 0, and fixed 9 against 9; Sonnet reproduced the bug first in 12 of 12 runs with Compound against 0 without, showed a new test failing before the fix in 12 against 0, and fixed 9 against 9. On the eight newer ones (2 runs each), Opus reproduced the bug first in 16 of 16 runs with Compound against 0 without, showed a new test failing before the fix in 16 against 0, and fixed 14 against 14; Sonnet reproduced the bug first in 14 of 16 runs with Compound against 0 without, showed a new test failing before the fix in 14 against 0, and fixed 12 against 14. Without Compound, a new test was shown failing on the unfixed code only after the fix, with the fix set aside: in 20 of 28 Opus runs and 4 Sonnet runs. So by the end of a run stock Opus often had the same evidence, gathered after the fix instead of before it.

Bug by bug and model, fixes were level on 23 of 24 pairs, ahead with Compound on 0 and behind on 1; with this few runs per bug, those differences are within noise. The one behind was attrs with Sonnet: both fixes with Compound stopped the renaming and passed the whole suite, but named each class's copy `evolve`, where upstream's test also expects `__replace__`. No run, with or without Compound, fully fixed two bugs: each fixed the case its report described, but upstream's tests also cover a case the report did not mention: click's progress bar, which upstream also tests through `bar.update()` where the report describes a loop; and packaging's dependency groups, where upstream also requires a group included twice to be reported once. The extra steps took more time and money: a median real fix took 44 → 68 seconds with Opus and 29 → 45 seconds with Sonnet.

<details>
<summary>The 12 bugs, and how the second set was frozen</summary>

- **flask**, fixed 2026-07-14: `app.run()` crashes on an IPv6 `SERVER_NAME` ([fix](https://github.com/pallets/flask/commit/7203feabf723)). Opus fixed 3 → 3 of 3 · Sonnet fixed 3 → 3 of 3.
- **flask**, fixed 2026-07-14: the test client loses the session with an IPv6 `base_url` ([fix](https://github.com/pallets/flask/commit/de8429ffda8c)). Opus fixed 3 → 3 of 3 · Sonnet fixed 3 → 3 of 3.
- **click**, fixed 2026-08-28: pickling a click option fails ([fix](https://github.com/pallets/click/commit/f58ca3e81424)). Opus fixed 3 → 3 of 3 · Sonnet fixed 3 → 3 of 3.
- **click**, fixed 2026-08-15: a progress bar stops at 14/20 ([fix](https://github.com/pallets/click/commit/f316d5cb3aa8)). Opus fixed 0 → 0 of 3 · Sonnet fixed 0 → 0 of 3.
- **attrs**, fixed 2026-08-02: defining a class renames `attrs.evolve` ([fix](https://github.com/python-attrs/attrs/commit/f53fc5440d7f)). Opus fixed 2 → 2 of 2 · Sonnet fixed 2 → 0 of 2.
- **packaging**, fixed 2026-08-08: `platforms=[]` still yields this machine's platform tags ([fix](https://github.com/pypa/packaging/commit/4e79787a31c9)). Opus fixed 2 → 2 of 2 · Sonnet fixed 2 → 2 of 2.
- **packaging**, fixed 2026-10-05: a later spelling of a `LicenseRef` overwrites the first ([fix](https://github.com/pypa/packaging/commit/2c87a33f6658)). Opus fixed 2 → 2 of 2 · Sonnet fixed 2 → 2 of 2.
- **packaging**, fixed 2026-10-07: a pylock path with mixed separators fails to load ([fix](https://github.com/pypa/packaging/commit/fa52d7237a74)). Opus fixed 2 → 2 of 2 · Sonnet fixed 2 → 2 of 2.
- **packaging**, fixed 2026-10-05: only the first malformed dependency group is reported ([fix](https://github.com/pypa/packaging/commit/959bb79c06cb)). Opus fixed 0 → 0 of 2 · Sonnet fixed 0 → 0 of 2.
- **marshmallow**, fixed 2026-08-21: `TimeDelta` crashes on "nan" instead of reporting a validation error ([fix](https://github.com/marshmallow-code/marshmallow/commit/7dff08fcb7fb)). Opus fixed 2 → 2 of 2 · Sonnet fixed 2 → 2 of 2.
- **marshmallow**, fixed 2026-08-08: `validate.URL` rejects a link with a fragment but no path ([fix](https://github.com/marshmallow-code/marshmallow/commit/902f99c4151d)). Opus fixed 2 → 2 of 2 · Sonnet fixed 2 → 2 of 2.
- **marshmallow**, fixed 2026-10-18: `Pluck` ignores an empty `data_key` ([fix](https://github.com/marshmallow-code/marshmallow/commit/5761beab3985)). Opus fixed 2 → 2 of 2 · Sonnet fixed 2 → 2 of 2.

The eight newer bugs were picked from fixes merged in August to October 2026 and frozen in commit c009f70 before any agent ran them. Before any run, setup's check found three problems, fixed in cd7da53: marshmallow puts the clock in some test ids, which setup now ignores; three reproduction patterns had an escaping mistake; and a werkzeug bug was dropped because its suite starts dev servers that hang in the sandbox.

</details>

### Isn't this just a rule in CLAUDE.md?

For the debugging habits, mostly yes. In the same run as stock Claude Code and Compound, one arm had no plugin and only this always-on rule:

> Before fixing a reported bug, reproduce it by running the code. Add a regression test and show that it fails on the unfixed code. Run the full test suite after your last change. Before a refactor, record current behaviour and compare afterwards. In your final message, list what you ran and what you did not verify.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-rule-dark.svg">
  <img src=".github/assets/benchmark-rule.svg" alt="Isn't this just a rule in CLAUDE.md? The same six tasks with no plugin, with only a five-sentence rule asking for the habits, and with Compound Skills 0.14.0: 5 runs per arm, task and model, side by side. Fixed the bug (hidden tests pass): Opus stock 15 of 15, Opus plain rule 15 of 15, Opus Compound 15 of 15, Sonnet stock 15 of 15, Sonnet plain rule 15 of 15, Sonnet Compound 15 of 15. Planted regressions the tests left behind catch: Opus stock 41 of 55, Opus plain rule 46 of 55, Opus Compound 47 of 55, Sonnet stock 28 of 55, Sonnet plain rule 40 of 55, Sonnet Compound 41 of 55. Refactor kept tax rounding and removed both helpers: Opus stock 3 of 5, Opus plain rule 5 of 5, Opus Compound 5 of 5, Sonnet stock 0 of 5, Sonnet plain rule 0 of 5, Sonnet Compound 5 of 5. Ran the whole suite on the final code: Opus stock 15 of 15, Opus plain rule 15 of 15, Opus Compound 15 of 15, Sonnet stock 15 of 15, Sonnet plain rule 14 of 15, Sonnet Compound 15 of 15. Reproduced the bug before changing code: Opus stock 0 of 15, Opus plain rule 15 of 15, Opus Compound 15 of 15, Sonnet stock 0 of 15, Sonnet plain rule 15 of 15, Sonnet Compound 15 of 15. Showed a new test failing before the fix: Opus stock 0 of 15, Opus plain rule 15 of 15, Opus Compound 15 of 15, Sonnet stock 0 of 15, Sonnet plain rule 15 of 15, Sonnet Compound 15 of 15. Committed without an AI co-author line: Opus stock 0 of 15, Opus plain rule 0 of 15, Opus Compound 15 of 15, Sonnet stock 0 of 15, Sonnet plain rule 0 of 15, Sonnet Compound 15 of 15. List-price cost vs stock, six tasks weighted equally: Opus stock 1.00×, Opus plain rule 1.35×, Opus Compound 1.54×, Sonnet stock 1.00×, Sonnet plain rule 1.41×, Sonnet Compound 1.68×. Planted regressions: 55 per arm and model over the three bugs and the refactor. The tasks were written for this benchmark and Compound was partly tuned on them.">
</picture>

The rule reproduced every bug first and showed a failing test, as Compound did, and cost less: 1.35× stock with Opus and 1.41× with Sonnet, against 1.54× and 1.68×, so Compound cost 1.14× and 1.26× as much as the rule. If those habits are all you want, copy it. What Compound added on these tasks: no AI co-author line in its commits (15 of 15 against 0 of 15), a safe refactor with Sonnet (5 of 5 against 0 of 5), more planted regressions caught after Opus's refactor, and the map. The rule names exactly the habits being scored, and Compound's own always-on rule asks for three of the same five, so most of the gap measures the skill, its guides and the map. We added the rule arm after the run began, so 10 of its 35 groups with Opus and 7 with Sonnet ran in a second pass; its cost multiples come only from the 25 and 28 groups that ran side by side with stock.

### Compared with other plugins

Every's Compound Engineering 3.34.0 (commit 3449230, 36 skills) and pstack 0.15.36 (commit 4dd1d05, its Claude Code copy, 58 skills), installed as their READMEs say, on the three bugs and the refactor. With plain prompts, their skills did not run in any task and the results looked like stock Claude Code's, at a little more cost. Started with the command each one tells you to type, both reproduced bugs first (Every's in 12 of 12 runs, pstack in 9 of 12), at 2–11× Compound's cost per Opus bug fix and 1.5–2.8× per Sonnet fix in the same run, and both kept AI co-author lines.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-compared-dark.svg">
  <img src=".github/assets/benchmark-compared.svg" alt="Compared with other plugins. Every's Compound Engineering 3.34.0 and pstack 0.15.36, installed as their READMEs say, on the three bugs and the refactor; Claude Opus 5.5 and Sonnet 5.5 together. With plain prompts, as everyone else ran; then started with the command each one tells you to type. Fixed the bug (hidden tests pass): stock 18 of 18, Every's Compound Engineering with plain prompts 18 of 18, pstack with plain prompts 18 of 18, Every's Compound Engineering with its commands 12 of 12, pstack with its command 12 of 12, Compound 18 of 18. Planted regressions the tests left behind catch: stock 45 of 66, Every's Compound Engineering with plain prompts 38 of 66, pstack with plain prompts 42 of 66, Every's Compound Engineering with its commands 30 of 44, pstack with its command 30 of 44, Compound 52 of 66. Refactor kept tax rounding and removed both helpers: stock 3 of 6, Every's Compound Engineering with plain prompts 1 of 6, pstack with plain prompts 1 of 6, Every's Compound Engineering with its commands 0 of 4, pstack with its command 2 of 4, Compound 6 of 6. Reproduced the bug before changing code: stock 0 of 18, Every's Compound Engineering with plain prompts 0 of 18, pstack with plain prompts 0 of 18, Every's Compound Engineering with its commands 12 of 12, pstack with its command 9 of 12, Compound 18 of 18. Showed a new test failing before the fix: stock 0 of 18, Every's Compound Engineering with plain prompts 0 of 18, pstack with plain prompts 0 of 18, Every's Compound Engineering with its commands 12 of 12, pstack with its command 9 of 12, Compound 18 of 18. Committed without an AI co-author line: stock 0 of 18, Every's Compound Engineering with plain prompts 0 of 18, pstack with plain prompts 0 of 18, Every's Compound Engineering with its commands 0 of 12, pstack with its command 0 of 12, Compound 18 of 18. Median cost of a bug fix, Opus 5.5: stock 10¢, Every's Compound Engineering with plain prompts 11¢, pstack with plain prompts 12¢, Every's Compound Engineering with its commands 183¢, pstack with its command 32¢, Compound 17¢. Median cost of a bug fix, Sonnet 5.5: stock 3.5¢, Every's Compound Engineering with plain prompts 4.4¢, pstack with plain prompts 4.0¢, Every's Compound Engineering with its commands 17¢, pstack with its command 9.5¢, Compound 5.6¢. Stock and Compound ran with plain prompts. Plain prompts: 3 runs per task and model. Commands (/ce-debug and /ce-work for Every's CE, /poteto-mode for pstack): 2 runs, in a separate run with its own stock arm. The tasks were written for this benchmark and Compound was partly tuned on them.">
</picture>

<details>
<summary>How each plugin ran</summary>

- **Every's Compound Engineering:** the repository's Claude Code plugin, unchanged. We skipped its optional `/ce-setup`, which writes a config file into the project. Commands: `/compound-engineering:ce-debug` for the bugs and `/compound-engineering:ce-work` for the refactor, as its skill descriptions direct. Its code review sends some reviewer agents to Sonnet even in Opus sessions; that cost is counted.
- **pstack:** the generated Claude Code copy in `cursor/plugins/harness/pstack/claude-code`. Its setup, `/setup-pstack`, writes a rule mapping roles to models; we wrote that rule with every role on the session's model, one of the choices it offers, so each run stayed on the model under test. Command: `/pstack:poteto-mode`, which its README says to use for anything that needs rigor.
- **Anthropic:** Claude Code's bundled debug, verify and code-review skills were available in every arm, stock included; Anthropic's public skills repository (checked at ca45fc4) holds document, design and API skills, none for debugging, testing or review.
- **Scope:** single bug fixes and a refactor on tasks Compound was partly tuned on; not their planning loops or parallel orchestration. The plain-prompt and command passes were separate runs, each with its own stock arm.

</details>

### Cost and time

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-cost-dark.svg">
  <img src=".github/assets/benchmark-cost.svg" alt="What it costs per task. Median list-price cost and time per run on the six controlled tasks and a plain question, with and without Compound Skills 0.14.0: 10 runs per task, arm and model, from two runs on the same day. Claude Opus 5.5: Bug: refund split 12.4¢ and 30 s without, 18.7¢ and 35 s with Compound; Bug: leap-year proration 10.7¢ and 23 s without, 17.1¢ and 36 s with Compound; Bug: December due date 8.9¢ and 22 s without, 15.8¢ and 38 s with Compound; Refactor: rounding helpers 16.6¢ and 33 s without, 25.1¢ and 46 s with Compound; Review a Flask commit 11.2¢ and 32 s without, 20.5¢ and 50 s with Compound; Question about Django 15.4¢ and 29 s without, 18.7¢ and 44 s with Compound; Plain Python question 0.6¢ and 3 s without, 0.7¢ and 4 s with Compound. Claude Sonnet 5.5: Bug: refund split 5.4¢ and 23 s without, 7.3¢ and 28 s with Compound; Bug: leap-year proration 4.2¢ and 17 s without, 7.2¢ and 26 s with Compound; Bug: December due date 3.5¢ and 15 s without, 4.8¢ and 21 s with Compound; Refactor: rounding helpers 5.4¢ and 21 s without, 8.5¢ and 29 s with Compound; Review a Flask commit 2.6¢ and 17 s without, 7.3¢ and 32 s with Compound; Question about Django 3.8¢ and 17 s without, 6.8¢ and 33 s with Compound; Plain Python question 0.3¢ and 4 s without, 0.3¢ and 4 s with Compound. Right: the extra cents per run and the ratio of the two medians. Across the six tasks weighted equally, paired runs cost 1.55× with Opus and 1.68× with Sonnet.">
</picture>

Cents and seconds are medians per run at API list prices, as Claude Code reports them. Multiples are geometric means of paired ratios with the tasks weighted equally: 1.55× (95% interval 1.49–1.61) with Opus and 1.68× (1.57–1.79) with Sonnet over 60 pairs each, for 1.53× and 1.54× the context tokens. Reviews are the costliest: with Compound, every review tried to run the code, which the benchmark blocks, so read-only tasks hit 87 blocked commands against 34 without; in everyday use that means more permission prompts. The always-on rule adds about 420 tokens to each request.

0.15.0's only change from the measured 0.14.0, running the check-up only on `compound setup`, was tested against 0.14.0 on the same tasks, side by side: the same habits (12 and 12 of 12 bugs reproduced first, the refactor safe in 4 and 3 of 4), a first bug fix in a new repository reproduced first in 6 and 6 of 6, and it cost 1.02× as much with Opus and 0.94× with Sonnet over 8 pairs per model.

We also tried a 30% shorter skill text against 0.14.0, in 30 pairs per model: it kept every measured habit but did not lower cost (1.04× with Opus, 0.99× with Sonnet), and Sonnet's reviews drew more incorrect statements, so it did not ship ([CHANGELOG](CHANGELOG.md)).

### Where it doesn't help: reviews and questions

No measured gain. A blind judge graded every Flask review and Django answer against a fixed key, in two runs: every review found all three planted defects in both arms (20 of 20 each). Opus covered all 11 Django key points in 9 of 10 answers without Compound and 7 of 10 with it; Sonnet's answers covered a median of 9 either way. The judge counted 13 incorrect statements without Compound and 9 with it for Opus, and 12 and 15 for Sonnet. Every arm could read the code but not run it, and no review or question changed the repository.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-answers-dark.svg">
  <img src=".github/assets/benchmark-answers.svg" alt="Reviews and answers graded blind in the first run, 5 per task, arm and model. Every review found all 3 planted defects in both arms. All 11 Django key points: Opus 4 of 5 answers without Compound and 5 of 5 with it; Sonnet's median answer covered 9 of 11 in both arms. Incorrect statements in the 10 reviews and Django answers: Opus 3 without and 3 with, Sonnet 5 without and 9 with.">
</picture>

### Individual runs

<details>
<summary>One bug fix side by side, and the 30 Opus bug-fix runs step by step</summary>

An example chosen before the runs: repetition 1 of the December bug on Claude Opus 5.5, in the first 0.14.0 run. Both runs fixed the bug, added a test, noticed that plain EOM terms were wrong too and committed. The highlighted sentences appear only in the report with Compound.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-reports-dark.svg">
  <img src=".github/assets/benchmark-reports.svg" alt="The final reports from rep 1 of the December bug on Claude Opus 5.5. Both fixed the bug, added a test that checks the reported example, noticed that plain EOM terms were wrong too and committed. Only the report with Compound says the new test failed before the fix, with 2023-12-31 != 2024-12-31, that it also called due_date with the reported example, that it found no other code doing the same month arithmetic, and that the commit has no Claude co-author trailer.">
</picture>

Only the report with Compound says “Before the fix it failed (`2023-12-31 != 2024-12-31`)” and that the commit “has no Claude co-author trailer”. The run without Compound also searched for the same month arithmetic and checked the reported example, but ran its tests only once, after the fix.

Each row below is one run, lined up on its first source edit; marks to the left happened before it.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-steps-dark.svg">
  <img src=".github/assets/benchmark-steps.svg" alt="The 30 Claude Opus 5.5 runs on the three bug reports, without Compound and with 0.14.0, each as a row of steps lined up on its first source edit. Without Compound, 14 of 15 runs started by editing the source. With Compound, all 15 showed a failing test before their first source edit.">
</picture>

Without Compound, 14 of 15 runs started by editing the source; the other ran Python first, but only tried pytest, which is not installed for this library. With Compound, all 15 showed a failing test before their first source edit.

</details>

### How we measured, and check our numbers

Claude Code 2.1.316 in headless mode, Claude Opus 5.5 and Claude Sonnet 5.5 at default effort, on 31 October 2026. The arms of a group started together in isolated sandboxes with identical paths, one CPU each, in rotating order. Prompts never mention a plugin, except the commands the other plugins ask their users to type. Write tasks may run code and commit; read tasks may only read; web access and installs are blocked in every arm.

<details>
<summary>Method: arms, tasks, scoring, detectors and corrections</summary>

- **Arms.** Stock was Claude Code as installed, with its bundled skills. Compound ran as a plugin plus the always-on rule its `setup-global` writes. The rule arm had no plugin, only the rule quoted above as a user rule. The other plugins are described above.
- **Tasks.** A small billing library written for this test, whose own tests miss its three bugs, and a refactor whose obvious version changes tax rounding; a Flask commit with three planted defects to review; a question about Django's 7,085 files; a plain Python question; and the real bugs above. No prompt mentions tests, a plugin or the map.
- **Scoring.** Hidden tests; 11 planted regressions run against the tests each agent left on the controlled tasks; upstream's new tests and the whole suite on the real bugs; a logging wrapper around `python` that records what ran on which version of the code; and a blind judge (Claude Opus 5.5, also one of the agents under test) that must quote the answer for each point it awards: three votes per answer in the first run, one in the second.
- **Detectors.** The habit detectors were checked by two arm-blind AI labellers in our first benchmark, agreeing on 45 to 47 of 48 Opus traces and on all 48 Sonnet traces.
- **Runs.** 10 runs per controlled task, arm and model across two runs with identical skill files; 3 per original real bug and 2 per new one. None of the 714 runs counted was invalid.
- **Corrections.** In the first run, the judge's copy of the Flask commit showed an old commit id, so 40 votes called the id wrong; we dropped those complaints and fixed the harness. One Sonnet group lost its log of Python calls when another benchmark started beside it; we gave every run its own logger and ran the group again. The rule arm's first groups ran in a second pass, after we added the arm. After the runs, we found the reproduction detector missed the short failure output of `pytest -q` (`1 failed, 50 passed`, `FAILED tests/…`); rescoring every arm's runs with the wider pattern raised Compound's real-bug reproductions from 24 to 28 with Opus and from 20 to 26 with Sonnet, and changed no stock run.

</details>

You can rerun the headline yourself. With the [requirements](bench/README.md) in place (Linux with user namespaces, the `claude` CLI and a sign-in), this runs every real bug once per arm with Sonnet, about $2 at list prices:

```bash
python3 bench/bench.py setup
python3 bench/bench.py run --label check --arms without,with --tasks real --models sonnet
python3 bench/bench.py report --label check
```

## The code map

![The Compound code map of the open-source Hono repository. Hovering context.ts lights up the 8 files it imports and the 73 files that import it, and fades the rest of the graph.](.github/assets/code-map.svg)

- **Explore it.** Hover a file to light up its connections, drag it to pull its neighbors along, and scroll or pinch to zoom.
- **See what a change touches.** **Impact** shows the files that import the one you picked, directly or through other files, as far as the map resolves imports. **Trace** finds how two files connect, and **Changed** shows your Git edits and their neighbors.
- **Read without switching apps.** Search files, folders, and symbols, preview source, and copy a compact summary into your chat.
- **Your agent asks it first.** Before searching a repository, the agent queries the map once, unless the task names its file. With 0.14.0 it ran a map query in 115 of the 120 runs with Compound on the six controlled tasks; in the other five, Sonnet's read-only permissions blocked the command.
- **Languages.** Imports are linked for Python, JavaScript, TypeScript, Go, and Rust. Symbols are outlined for those plus Java, C, C++, C#, Ruby, PHP, Swift, and Kotlin.

![Four views of the Compound code map on the Hono repository: Impact for url.ts, which counts 219 dependent files; Trace, showing the import path from hono.ts through the trie router to node.ts; Changed, with the two edited files ringed among the files wired to them; and the source preview of the smart router.](.github/assets/code-map-views.svg)

The map opens at `http://127.0.0.1:43127/` and keeps its data in your user cache, outside the repository. Coverage and limits: [code maps](skills/compound/references/map.md).

### How fast is it?

Six of seven repositories build in under 2.5 seconds the first time and in under 0.3 seconds when nothing changed; Django, with 7,085 files, takes 8.20 and 2.29 seconds. Once the local service is running, an agent's later queries take about 0.4 seconds, and 0.97 on Django.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/map-speed-dark.svg">
  <img src=".github/assets/map-speed.svg" alt="How fast the code map is on seven repositories from 130 to 7,085 files. First builds take 0.41 to 2.48 seconds, and 8.20 on Django; rebuilds when nothing changed take 0.05 to 0.27 seconds, and 2.29 on Django; an agent's later queries take 0.38 to 0.43 seconds, and 0.97 on Django.">
</picture>

Median of 5 runs on 4 cores with Python 3.13.17, timed on 0.13.0; the map code has not changed since.

### Does it find the files a change touches?

Usually, and more often than a word-count search. For 240 real commits not used to tune it, 60 each from Flask, Click, Hono and Gin, we queried the map with each commit's title: it put 74% of the source files each commit changed in its top 4, against 51% for word-count search and 4% at random, and was ahead on 73 commits to the search's 11; on Click the gap was small enough to be noise.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/map-retrieval-dark.svg">
  <img src=".github/assets/map-retrieval.svg" alt="Share of each commit's changed source files in the map's top 4, on 60 held-out commits each from Flask, Click, Hono and Gin: the current map 74% on average, against 48% for the map in 0.12.1, 51% for word-count search and 4% at random.">
</picture>

<details>
<summary>How the ranking works and how we tested it</summary>

It was clearly ahead on Flask (60% against 35%, ahead on 21 commits to the search's 4), Hono (75% against 34%, 27 commits to 0) and Gin (81% against 63%, 15 commits to 2). On Click it was slightly ahead (81% against 73%, 10 commits to 5), a gap small enough to be noise.

The map weighs the query's rarer words in file paths, symbols and the text of its 50 leading candidates, favors larger and widely imported code files, and lists tests lower unless the query mentions tests. We tuned it on the 60 most recent such commits of Flask, Click and Hono; Gin, a Go project, was used only for this check. Part of the gain comes from listing tests lower, since only non-test files were scored: a word search that also skips common words and lists tests last put 67% in its top 4, about level with the map on Click and Gin. Each commit's parent was copied into a fresh repository without history, so the map's co-change hints played no part. The newer ranking made later queries 0.03 to 0.09 seconds slower than in 0.12.1 and a coding task's first query 0.04 to 1.19 seconds slower.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/map-retrieval-detail-dark.svg">
  <img src=".github/assets/map-retrieval-detail.svg" alt="Share of each commit's changed source files in the map's top 4 and top 12 for Flask, Click, Hono and Gin, against the map in 0.12.1, word-count search and random order. The current map found 60% and 96% on Flask, 81% and 95% on Click, 75% and 90% on Hono, and 81% and 92% on Gin.">
</picture>

</details>

## Limits

- **Python projects in Claude Code only.** Every agent task is a Python project run in headless Claude Code; Codex and Cursor load the same skill files but were not measured.
- **Small samples.** Two or three runs per real bug, 10 per controlled task and 2 or 3 per task in the head-to-head can miss small effects.
- **Partly tuned on the controlled tasks.** Compound's rule sentence and refactor guide were revised after earlier runs of the same six tasks, and the rule and head-to-head comparisons ran on them. The real bugs were new to the benchmark.
- **The habit measures are Compound's own checklist,** and the plain rule names them too; the outcomes are what tests and the judge measured.
- **The judge** is Claude Opus 5.5, also one of the agents under test.
- **Other plugins** ran as we set them up, on tasks of our choosing, and the benchmark's author also wrote Compound; their larger workflows were not tested.
- **The map's** effect on the agent's results is not measured; its ranking was tuned on other Flask, Click and Hono commits.
- **Instructions, not enforcement.** Compound asks the agent; it cannot force it.

## Reference

### What each guide asks for

Compound has one short guide for each kind of work and tells the agent to read the one that fits; the benchmark exercised the debug, refactor, review, investigate and Git guides.

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

### What loads when

- **Every request:** the always-on rule, about 420 tokens.
- **Each engineering task:** the `compound` skill, once, then the map query.
- **When a task needs it:** one guide, such as the debug guide for a bug.

### Commits

Your project's conventions come first; otherwise subjects follow Conventional Commits (`fix: …`). Compound leaves out AI co-author trailers and generated-by lines, even when a template or earlier commits have them; it keeps human co-authors, sign-offs and required AI-use disclosures, and your configured Git identity.

## Credits

Adapted selectively from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), which is also one of the benchmark arms, with lineage from earlier Karpathy-inspired guidelines and the Claude-Mem local-service concept. Not affiliated with Every or its Compound Engineering plugin. See [SOURCES.md](SOURCES.md), [third-party notices](THIRD_PARTY_NOTICES.md), the [changelog](CHANGELOG.md) and the [MIT license](LICENSE).
