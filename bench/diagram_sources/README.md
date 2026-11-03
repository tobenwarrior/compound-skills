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
