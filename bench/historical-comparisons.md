# Historical benchmark comparisons

The [main README](../README.md#benchmark) presents without Compound / with Compound. This methodology appendix retains the plain-rule controls, other plugins, map ablations, individual tasks and corrections. These are saved historical measurements, not new runs or measurements of the current checkout. The original multi-arm charts are retained here; the main README summaries select only the control and Compound arms from those measurements.

### Historical Claude Code rounds

These used default effort, Claude Code 2.1.316 unless noted, and the versions below. They remain evidence about those versions; the small DeepSeek workflows do not replace them.

- **0.16.0 round, 1 November 2026:** stock, the plain rule, Compound before its 0.16.0 redesign, and that version without its map query ran side by side on 12 real bugs (2 runs per bug, arm and model), 3 held-out refactors (5 runs each) and a Flask review (3 runs). The redesign, which is 0.16.0, ran just after them on the same tasks and is paired with them by task, model and repetition. Stock, the rule and 0.16.0 then ran side by side on a Django question and a plain question (3 runs each).
- **Second 0.16.0 round, 1 November 2026:** stock, the plain rule, Compound before its redesign and 0.16.0 as shipped started together in every group, in Claude Code 2.1.312, on the same 12 real bugs (1 run per bug, arm and model), 3 held-out refactors, the Flask review, the Django question and the plain question (2 runs each). [Second round](#second-round-side-by-side)
- **Earlier rounds with 0.14.0, 31 October 2026:** six controlled tasks written for this benchmark, which Compound was partly tuned on, against stock, the rule and two other plugins; and the same 12 real bugs against stock. [Earlier rounds](#earlier-rounds-with-0140)

Outcome measures are hidden tests, upstream's own tests, planted wrong fixes and refactors, and a blind judge. The habit measures check Compound's own instructions, so read them as compliance with its checklist.

### Held-out refactors

Three refactors in shopkit, a small library written after Compound's refactor guide and frozen in commit f2faf1f before any agent ran it. Each asks to merge two near-duplicate helpers whose obvious merge changes one caller:

- **Slugs:** product URLs strip accents and cap their length, while search facet keys keep letters and punctuation.
- **Retries:** a card charge must not be retried after a lost connection, since it may already have gone through, while webhook deliveries retry more often and back off further.
- **Money:** the supplier importer accepts `$` and accounting negatives such as `(12.00)` and rounds half up, while the refunds API rejects both and rounds half to even.

Hidden tests check every caller through the public API, and each task has three planted wrong refactors that the tests a run leaves behind should catch. Before any measured run, three agents asked to refactor carefully each passed every check, so each task can be done right as posed.

Compound got all three right in all 30 of its runs. Stock never got the slugs refactor right: in all 10 of its runs, the merged helper changed product URLs or facet keys. The rule did the same in all 5 Sonnet runs; with Opus, it kept the behavior in 4 runs by leaving both helpers in place, which the task asked it to remove, and changed it in the fifth. On retries and money, stock and the rule got 39 of 40 runs right; the miss was a Sonnet run with the rule that left the money helpers in place. The tests each run left behind tell the same story: Compound's caught all 45 planted wrong refactors with each model, the rule's 17 with Opus and 0 with Sonnet, and stock's 6 and 0; with Sonnet, no test left by stock or the rule caught the obvious merge. A refactor cost 1.64× with each model stock's cost, where the rule cost 1.20× and 1.31×.

### Real bugs

Each run got the project at the commit before the upstream fix, with its history and test suite, and a report that describes only the symptom. The fix's own new tests stayed hidden, and the project's whole suite had to pass.

<picture>
  <img src="../.github/assets/benchmark-real16-controls.svg" alt="12 real bugs: stock, a plain rule and Compound. Flask, click, attrs, packaging and marshmallow at the commit before each upstream fix, with the fix's own tests hidden; the report describes only the symptom. 2 runs per bug, arm and model; Compound Skills 0.16.0 ran just after stock and the rule, on the same tasks. Fixed the bug (upstream's tests pass): Opus stock 20 of 24, Opus plain rule 20 of 24, Opus Compound 20 of 24, Sonnet stock 19 of 24, Sonnet plain rule 18 of 24, Sonnet Compound 18 of 24. Left a test that fails on the buggy code: Opus stock 23 of 24, Opus plain rule 22 of 24, Opus Compound 23 of 24, Sonnet stock 22 of 24, Sonnet plain rule 21 of 24, Sonnet Compound 24 of 24. Reproduced the bug before changing code: Opus stock 2 of 24, Opus plain rule 24 of 24, Opus Compound 24 of 24, Sonnet stock 0 of 24, Sonnet plain rule 21 of 24, Sonnet Compound 24 of 24. Showed a new test failing before the fix: Opus stock 1 of 24, Opus plain rule 24 of 24, Opus Compound 24 of 24, Sonnet stock 0 of 24, Sonnet plain rule 18 of 24, Sonnet Compound 24 of 24. Ran the whole suite on the final code: Opus stock 18 of 24, Opus plain rule 23 of 24, Opus Compound 22 of 24, Sonnet stock 10 of 24, Sonnet plain rule 24 of 24, Sonnet Compound 24 of 24. Committed without an AI co-author line: Opus stock 0 of 24, Opus plain rule 0 of 24, Opus Compound 24 of 24, Sonnet stock 0 of 24, Sonnet plain rule 0 of 24, Sonnet Compound 24 of 24. Median cost of a fix: Opus stock 21¢, Opus plain rule 25¢, Opus Compound 20¢, Sonnet stock 7.0¢, Sonnet plain rule 7.8¢, Sonnet Compound 7.7¢. Cost against stock, bug by bug: Opus stock 1×, Opus plain rule 1.23×, Opus Compound 1.09×, Sonnet stock 1×, Sonnet plain rule 1.09×, Sonnet Compound 1.14×. The plain rule is a five-sentence user rule asking for the habits scored here. Stock and the rule kept Claude Code's default co-author line; its attribution setting can remove it without a plugin. The multiples compare each bug's runs with stock's, with the bugs weighted equally, so they can differ from the medians.">
</picture>

All three fixed about as many bugs: 20, 20 and 20 of 24 runs with Opus (stock, rule, Compound), and 19, 18 and 18 with Sonnet. Compound and the rule reproduced the bug and showed a new test failing before editing the source in nearly every run; stock did either in at most 2 runs per model, and showed a new test failing at any point in 14 Opus and 4 Sonnet runs, after its fix, with the fix set aside. With Sonnet, the rule skipped showing the failing test first in 6 runs where Compound did not (McNemar p = 0.03). Compound and the rule also ran the whole suite on the final code more often: 22 and 23 of 24 runs against stock's 18 with Opus, and 24 and 24 against 10 with Sonnet.

Bug by bug, the three fixed each bug equally often, except attrs with Sonnet. No run of the three fixed two bugs, because upstream's tests also cover a case the report did not mention: click's progress bar, which upstream also tests through `bar.update()` where the report describes a loop, and packaging's dependency groups, where upstream also requires a group included twice to be reported once. With Sonnet, every attrs fix by the rule and by Compound passed the project's suite but failed one of upstream's tests, which expects a class's `__replace__` to show its own name rather than `evolve`'s; one of stock's two runs passed it. The extra steps take time: a median fix took 66 seconds with Opus against stock's 41, and 36 against 24 with Sonnet.

<details>
<summary>The 12 bugs</summary>

- **flask**, fixed 2026-07-14: `app.run()` crashes on an IPv6 `SERVER_NAME` ([fix](https://github.com/pallets/flask/commit/7203feabf723)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).
- **flask**, fixed 2026-07-14: the test client loses the session with an IPv6 `base_url` ([fix](https://github.com/pallets/flask/commit/de8429ffda8c)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).
- **click**, fixed 2026-08-28: pickling a click option fails ([fix](https://github.com/pallets/click/commit/f58ca3e81424)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).
- **click**, fixed 2026-08-15: a progress bar stops at 14/20 ([fix](https://github.com/pallets/click/commit/f316d5cb3aa8)). Fixed in Opus 0 / 0 / 0; Sonnet 0 / 0 / 0 of 2 runs (stock / rule / Compound).
- **attrs**, fixed 2026-08-02: defining a class renames `attrs.evolve` ([fix](https://github.com/python-attrs/attrs/commit/f53fc5440d7f)). Fixed in Opus 2 / 2 / 2; Sonnet 1 / 0 / 0 of 2 runs (stock / rule / Compound).
- **packaging**, fixed 2026-08-08: `platforms=[]` still yields this machine's platform tags ([fix](https://github.com/pypa/packaging/commit/4e79787a31c9)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).
- **packaging**, fixed 2026-10-05: a later spelling of a `LicenseRef` overwrites the first ([fix](https://github.com/pypa/packaging/commit/2c87a33f6658)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).
- **packaging**, fixed 2026-10-07: a pylock path with mixed separators fails to load ([fix](https://github.com/pypa/packaging/commit/fa52d7237a74)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).
- **packaging**, fixed 2026-10-05: only the first malformed dependency group is reported ([fix](https://github.com/pypa/packaging/commit/959bb79c06cb)). Fixed in Opus 0 / 0 / 0; Sonnet 0 / 0 / 0 of 2 runs (stock / rule / Compound).
- **marshmallow**, fixed 2026-08-21: `TimeDelta` crashes on "nan" instead of reporting a validation error ([fix](https://github.com/marshmallow-code/marshmallow/commit/7dff08fcb7fb)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).
- **marshmallow**, fixed 2026-08-08: `validate.URL` rejects a link with a fragment but no path ([fix](https://github.com/marshmallow-code/marshmallow/commit/902f99c4151d)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).
- **marshmallow**, fixed 2026-10-18: `Pluck` ignores an empty `data_key` ([fix](https://github.com/marshmallow-code/marshmallow/commit/5761beab3985)). Fixed in Opus 2 / 2 / 2; Sonnet 2 / 2 / 2 of 2 runs (stock / rule / Compound).

The first four are Flask and click bugs fixed upstream between July and September 2026. The other eight were picked from fixes merged in August to October 2026 and frozen in commit c009f70 before any agent ran them. Before any run, setup's check found three problems, fixed in cd7da53: marshmallow puts the clock in some test ids, which setup now ignores; three reproduction patterns had an escaping mistake; and a werkzeug bug was dropped because its suite starts dev servers that hang in the sandbox.

</details>

### How 0.16.0 was chosen

This round first ran Compound as it was before 0.16.0, which loaded its skill, guides and map query for every engineering task, bug fixes included. On the real bugs it matched the rule's fixes and habits but cost 1.26× and 1.38× as much as the rule in the same groups; on the held-out refactors it got all 30 right. So 0.16.0 puts the bug-fix habits in Compound's always-on rule, in nearly the plain rule's words, adds "before you edit the source" and commits without AI co-author lines, and loads the skill only for refactors, new features, performance work, reviews and pull requests. In its runs, the skill loaded in 1 of 48 bug fixes and in none of 12 questions. A held-out review then showed the skill added nothing to reviews, so 0.16.0 as shipped loads it for refactors, new features, performance work and pull requests only ([below](#where-it-doesnt-help-reviews)).

We chose this design after seeing this round's results and then ran it on the same tasks, so its numbers here are a second measurement of a version tuned on the first, not a held-out test. Against the version before it, it fixed about as many bugs (20 and 18 of 24, against 20 and 19), reproduced the bug and showed the failing test first in every run, as before, ran the whole suite on the final code more often (22 and 24 of 24, against 18 and 19), and cost 0.71× and 0.75× as much per fix. On the held-out refactors it again did all 30 correctly and caught all 90 planted wrong refactors, at 1.07× with each model the earlier version's cost (95% intervals 1.01–1.13 with Opus and 0.98–1.17 with Sonnet).

### Second round, side by side

To remove the "ran just after" caveat, a second, smaller round started all four arms together in every group: stock, the plain rule, Compound before its redesign, and 0.16.0 as shipped, which no longer loads the skill for reviews. It ran in Claude Code 2.1.312, 1 run per real bug and 2 per held-out refactor, review and question, for each arm and model.

| Stock / plain rule / before the redesign / 0.16.0 | Claude Opus 5.5 | Claude Sonnet 5.5 |
| --- | --- | --- |
| Held-out refactors, 6 runs: done correctly | 4 / 4 / 6 / 6 | 4 / 2 / 5 / 6 |
| Held-out refactors: planted wrong refactors their tests catch, of 18 | 0 / 5 / 18 / 18 | 0 / 0 / 15 / 18 |
| Real bugs, 12 runs: fixed, upstream's hidden tests pass | 10 / 10 / 10 / 10 | 10 / 10 / 9 / 9 |
| Real bugs: reproduced and a new test shown failing before the fix | 0 / 11 / 12 / 12 | 0 / 11 / 12 / 11 |
| Real bugs: whole suite run on the final code | 9 / 12 / 12 / 12 | 3 / 12 / 9 / 11 |
| Real bugs: commits without an AI co-author line | 0 / 0 / 12 / 12 | 0 / 0 / 12 / 11 |
| Cost against stock: a real-bug fix | 1× / 1.17× / 1.44× / 1.16× | 1× / 1.26× / 1.50× / 1.20× |
| Cost against stock: a held-out refactor | 1× / 1.21× / 1.43× / 1.65× | 1× / 1.24× / 1.43× / 1.56× |
| Cost against stock: a Flask review | 1× / 1.57× / 1.91× / 1.61× | 1× / 2.28× / 3.30× / 2.21× |
| Cost against stock: a question about Django | 1× / 0.85× / 1.14× / 1.07× | 1× / 0.97× / 1.38× / 1.13× |

It agrees with the first round. Over both models, 0.16.0 did a held-out refactor correctly in 6 pairs where the rule did not and never the other way (McNemar p = 0.03), and in 4 pairs against stock's 0 (p = 0.13). All four arms fixed about as many bugs. 0.16.0 fixed one Sonnet bug fewer than stock and the rule: in that run, Claude Code refused its command to install Flask's dependencies into a new environment, so it could not run the code, and it stopped without editing, citing the rule's order to reproduce first, after naming the cause and a fix. It showed a new test failing before the fix in 23 of 24 pairs where stock did not (p < 0.001), and in 2 where the rule did not against 1 the other way. A fix cost 0.80× with each model what it cost before the redesign, and about what the rule costs (0.99× and 0.95×). The skill loaded in 1 of 0.16.0's 24 bug-fix runs, in none of its 8 review and question runs, and in all 12 of its refactor runs. Its commit count is out of 11 with Sonnet because of the run that stopped.

With one run per bug, the real-bug cost multiples have no meaningful interval; the refactor multiples rest on 6 pairs per model and the review and question multiples on 2.

### Does the map query pay for itself?

<picture>
  <img src="../.github/assets/benchmark-map.svg" alt="Does the map query pay for itself? Compound before its 0.16.0 redesign, which loaded the skill for every task, against the same text with the map query removed from its startup and its rule, on the 12 real bugs and 3 held-out refactors, side by side. Real bugs fixed: Opus Compound 20 of 24, Opus Compound without the map query 20 of 24, Sonnet Compound 19 of 24, Sonnet Compound without the map query 18 of 24. Refactors done correctly: Opus Compound 15 of 15, Opus Compound without the map query 15 of 15, Sonnet Compound 15 of 15, Sonnet Compound without the map query 15 of 15. Real bugs reproduced first: Opus Compound 24 of 24, Opus Compound without the map query 24 of 24, Sonnet Compound 24 of 24, Sonnet Compound without the map query 24 of 24. New test failing before the fix: Opus Compound 24 of 24, Opus Compound without the map query 24 of 24, Sonnet Compound 24 of 24, Sonnet Compound without the map query 24 of 24. Median cost of a real fix: Opus Compound 28¢, Opus Compound without the map query 27¢, Sonnet Compound 10¢, Sonnet Compound without the map query 11¢. Median cost of a refactor: Opus Compound 24¢, Opus Compound without the map query 21¢, Sonnet Compound 9.6¢, Sonnet Compound without the map query 9.8¢. The decision rule was fixed before the run; see the text.">
</picture>

Compound's startup map query was measured on its own, before the redesign, with the rule for keeping it fixed before the run ([bench/README.md](README.md#arms)): drop the query only if, without it, the agent fixed no fewer bugs and did no fewer refactors correctly beyond noise, kept the habits within two runs, and cost less, with the paired cost ratio's 95% upper bound at or below 1.0. Without it, one bug that Compound fixed went unfixed and nothing went the other way; the habits were identical (all 48 real-bug runs of each reproduced the bug and showed the failing test first); and runs cost 0.98× as much (95% interval 0.95–1.004, 78 pairs). The upper bound was above 1.0, so the query stays. Its effect on these outcomes is too small to measure in either direction; the map's case rests on finding files ([below](#map-file-ranking)) and on the viewer.

### Isn't this just a rule in CLAUDE.md?

For bug fixes, mostly yes. One arm had no plugin and only this always-on rule, added as a user rule in `~/.claude/rules/`, where Compound's own rule goes:

> Before fixing a reported bug, reproduce it by running the code. Add a regression test and show that it fails on the unfixed code. Run the full test suite after your last change. Before a refactor, record current behaviour and compare afterwards. In your final message, list what you ran and what you did not verify.

On the 12 real bugs, the rule fixed as many bugs as Compound (20 and 18 of 24 runs with Opus and Sonnet, against 20 and 18), reproduced the bug first in 24 and 21, against Compound's 24 and 24, and showed a new test failing before the fix in 24 and 18, against 24 and 24. Compound cost 0.89× the rule's cost with Opus and 1.04× with Sonnet. Since 0.16.0, Compound's always-on rule asks for the same habits in nearly the same words and adds "before you edit the source"; with Sonnet, it showed the failing test first in 6 runs where the rule did not (McNemar p = 0.03). If those habits are all you want, copy the rule.

For refactors, no. On the held-out refactors the rule did 10 and 9 of 15 correctly, against Compound's 15 and 15, and its tests caught 17 and 0 of 45 planted wrong refactors, against 45 and 45. In the 0.14.0 round on the controlled refactor, the rule broke tax rounding in all 5 Sonnet runs, where Compound broke none.

Commit lines are the other difference: the rule did not ask about them, and Claude Code's own `attribution` setting (`"commit": ""` in `settings.json`) removes the co-author line without a plugin.

### Cost and time

To audit existing runs without model usage, run `python3 bench/bench.py cost-audit --label <saved-label>`. It includes recorded spend from unsuccessful, invalid and superseded attempts, and reports accepted and unresolved outcomes separately by task, model and arm. Spend per accepted result includes failed attempts; missing cost records make it unknown. These are first-attempt batches, not measured correction sessions or project-lifetime savings.

Cents and seconds are medians per run at API list prices, as Claude Code reports them. Multiples are geometric means of paired cost ratios with the tasks weighted equally, with 95% intervals. Arms that started together are paired by group; Compound 0.16.0, which ran just after the others on the real bugs, refactors and review, is paired with them by task, model and repetition.

| Compound 0.16.0 against stock | Claude Opus 5.5 | Claude Sonnet 5.5 |
| --- | --- | --- |
| A real-bug fix, 24 pairs | 1.09× (1.03–1.16) | 1.14× (1.05–1.24) |
| A held-out refactor, 15 pairs | 1.64× (1.52–1.77) | 1.64× (1.55–1.75) |
| A question about Django, 3 pairs | 1.05× (0.79–1.32) | 1.17× (0.88–1.34) |
| A Flask review, 3 pairs, with the skill loaded for reviews | 1.67× (1.23–2.32) | 2.91× (1.95–5.34) |
| A Flask review as shipped, 2 pairs, [second round](#second-round-side-by-side) | 1.61× (1.45–1.79) | 2.21× (1.50–3.26) |

Medians and multiples can disagree: with Opus, Compound's median fix cost 20.2¢ against stock's 20.9¢, but it cost more than stock on 8 of the 12 bugs. In the same groups as stock, the plain rule cost 1.23× and 1.09× stock per fix and 1.20× and 1.31× per refactor.

The extra steps take time: a median fix took 66 seconds with Opus against stock's 41, and 36 against 24 with Sonnet; a median refactor took 54 against 39, and 33 against 21.

The benchmarked always-on rule and the plugin's skill list added about 510 tokens to every request, measured on a plain question; the plain rule adds about 210. Questions don't load the skill, and none of Compound's 12 question runs did, so a question costs about what it does on stock. Reviews no longer load it either, but still cost more than stock for the same findings, about what the plain rule costs ([below](#where-it-doesnt-help-reviews)).

### Where it doesn't help: reviews

No measured gain. A blind judge graded every Flask review against a fixed key: every review in every arm, with both models, found all three planted defects, so this review was too easy to show a gain or a loss. With the skill loaded, Compound's reviews cost 1.67× stock with Opus and 2.91× with Sonnet, over 3 pairs each, and the judge counted 2 incorrect statements in Compound's six reviews against 2 in stock's. Every arm could read the code but not run it, and no review changed the repository.

So 0.16.0 stopped loading the skill for reviews, by a rule fixed in [bench/README.md](README.md#arms) before the test ran: on a held-out review of a commit whose three helper merges each change one caller, 0.16.0 without the skill for reviews found as much as with it (the same score in all 10 pairs) and cost 0.75× as much (95% interval 0.72–0.78). In the [second round](#second-round-side-by-side), 0.16.0 as shipped found all three Flask defects in all 4 of its reviews and cost 1.61× and 2.21× stock, about what the plain rule costs; the rule missed one defect in one Sonnet review.

The question about Django, which no longer loads the skill, was answered as well with Compound as without: with Opus, every answer in every arm covered all 11 key points; with Sonnet, answers covered a median of 9 without Compound and 9 with it.

In the 0.14.0 rounds, which loaded the skill for questions too, the judge graded every Flask review and Django answer in two rounds of 5 runs per arm and model. Every review found all three planted defects in both arms (20 of 20 each). Opus covered all 11 Django key points in 9 of 10 answers without Compound and 7 of 10 with it; Sonnet's answers covered a median of 9 either way. The judge counted 13 incorrect statements without Compound and 9 with it for Opus, and 12 and 15 for Sonnet.

<picture>
  <img src="../.github/assets/benchmark-answers.svg" alt="Reviews and questions: no measured gain. A blind judge, Claude Opus 5.5, graded every Flask review and Django answer against a fixed key: 10 per task, arm and model, from two runs of Compound Skills 0.14.0 on the same day. Found all 3 defects: Opus stock 10 of 10, Opus with Compound 10 of 10, Sonnet stock 10 of 10, Sonnet with Compound 10 of 10. Incorrect statements in the 10 reviews: Opus stock 6, Opus with Compound 3, Sonnet stock 5, Sonnet with Compound 5. Median cost of a review: Opus stock 11¢, Opus with Compound 20¢, Sonnet stock 2.6¢, Sonnet with Compound 7.3¢. Covered all 11 key points: Opus stock 9 of 10, Opus with Compound 7 of 10, Sonnet stock 0 of 10, Sonnet with Compound 0 of 10. Median key points covered: Opus stock 11 of 11, Opus with Compound 11 of 11, Sonnet stock 9 of 11, Sonnet with Compound 9 of 11. Incorrect statements in the 10 answers: Opus stock 7, Opus with Compound 6, Sonnet stock 7, Sonnet with Compound 10. Median cost of an answer: Opus stock 15¢, Opus with Compound 19¢, Sonnet stock 3.8¢, Sonnet with Compound 6.8¢. Every arm could read the code but not run it. The first run took three votes per answer and the second one; 40 votes in the first run that called the commit id wrong, because the judge's copy showed an old id, are not counted.">
</picture>

### Earlier rounds with 0.14.0

These rounds measured Compound 0.14.0, which loaded its skill for every engineering task, bug fixes included. The [0.15.0 README](https://github.com/tobenwarrior/compound-skills/blob/18e647f/README.md#benchmark) reports them in full.

<details>
<summary>Six controlled tasks, the plain rule, the same 12 real bugs, and two other plugins</summary>

#### Six controlled tasks and the plain rule

A small billing library written for this benchmark, whose own tests miss its three bugs, and a refactor whose obvious version changes tax rounding; a Flask commit with three planted defects to review; a question about Django; and a plain question. Stock against Compound 0.14.0 in two rounds of 5 runs per task and model, the second also with the plain rule.

<picture>
  <img src="../.github/assets/benchmark-rule.svg" alt="Isn't this just a rule in CLAUDE.md? The same six tasks with no plugin, with only a five-sentence rule asking for the habits, and with Compound Skills 0.14.0: 5 runs per arm, task and model, side by side. Fixed the bug (hidden tests pass): Opus stock 15 of 15, Opus plain rule 15 of 15, Opus Compound 15 of 15, Sonnet stock 15 of 15, Sonnet plain rule 15 of 15, Sonnet Compound 15 of 15. Planted regressions the tests left behind catch: Opus stock 41 of 55, Opus plain rule 46 of 55, Opus Compound 47 of 55, Sonnet stock 28 of 55, Sonnet plain rule 40 of 55, Sonnet Compound 41 of 55. Refactor kept tax rounding and removed both helpers: Opus stock 3 of 5, Opus plain rule 5 of 5, Opus Compound 5 of 5, Sonnet stock 0 of 5, Sonnet plain rule 0 of 5, Sonnet Compound 5 of 5. Ran the whole suite on the final code: Opus stock 15 of 15, Opus plain rule 15 of 15, Opus Compound 15 of 15, Sonnet stock 15 of 15, Sonnet plain rule 14 of 15, Sonnet Compound 15 of 15. Reproduced the bug before changing code: Opus stock 0 of 15, Opus plain rule 15 of 15, Opus Compound 15 of 15, Sonnet stock 0 of 15, Sonnet plain rule 15 of 15, Sonnet Compound 15 of 15. Showed a new test failing before the fix: Opus stock 0 of 15, Opus plain rule 15 of 15, Opus Compound 15 of 15, Sonnet stock 0 of 15, Sonnet plain rule 15 of 15, Sonnet Compound 15 of 15. Committed without an AI co-author line: Opus stock 0 of 15, Opus plain rule 0 of 15, Opus Compound 15 of 15, Sonnet stock 0 of 15, Sonnet plain rule 0 of 15, Sonnet Compound 15 of 15. List-price cost vs stock, six tasks weighted equally: Opus stock 1.00×, Opus plain rule 1.35×, Opus Compound 1.54×, Sonnet stock 1.00×, Sonnet plain rule 1.41×, Sonnet Compound 1.78×. Planted regressions: 55 per arm and model over the three bugs and the refactor. Cost multiples come from the 22 (Opus) and 24 (Sonnet) task groups where all three arms ran side by side. The tasks were written for this benchmark and Compound was partly tuned on them.">
</picture>

On these tasks the rule reproduced every bug first and showed a failing test before the fix, as Compound 0.14.0 did. In the 22 of 30 Opus task runs and 24 of 30 Sonnet ones where stock, the rule and Compound started together, the rule cost 1.35× and 1.41× stock and Compound 1.54× and 1.78×. With Sonnet, the rule broke tax rounding in all 5 refactor runs, where Compound broke none; that refactor's guide had been revised after earlier runs of the same task, which is why the held-out refactors were written. We added the rule arm after the round began, so 10 of its 35 task runs with Opus and 7 with Sonnet (seven tasks, five runs each, counting the plain question) ran in a second pass, without stock and Compound beside them.

#### The same 12 real bugs against stock

With 0.14.0, the first four bugs ran 3 times per arm and model and the other eight twice. Compound reproduced the bug first in 28 of 28 Opus runs and 26 of 28 Sonnet runs, against 5 and 0 without it, and showed a new test failing before the fix in 28 and 26, against none without. Upstream's tests passed about equally often without and with Compound (23 and 23 of 28 runs with Opus; 23 and 21 of 28 runs with Sonnet).

#### Compared with other plugins

Every's Compound Engineering 3.34.0 (commit 3449230, 36 skills) and pstack 0.15.36 (commit 4dd1d05, its Claude Code copy, 58 skills), installed as their READMEs say, on the three bugs and the refactor. These are Compound's own habit measures, on tasks Compound was partly tuned on, run by Compound's author, and the others' default co-author lines count against them: read this as how each plugin behaves on this checklist, not as a ranking. With plain prompts, their skills did not run in any task and the results looked like stock Claude Code's, at a little more cost. Started with the command each one tells you to type, both reproduced bugs first (Every's in 12 of 12 runs, pstack in 9 of 12), at 2–11× Compound's cost per Opus bug fix and 1.5–2.8× per Sonnet fix in the same round, and both kept AI co-author lines.

<picture>
  <img src="../.github/assets/benchmark-compared.svg" alt="Compared with other plugins. Every's Compound Engineering 3.34.0 and pstack 0.15.36, installed as their READMEs say, on the three bugs and the refactor; Claude Opus 5.5 and Sonnet 5.5 together. With plain prompts, as everyone else ran; then started with the command each one tells you to type. Fixed the bug (hidden tests pass): stock 18 of 18, Every's Compound Engineering with plain prompts 18 of 18, pstack with plain prompts 18 of 18, Every's Compound Engineering with its commands 12 of 12, pstack with its command 12 of 12, Compound 18 of 18. Planted regressions the tests left behind catch: stock 45 of 66, Every's Compound Engineering with plain prompts 38 of 66, pstack with plain prompts 42 of 66, Every's Compound Engineering with its commands 30 of 44, pstack with its command 30 of 44, Compound 52 of 66. Refactor kept tax rounding and removed both helpers: stock 3 of 6, Every's Compound Engineering with plain prompts 1 of 6, pstack with plain prompts 1 of 6, Every's Compound Engineering with its commands 0 of 4, pstack with its command 2 of 4, Compound 6 of 6. Reproduced the bug before changing code: stock 0 of 18, Every's Compound Engineering with plain prompts 0 of 18, pstack with plain prompts 0 of 18, Every's Compound Engineering with its commands 12 of 12, pstack with its command 9 of 12, Compound 18 of 18. Showed a new test failing before the fix: stock 0 of 18, Every's Compound Engineering with plain prompts 0 of 18, pstack with plain prompts 0 of 18, Every's Compound Engineering with its commands 12 of 12, pstack with its command 9 of 12, Compound 18 of 18. Committed without an AI co-author line: stock 0 of 18, Every's Compound Engineering with plain prompts 0 of 18, pstack with plain prompts 0 of 18, Every's Compound Engineering with its commands 0 of 12, pstack with its command 0 of 12, Compound 18 of 18. Median cost of a bug fix, Opus 5.5: stock 10¢, Every's Compound Engineering with plain prompts 11¢, pstack with plain prompts 12¢, Every's Compound Engineering with its commands 183¢, pstack with its command 32¢, Compound 17¢. Median cost of a bug fix, Sonnet 5.5: stock 3.5¢, Every's Compound Engineering with plain prompts 4.4¢, pstack with plain prompts 4.0¢, Every's Compound Engineering with its commands 17¢, pstack with its command 9.5¢, Compound 5.6¢. Stock and Compound ran with plain prompts. Plain prompts: 3 runs per task and model. Commands (/ce-debug and /ce-work for Every's CE, /poteto-mode for pstack): 2 runs, in a separate run with its own stock and Compound arms, where a bug fix's median cost was 10¢ stock and 16¢ with Compound on Opus, 4.2¢ and 6.2¢ on Sonnet. The tasks were written for this benchmark and Compound was partly tuned on them.">
</picture>

<details>
<summary>How each plugin ran</summary>

- **Every's Compound Engineering:** the repository's Claude Code plugin, unchanged. We skipped its optional `/ce-setup`, which writes a config file into the project. Commands: `/compound-engineering:ce-debug` for the bugs and `/compound-engineering:ce-work` for the refactor, as its skill descriptions direct. Its code review sends some reviewer agents to Sonnet even in Opus sessions; that cost is counted.
- **pstack:** the generated Claude Code copy in `cursor/plugins/harness/pstack/claude-code`. Its setup, `/setup-pstack`, writes a rule mapping roles to models; we wrote that rule with every role on the session's model, one of the choices it offers, so each run stayed on the model under test. Command: `/pstack:poteto-mode`, which its README says to use for anything that needs rigor.
- **Anthropic:** Claude Code's bundled debug, verify and code-review skills were available in every arm, stock included; Anthropic's public skills repository (checked at ca45fc4) holds document, design and API skills, none for debugging, testing or review.
- **Scope:** single bug fixes and a refactor on tasks Compound was partly tuned on; not their planning loops or parallel orchestration. The plain-prompt and command passes were separate rounds, each with its own stock and Compound arms.

</details>

#### Individual runs

<details>
<summary>One bug fix side by side, and the 30 Opus bug-fix runs step by step</summary>

An example chosen before the runs: repetition 1 of the December bug on Claude Opus 5.5, in the first 0.14.0 round. Both runs fixed the bug, added a test, noticed that plain EOM terms were wrong too and committed. The highlighted sentences appear only in the report with Compound.

<picture>
  <img src="../.github/assets/benchmark-reports.svg" alt="The final reports from rep 1 of the December bug on Claude Opus 5.5. Both fixed the bug, added a test that checks the reported example, noticed that plain EOM terms were wrong too and committed. Only the report with Compound says the new test failed before the fix, with 2023-12-31 != 2024-12-31, that it also called due_date with the reported example, that it found no other code doing the same month arithmetic, and that the commit has no Claude co-author trailer.">
</picture>

Only the report with Compound says “Before the fix it failed (`2023-12-31 != 2024-12-31`)” and that the commit “has no Claude co-author trailer”. The run without Compound also searched for the same month arithmetic and checked the reported example, but ran its tests only once, after the fix.

Each row below is one run, lined up on its first source edit; marks to the left happened before it.

<picture>
  <img src="../.github/assets/benchmark-steps.svg" alt="The 30 Claude Opus 5.5 runs on the three bug reports, without Compound and with 0.14.0, each as a row of steps lined up on its first source edit. Without Compound, 14 of 15 runs started by editing the source. With Compound, all 15 showed a failing test before their first source edit.">
</picture>

Without Compound, 14 of 15 runs started by editing the source; the other ran Python first, but only tried pytest, which is not installed for this library. With Compound, all 15 showed a failing test before their first source edit.

</details>

</details>

### How we measured, and check our numbers

Claude Code 2.1.316 in headless mode, Claude Opus 5.5 and Claude Sonnet 5.5 at default effort, on 31 October and 1 November 2026. The arms of a group started together in isolated sandboxes with identical paths, one CPU each, in rotating order. Compound 0.16.0 ran just after the other arms of its round, on the same tasks, Claude Code version and models. In the second round, in Claude Code 2.1.312, all four arms started together. Prompts never mention a plugin, except the commands the other plugins ask their users to type. Write tasks may run code and commit; read tasks may only read; web access and installs are blocked in every arm.

<details>
<summary>Method: arms, tasks, scoring, detectors and corrections</summary>

- **Arms.** Stock was Claude Code as installed, with its bundled skills. Compound ran as a plugin plus the always-on rule its `setup-global` writes. The rule arm had no plugin, only the rule quoted above as a user rule. The no-map arm was Compound before the redesign with the map query removed from its startup and its rule (`+variant:nomap` in [bench/](README.md#arms)). The other plugins are described above.
- **Tasks.** The 12 real bugs and 3 held-out refactors above; a Flask commit with three planted defects to review; a question about Django's 7,085 files; a plain Python question; and, in the 0.14.0 rounds, a small billing library whose own tests miss its three bugs and a refactor whose obvious version changes tax rounding. No prompt asks for tests or mentions a plugin or the map; one real bug report says the user's own test fails.
- **Scoring.** Hidden tests; planted wrong fixes and refactors run against the tests each agent left; upstream's new tests and the whole suite on the real bugs; a logging wrapper around `python` that records what ran on which version of the code; and a blind judge (Claude Opus 5.5, also one of the agents under test) that must quote the answer for each point it awards, with three votes per answer, except one vote in the second 0.14.0 round.
- **Detectors.** The habit detectors were checked by two arm-blind AI labellers in our first benchmark, agreeing on 45 to 47 of 48 Opus traces and on all 48 Sonnet traces. A new test counts as shown failing before the fix only if it failed before the first source edit; stock often showed one failing only after its fix, with the fix set aside, which does not count.
- **Statistics.** Cost multiples are geometric means of paired ratios with the tasks weighted equally, with bootstrap 95% intervals; outcome differences use exact McNemar tests on the pairs that disagree.
- **Runs.** In the first 0.16.0 round, 2 runs per real bug, 5 per held-out refactor and 3 per review and question, for each arm and model; in the second, 1 per real bug and 2 per held-out refactor, review and question; in the 0.14.0 rounds, 10 per controlled task. None of the 1,334 runs this README cites was invalid.
- **Correction in the second round.** The check that a control arm never mentions Compound flagged two Opus control answers to the Django question, because Claude Code's own permission message spoke of a "compound command". The check now ignores that phrase, and both runs count.
- **Corrections in the 0.16.0 round.** The judge checks that each quote it gives is in the answer, and it rejected quotes that ran across two bullet points of a list. Two Sonnet reviews that name all three defects scored 0 and 1 of 3 this way: one by Compound before the redesign and one by 0.16.0. The check now ignores list markup, and we regraded every judged answer of every round from the stored votes; that changed those two scores to 3 of 3, and one review by an arm this README does not cite. A batch of held-out refactor runs was stopped by a time limit outside the benchmark; groups cut off mid-run had written no records and ran again in full.
- **Corrections in the 0.14.0 rounds.** In the first round, the judge's copy of the Flask commit showed an old commit id, so 40 votes called the id wrong; `bench.py report` leaves those complaints out, and the harness is fixed. One Sonnet group lost its log of Python calls when another benchmark started beside it; we gave every run its own logger and ran the group again. The rule arm's first groups ran in a second pass, after we added the arm. After the runs, we found the reproduction detector missed the short failure output of `pytest -q` (`1 failed, 50 passed`, `FAILED tests/…`); rescoring every arm's runs with the wider pattern raised Compound's real-bug reproductions from 24 to 28 with Opus and from 20 to 26 with Sonnet, and changed no stock run. We read the matching output of all 10 changed runs: each was a new test, named for the reported bug, failing before the first source edit.

</details>

You can rerun the headline yourself. With the [requirements](README.md#requirements) in place (Linux with user namespaces, the `claude` CLI and a sign-in), this runs every real bug and held-out refactor once per arm with Sonnet, stock against this checkout, for about $2 at list prices:

```bash
python3 bench/bench.py setup
```

```bash
python3 bench/bench.py run --label check --arms without,with --tasks real,heldout --models sonnet
```

```bash
python3 bench/bench.py report --label check
```


## Map cache timings

Of seven open-source repositories (Gin, Click, ripgrep, Flask, Hono, Vue core and Django), six build in under 2.5 seconds the first time and in under 0.3 seconds when nothing changed; Django, with 7,085 files, takes 8.20 and 2.29 seconds. Once the local service is running, an agent's later queries take about 0.4 seconds, and 0.97 on Django.

<picture>
  <img src="../.github/assets/map-speed.svg" alt="How fast the code map is on seven repositories from 130 to 7,085 files. First builds take 0.41 to 2.48 seconds, and 8.20 on Django; rebuilds when nothing changed take 0.05 to 0.27 seconds, and 2.29 on Django; an agent's later queries take 0.38 to 0.43 seconds, and 0.97 on Django.">
</picture>

Median of 5 runs on 4 cores with Python 3.13.17, timed on 0.13.0; later versions have not been retimed. To rerun: `python3 bench/bench.py map-speed --repos flask,click,hono,django,vue-core,gin,ripgrep`.


## Map summary density

![Offline comparison of Compound’s focused summaries before and after 0.16.1: median complete file entries rise from 3 to 4 inside the same 2,500-character limit. Full outlines total 97,350 versus 76,283 UTF-8 bytes across 15 paired queries on five pinned repositories.](../.github/assets/map-context.svg)

0.16.1 keeps matching symbols and trims unrelated ones: **4 complete file entries instead of 3 at the median**, within the same 2,500-character limit. This offline comparison uses identical map metadata for 15 fixed queries across Flask, Click, attrs, packaging and marshmallow; ranking and JSON stay unchanged. The full, uncapped outlines are 21.6% smaller. This measures information density within Compound; lower model bills and task outcomes have not been remeasured. [Method and reproduction](README.md#offline-summary-comparison).


## Map file ranking

On average, 74% of the source files a commit changed were in the map's top 4, against 67% for a word search that skips common words and lists tests last, 51% for a plain word count and 4% at random. That is over 240 real commits held out from tuning, 60 each from Flask, Click, Hono and Gin, each queried with its title. It was ahead of the plain count on 73 commits to 11; on Click the gap was small enough to be noise.

<picture>
  <img src="../.github/assets/map-retrieval-controls.svg" alt="Share of each commit's changed source files in the map's top 4, on 60 held-out commits each from Flask, Click, Hono and Gin: the current map 74% on average, against 48% for the map in 0.12.1, 51% for word-count search and 4% at random.">
</picture>

<details>
<summary>How the ranking works and how we tested it</summary>

It was clearly ahead on Flask (60% against 35%, ahead on 21 commits to the search's 4), Hono (75% against 34%, 27 commits to 0) and Gin (81% against 63%, 15 commits to 2). On Click it was slightly ahead (81% against 73%, 10 commits to 5), a gap small enough to be noise.

The map weighs the query's rarer words in file paths, symbols and the text of its 50 leading candidates, favors larger and widely imported code files, and lists tests lower unless the query mentions tests. We tuned it on the 60 most recent such commits of Flask, Click and Hono, and held out older ones; Gin, a Go project, was used only for this check, which ran at 0.13.0 with a script outside bench/. `python3 bench/bench.py map-retrieval` scores the same way on the most recent commits of Flask, Click and Hono, the ones the ranking was tuned on, so it compares versions rather than testing on held-out commits. Part of the gain comes from listing tests lower, since only non-test files were scored: a word search that also skips common words and lists tests last put 67% in its top 4, about level with the map on Click and Gin. Each commit's parent was copied into a fresh repository without history, so the map's co-change hints played no part. The newer ranking made later queries 0.03 to 0.09 seconds slower than in 0.12.1 and a coding task's first query 0.04 to 1.19 seconds slower.

<picture>
  <img src="../.github/assets/map-retrieval-detail.svg" alt="Share of each commit's changed source files in the map's top 4 and top 12 for Flask, Click, Hono and Gin, against the map in 0.12.1, word-count search and random order. The current map found 60% and 96% on Flask, 81% and 95% on Click, 75% and 90% on Hono, and 81% and 92% on Gin.">
</picture>

</details>
