# Compound Skills

**Build cleaner software. Keep your agent's context focused.**

A compact engineering plugin for **Codex, Cursor, and Claude Code**. Get practical guidance for architecture, implementation, debugging, refactoring, and review—and a process for improving that guidance as you discover better skills.

After activation, give normal engineering requests. The setup shortcuts manage project and global defaults; `compound` also supports chat activation and other modes.

- **Clearer architecture:** design around callers, explicit ownership, meaningful states, and interfaces that hide complexity.
- **Automatic code maps:** orient agent work with compact structural context, then explore an interactive repository graph with source previews, Git changes, impact analysis, and import tracing.
- **Evidence behind changes:** reproduce failures, preserve behavior during refactoring, and verify observable results. A small headless model comparison is documented below; it is not a general ranking.
- **Consistent commits and PRs:** concrete titles, concise explanations, truthful validation, and no AI co-author credits across all three apps.
- **Set up once:** make Compound the default across all your projects in Codex, Cursor, and Claude Code, or limit activation to one project or chat.
- **Existing-project cleanup:** run the `setup` shortcut to reassess architecture, dependencies, scripts, docs, tests, and Git conventions—even after prior setup. Apply verified cleanup and report larger decisions. New projects retain automatic first-use onboarding.
- **Focused context:** load the relevant reference when needed; keep a shared source across all three hosts.
- **Knowledge that compounds:** retain useful ideas, replace weaker guidance, and delete superseded material as the toolkit evolves.

## Install

Install once in each app you use. Choose **User** scope so the plugin is available across your projects.

### Codex

Run these in a terminal:

```sh
codex plugin marketplace add tobenwarrior/compound-skills
codex plugin add compound-skills@compound-skills
```

Optional command: `$compound`. Choose an activation mode below.

### Claude Code

Run these inside a Claude Code chat, choosing **User** scope if prompted:

```text
/plugin marketplace add tobenwarrior/compound-skills
/plugin install compound-skills@compound-skills
```

Optional command: `/compound-skills:compound`. Choose an activation mode below.

### Cursor

1. Open **Customize → Plugins → Add → From GitHub Repository**.
2. Enter `https://github.com/tobenwarrior/compound-skills`, choose **User** scope, then **Import**.
3. Click **Add** or **Install** beside `compound-skills` in the imported marketplace.

