# README diagram sources

Run from the repository root:

```sh
python3 -B bench/render_readme_diagrams.py
python3 -B bench/render_readme_diagrams.py --check
```

The generator uses only Python's standard library. It writes every README SVG into `.github/assets/`, with shared colors from `theme.json`, Inter/system typography, cream backgrounds, rounded cards and green accents from the supplied hey.trading theme. It makes no model or network calls. `--check` detects output that differs from these sources; `--output <directory>` renders a separate preview.

`pilot.json` contains sanitized saved measurements from the 2 November 2026 DeepSeek V4.1 Flash pilot on Compound 0.16.7. Bar lengths and percentage changes are calculated from these values. The generator rejects task totals that disagree with arm totals or all-attempt spend. Allowance, API list-price usage and cash charges remain distinct; these are provider-reported amounts, not token-price estimates. Four valid runs on two development tasks are too few to establish general or long-term savings. Raw transcripts and request records remain local under ignored `bench/results/`.

`scenes/` holds the historical charts as declarative vector elements: text, geometry and measurement descriptions transcribed losslessly from the previous README SVGs. The generator preserves their content, bar geometry and timelines, replaces their outer frames, and applies shared typography without overriding individual text colors. Each scene names its measurement scope; cache-state comparisons and within-Compound ablations are not comparisons against stock. Edit a scene when correcting a historical chart; do not edit the generated SVG.

`screenshots/` contains text-encoded copies of the five original Flask viewer screenshots extracted from the two previous map SVGs. The generator embeds these real screenshots inside the shared frame; it does not synthesize a new viewer or alter the captured pixels. No font files or external runtime dependencies are required.

`workflow.json` records the completed two-repository, six-change DeepSeek workflow, including failed implementations, semantic repairs and transport resumptions. Every task has an accepted final result. Per-attempt costs sum into stage, sequence and mode totals. Exact totals stay `null` when any response has unreported usage; the graphics mark known minimums with `≥`. The invoicekit bug-fix sequence is fully priced and supports its scoped 15.5% reduction; the complete workflow has missing usage in both modes and supports no exact overall savings claim. The experiment audit also retains invalid setup spend separately.

`comparisons.json` selects the without/with arms from the historical measurements for the main refactor, bug-fix and file-discovery charts. Bar lengths are computed from these values. Source-description hashes require an explicit recheck when the historical scene changes. The original charts, including all controls, render as `*-controls.svg` for the historical methodology. Two-arm presentation does not discard losses or relabel map-cache/ablation measurements as stock comparisons.

`map_query_profile.json` retains the keyless, same-input ranking profile for the directory-open optimization: source hashes, pinned repository revisions, result hashes, open counts and all timing summaries. Timing was mixed on the shared host; only the reduction in opens and ranking equivalence are established. It is not a model-cost result and is not rendered as a without/with task chart.

`work_audit.json` counts saved Y Harness / DeepSeek V4.1 Flash events and records source hashes, edit prerequisite refusals and annotated extra-work causes. `navigation_replay.json` checks the changed map presentation on the saved query and pinned fixture, preserving the entire ranked index. Neither artifact projects new model behavior or subtracts hypothetical costs.

`work_review_v0169.json` annotates exact saved request steps and their recorded usage from `comparison_v0169.json`. It keeps useful mixed-step work and functional corrections distinct from optional exploration/polish. Costs are retained unchanged; the annotations do not establish future savings.

`comparison_dispatch_v01615.json` records the fresh two-change Dispatchkit sequence. It includes every attempt, exact provider-reported charges, input-cache counts and the independent cumulative grades. The generated cost chart recomputes the verdict from every attempt and checks the saved stage and arm totals. It requires complete usage, both tasks accepted in both modes and lower overall cost with Compound. This was one sequence per mode on a synthetic repository.

`comparison_flask_v01645.json` records the upstream Flask sequence. It includes all four attempts, provider-reported usage, the frozen inputs and the cumulative grades. The generator applies the same checks and uses the two IPv6 tasks as labels.

`comparison_codex_flask_luna.json` records the same two prompts in clean Git checkouts on GPT-6 Luna. It includes all four attempts, the native Codex token counts and the cumulative grades. The chart verifies both tasks passed and reconciles the per-attempt request counts.
