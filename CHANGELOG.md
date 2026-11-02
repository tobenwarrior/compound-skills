# Changelog

Notable changes to Compound Skills, newest first. Every change is in the Git history; benchmark numbers come from [bench/](bench/README.md) and are explained in the [README](README.md#benchmark).

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