Optional command: `/compound`. See [Cursor's plugin documentation](https://cursor.com/docs/plugins).

After installation, start a **new chat** in each app before using the commands. Claude Code can also load the install with `/reload-plugins`. If a plugin is missing after installation, reopen the app and check its plugin manager. After updating from 0.6.0 or earlier, repeat global setup once to refresh saved routing.

## Enable once, then work normally

After the user-scope installs above, run global setup **once from any one app**. Choose one command from the first row; you do not need to run it in all three:

| Action | Codex | Cursor | Claude Code |
| --- | --- | --- | --- |
| All projects on this machine | `$setup-global` | `/setup-global` | `/compound-skills:setup-global` |
| Check global defaults | `$status-global` | `/status-global` | `/compound-skills:status-global` |
| Remove global defaults | `$compound disable global` | `/compound disable global` | `/compound-skills:compound disable global` |

The three shortcuts `setup`, `setup-global`, and `status-global` appear separately in autocomplete. `disable global` remains an argument after `compound`. Existing `compound setup`, `compound setup global`, and `compound status global` forms still work.

Global setup saves the Codex and Claude defaults together and adds only Compound’s local state directory to the native Codex/Cursor write-path lists so first-use completion can be remembered. Cursor includes its default in the plugin: install at user scope and keep the `compound-default` rule set to **Always** in Customize → Rules. New chats across your projects use Compound without repeating a command or adding files to every repository. Only a small routing rule stays active; detailed guidance loads when relevant.

Before the first write-authorized engineering task in a repository, Compound runs a bounded onboarding pass: inspect the structure and existing checks, audit hygiene, apply high-confidence cleanup, and verify changes. It preserves existing uncommitted work and leaves larger architecture changes for review. Read-only requests remain read-only. Completion is remembered locally across all three apps, so it does not repeat in every chat or add a marker to Git. See [first-use behavior](skills/compound/references/onboarding.md).

| App | Global rule |
| --- | --- |
| Codex | `~/.codex/AGENTS.md`, plus an existing nonempty `AGENTS.override.md` |
| Cursor | Bundled `compound-default` rule, enabled as Always in the user-scoped plugin |
| Claude Code | `~/.claude/rules/compound-skills.md` |

Custom `CODEX_HOME` and `CLAUDE_CONFIG_DIR` locations are respected. Saved Codex and Claude rules stay on this machine; repeat setup on another machine or profile. Keep the plugin installed and enabled in each app. Host settings and project-specific guidance can change how defaults apply; setup checks saved rules and reports Cursor as host-managed, without verifying runtime loading.

`disable global` removes the managed Codex and Claude defaults. For Cursor, change `compound-default` to Manual or disable it in Customize. Independent project defaults remain in place.

## Reassess an existing project

Run in the project you want to clean up:

| Codex | Cursor | Claude Code |
| --- | --- | --- |
| `$setup` | `/setup` | `/compound-skills:setup` |

Each explicit project setup enables guidance and reruns assessment, even when previously completed. The agent inspects the code map, architecture, dependencies, scripts, docs, tests, and Git conventions; applies justified cleanup; and verifies the diff with relevant checks. Proven obsolete or redundant material is removed rather than archived. Useful regression tests stay; a large test suite alone is not bloat. Existing unfinished work and the Git index are preserved. Cleanup uses exact working-tree deletions; uncertain deletions or major redesigns are reported for a separate decision. Another active assessment is allowed to finish first.

Setup applies to the current project, not every repository on the machine. Global setup only enables defaults; new repositories receive automatic first-use onboarding during normal coding work. Subsequent work follows the engineering guidance without repeating a command. Project setup preserves unrelated instructions in managed routing sections and handles Codex overrides and legacy Claude compatibility. See [assessment details](skills/compound/references/onboarding.md).

For chat-only activation, use `compound session` or a bare `compound` invocation with the same host prefixes; it writes no files. See [activation details](skills/compound/references/activation.md).

## See your codebase

With global or project activation enabled, repository tasks use an existing host index when suitable, or a focused Compound code map before broad exploration. Write-authorized work starts or reuses the local map service; read-only analysis reuses a validated cache when available and otherwise scans in memory, without starting the service or writing cache files. The agent's text summary defaults to 2,500 characters. Confirm behavior in source and tests.

Open the live viewer with its own command:

| App | Command |
| --- | --- |
| Codex | `$map` |
| Claude Code | `/compound-skills:map` |
| Cursor | `/map` |

Add a focus such as `map pricing`. In Claude Code, `/map` can also resolve when no other skill shares that name. Start a new chat after updating so the new command appears; Claude Code also supports `/reload-plugins`. The older `compound map` form still routes to the same viewer.

The viewer opens at **`http://127.0.0.1:43127/`**. Its terminal-style workspace includes:

- **A full repository graph:** folder colors, organic clusters, zoom, pan, drag, search highlights, and readable labels. Explore up to 5,000 indexed files; drawing is capped at 20,000 links, with counts showing the complete indexed relationships.
- **Useful navigation:** browse folders, files, or symbols; inspect imports and importers; move backward and forward through selected files.
- **Impact and trace:** find direct and transitive importers, or follow a shortest recorded import path between two files. These are structural dependency views, not a complete runtime call graph.
- **Git awareness:** see changed files and their neighbors, the current branch, and files that often changed together in recent commits.
- **Source and context:** open an indexed file's read-only source preview, jump to a symbol's line, or copy at most 2,500 characters of focused context into your chat.

One local service handles registered projects. The viewer opens immediately, indexes in the background, and keeps the last map available during incremental updates. Reopening `map` reuses its index; saved project links survive service restarts and restore on demand. The host may request local cache and network access. Use `map status` to inspect the service and `map stop` to stop it. It runs until stopped or the machine session ends; the next coding or map request starts it again. It does not scan every project at login. Set `COMPOUND_MAP_PORT` for another local port.

Python 3.11+ and Git are required. The core adds no runtime dependencies, model calls, database, filesystem watcher, or frontend framework; semantic LSP lookup requires a separately installed server. Python receives AST outlines; JavaScript/TypeScript receives bounded outlines, exports, and local import resolution, including supported `tsconfig`/`jsconfig` aliases. Go, Rust, Java, C/C++, C#, Ruby, PHP, Swift, and Kotlin have heuristic declaration outlines. Go and Rust also have bounded local module/import links; other languages still require native import search. The read-only `symbol_lookup.py` helper finds exact-name declarations and bounded lexical occurrence locations, not semantic references. An opt-in `lsp_lookup.py` adapter can query an explicitly selected installed language server for semantic definitions and references. Git-listed hand-written `build/` and `dist/` source is included; ignored output and dependency folders stay excluded. Each pass reads at most 64 MiB, with a 1 MiB per-file limit. Files beyond those limits retain metadata with an explicit outline warning. Unknown or dynamic imports, parser limits, and scan failures remain visible. This plugin does not bundle a language server or claim Empryo's full semantic editing capabilities.

For repeated write-authorized lookups, `symbol_lookup.py --service` uses the local service’s bounded in-memory postings cache; it never persists postings. Postings can contain words from code, comments, and strings and remain in memory until eviction or service shutdown. The LSP adapter runs only an explicitly specified trusted server, which receives source text and inherits the caller’s environment and permissions; it is not sandboxed.

Metadata stays in the local user cache outside your repository. Normal map responses contain no source bodies. Clicking **Source** reads only the requested indexed file, limited to a 64 KiB preview; the service does not cache source bodies. Ignore rules, private-file exclusions, and symlink checks apply. The service binds to loopback and rejects foreign origins. Summaries copied into a chat become part of that chat's context. Details: [code maps](skills/compound/references/map.md).

### Agent navigation

Set `COMPOUND_SKILL_DIR` to the installed `compound` skill directory (the directory containing its `SKILL.md`). These portable helpers return bounded JSON without source snippets:

```bash
# Exact-name outline matches and lexical occurrence lines; no writes or service.
python3 -B "$COMPOUND_SKILL_DIR/scripts/symbol_lookup.py" --repo . --symbol Example

# Optional repeated-query acceleration, for write-authorized work only.
python3 -B "$COMPOUND_SKILL_DIR/scripts/symbol_lookup.py" --repo . --symbol Example --service

# Optional semantic lookup with a trusted, explicitly selected local server.
python3 -B "$COMPOUND_SKILL_DIR/scripts/lsp_lookup.py" --repo . --file src/main.cpp --line 4 --column 5 --server-command-json '["clangd","--background-index=false"]'
```

The adapter starts a stdio server per lookup and requires both definition and references capabilities. A language server is executable code, receives source text and runs with the caller’s permissions. Run only one you trust. Input positions are 1-based Unicode code points; returned columns use the negotiated LSP encoding. See [code maps](skills/compound/references/map.md) for limits, privacy, and fallback behavior.

## Nine engineering workflows

`compound` reads the project's instructions, identifies the task, and opens the relevant guide. It scales effort to uncertainty and impact, using the host's available models and tools.

| Workflow | How it helps |
| --- | --- |
| [Investigate](skills/compound/references/investigate.md) | Trace behavior through callers, configuration, state, and side effects; distinguish recorded rationale from inference |
| [Design and implement](skills/compound/references/design.md) | Start with concrete caller examples and acceptance cases; choose clear interfaces, valid states, and ownership |
| [Debug](skills/compound/references/debug.md) | Reproduce the failure, distinguish competing causes, add a regression check, and replay the original case |
| [Refactor](skills/compound/references/refactor.md) | Establish a behavior baseline, simplify responsibilities and layers, and verify equivalence as code moves |
| [Performance](skills/compound/references/performance.md) | Define a representative workload, measure a baseline, find the bottleneck, and check correctness alongside speed |
| [Review](skills/compound/references/review.md) | Follow the affected contract and return findings with locations, triggering conditions, impact, and evidence |
| [Verify](skills/compound/references/verify.md) | Match checks to the claim: user behavior, integration, regression, refactoring, performance, or packaging |
| [Repository hygiene](skills/compound/references/repo-hygiene.md) | Inspect clutter, source-size candidates, script references, ignore rules, and accumulated agent artifacts |
| [Git and pull requests](skills/compound/references/git.md) | Follow project formats, write clear commit/PR titles and explanations, report verified checks, and preserve human attribution |

## Native-agent comparison status

| Native host | Without Compound | With Compound |
| --- | --- | --- |
| ChatGPT via Codex CLI | Not measured | Not measured |
| Claude Code | Not measured | Not measured |

A controlled four-arm native benchmark is still needed before making direct speed, cost, or quality claims. The experiment below is a smaller Empryo-hosted, guidance-only sanity check, not a substitute for that comparison.

## Small headless comparison (one synthetic task)

This is a sanity check, not evidence of general improvement. All four runs used Empryo 3.12.0-beta `--headless` with fresh synthetic directories, `--no-profile --no-genome`, low effort, a 120-second timeout, the same task and safety prompt, and local tools only. “Guidance off” injected no Compound files; “on” preloaded this checkout’s `skills/compound/SKILL.md`, `skills/compound/references/debug.md`, and `skills/compound/references/verify.md` via `--include`. This was instruction-only, not an installed Compound plugin: the safety prompt prohibited its map service, so the benchmark does not test full Compound functionality. The initial `total.py` returned the unclamped `subtotal_cents - discount_cents + shipping_cents`; the initial tests covered 2,500/500/450 → 2,450 and a deliberately failing 100/150/0 → 0. The task fixed `total_cents` to return `max(0, subtotal_cents - discount_cents + shipping_cents)` and add a regression test. A separate grader checked 2,500/500/450 → 2,450, 100/150/0 → 0, 100/150/100 → 50, and 100/150/25 → 0 (subtotal/discount/shipping); every arm also passed its three unit tests.

<details>
<summary>Reconstructed initial two-file fixture</summary>

`total.py`:

```python
def total_cents(subtotal_cents, discount_cents=0, shipping_cents=0):
    """Return amount due, in integer cents."""
    return subtotal_cents - discount_cents + shipping_cents
```

`test_total.py`:

```python
from total import total_cents
import unittest

class TotalTests(unittest.TestCase):
    def test_existing_normal_total(self):
        self.assertEqual(total_cents(2500, discount_cents=500, shipping_cents=450), 2450)

    def test_discount_cannot_make_total_negative(self):
        self.assertEqual(total_cents(100, discount_cents=150), 0)
```

</details>

| Empryo route | Guidance | Correct / 4 | Wall time | Input / output tokens | Cache read / write¹ | CLI-reported cost² |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `subscriptions/gpt-6-luna` | Off | 4/4 | 10.61 s | 72,621 / 437 | 56,832 / 0 | $0.002366 |
| `subscriptions/gpt-6-luna` | On | 4/4 | 20.75 s | 129,592 / 615 | 111,104 / 0 | $0.003267 |
| `subscriptions/claude-haiku-5-5` | Off | 4/4 | 11.32 s | 116,954 / 1,049 | 92,705 / 24,235 | $0.004482 |
| `subscriptions/claude-haiku-5-5` | On | 4/4 | 14.16 s | 156,565 / 1,180 | 151,311 / 5,238 | $0.002759 |

¹ Cache figures are provider-reported subsets of input tokens. ² Cost is Empryo’s estimate, not a billing receipt. Wall time is `/usr/bin/time -p` real time, including host startup and local tool work. Token totals cover the full tool loop, not just the user prompt. Cache was observed, not disabled; runs were not repeated or randomized. Correctness was identical, while guidance-on took longer and used more reported input tokens in this one task. The cost estimates varied with uncontrolled caching, so no broader performance, savings, or quality claim follows.

These are Empryo’s exact subscription route labels—not ChatGPT’s web app or Claude Code—and the upstream model identity is not independently verified here. Empryo reports different provider-side capabilities for these routes; this task needed only local repository tools, so it is not a tool-parity benchmark. `proxy/gpt-5.4` was also tried but returned HTTP 401 before model execution and was excluded. A native Codex/Claude Code four-arm comparison was not run: the first Codex isolation check reported user-level hooks, and a later probe relied on an experimental skill-discovery control while omitting model identity. Isolation could not be independently verified. No direct ChatGPT or Claude Code performance claim is made.

To reproduce, create a fresh copy of the same two-file fixture for each arm under `$ROOT/{gpt-off,gpt-on,claude-off,claude-on}` and use this identical prompt: “Fix `total_cents` so amount due is `max(0, subtotal_cents - discount_cents + shipping_cents)`. Preserve existing integer-cent behavior. Add focused regression tests for shipping making an otherwise negative pre-shipping balance positive. Run the tests and stop once verified. Make only necessary edits; do not change README or files outside this synthetic repository.” Run each arm with `/usr/bin/time -p empryo --headless --json --no-profile --no-genome --model MODEL --effort low --max-steps 12 --timeout 120000 --cwd "$ROOT/ARM" --system "$SAFE_PROMPT" "$TASK_PROMPT"`; for the two `on` arms also pass `--include` for the three local Compound files listed above. The exact common safety prompt was: “Controlled synthetic benchmark: operate only on files inside the current synthetic working directory. Do not access the network, any user/global config or path outside this directory; do not use repository map services, provider web search, computer, or hosted code-execution tools. Use the same local file and shell tools available in this host. Run only local tests. Never read or print secrets. Stay within the authorized task.” These results describe this host and these routes only.

## Offline code-map benchmark

Run `python3 -B scripts/benchmark_code_map.py --files-per-language 20 --repetitions 3` to generate a temporary, synthetic five-language Git repository and print measured JSON. One run on macOS arm64 with Python 3.14.5 and 10 logical CPUs (2026-10-28), with 103 generated files (including one manifest) and 331,745 UTF-8 bytes, returned 5/5 expected declarations, 20/20 expected lexical occurrence lines, and 2/2 Go/Rust local import edges; it does not score semantic references or model quality.

| Map pass | Time | Files parsed | Source bytes read |
| --- | ---: | ---: | ---: |
| Cold | 0.198 s | 103 | 331,745 |
| Warm median (3 samples) | 0.095 s | 0 | 0 |
| After one edit | 0.105 s | 1 | 230 |

Cold means an empty Compound metadata cache; operating-system caches were not controlled. In the same fixture, a primed in-process postings cache served all 102 scanned source files without rereading source bytes for each of the five queries. This excludes service startup and does not mean zero filesystem operations. These small, synthetic measurements are a reproducible sanity check, not a market ranking or a claim about model tokens; timings vary by machine and load.

Architecture guidance favors simpler responsibilities, less reader effort, and short comments only where intent or constraints need explaining. A long file alone is insufficient reason to split it. Independent work can be delegated when useful and supported; returned artifacts still need inspection.



After activation, Compound guides engineering tasks without a repeated command. Automatic onboarding provides bounded first-use cleanup; explicit project `setup` requests another assessment. Later work follows the task you authorize. Explanations and reviews stay read-only. It does not run background restructuring.

## Try it on your project

Once activated, give normal requests such as:

| Goal | Example task |
| --- | --- |
| Improve architecture | Audit this project's architecture. Implement the highest-value simplifications, preserve existing behavior, and verify the changes. |
| Fix a stubborn bug | Reproduce this failure, identify its cause, make the smallest correction, and replay the original case. |
| Review a change | Review this diff for correctness, ownership, retry behavior, and unnecessary complexity. Report concrete findings without editing. |

## How the toolkit grows

New source material is integrated in this repository through the [maintainer guide](CONTRIBUTING.md): select useful ideas, consolidate overlap, compare actual behavior and context cost, and preserve provenance in [SOURCES.md](SOURCES.md). This is repository maintenance; it adds no user command or routine prompt overhead.

## Repository hygiene with a practical adoption path

The bundled Python 3.11+ [checker](skills/compound/scripts/repo_audit.py) audits repository-root clutter, scratch files and directories, source-size thresholds, worktree accumulation, `.gitignore` gaps, scripts without textual references, and some ignored agent litter.

It supports configurable rules, JSON output, strict mode, and a baseline for adopting an existing messy repository. Accepted findings remain visible as backlog; new findings and growth of baselined oversized files become active again. Audits are read-only; `--write-baseline` explicitly writes the baseline file.

These findings are review heuristics. They do not prove architectural quality or dead code. Confirm callers and behavior before removing files. See the [audit guide](skills/compound/references/repo-hygiene.md) for commands and configuration.

## Inspect the plugin's context cost

The toolkit has one shared engineering skill, a thin map command, focused references, and executable checks. There is no required model, MCP server, external plugin, or automatic hook.

From a source checkout, stage intended changes when using Git, then run:

```sh
python3 scripts/check.py --json
```

The package checker validates host manifests, skill frontmatter, local links, and release content, including common credential and private-path patterns. It also reports discovery descriptions, entrypoint bodies, optional references, metadata, and scripts separately. Counts are UTF-8 bytes and words; token costs depend on the model's tokenizer and host framing.

Python 3.11+ is required for the bundled scripts. First-use completion is stored in `~/.cache/compound-skills/onboarding.sqlite3`; `COMPOUND_SKILLS_STATE_DIR` can select a different local state directory. Local development tests and evaluation artifacts are intentionally excluded from the distributed package.

## Credits

Adapted selectively from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), with lineage from the earlier Karpathy-inspired guidelines. See [SOURCES.md](SOURCES.md), [third-party notices](THIRD_PARTY_NOTICES.md), and [MIT license](LICENSE).
