# Compound Skills

**Build cleaner software. Keep your agent's context focused.**

A compact engineering plugin for **Codex, Cursor, and Claude Code**. Get practical guidance for architecture, implementation, debugging, refactoring, and review—and a process for improving that guidance as you discover better skills.

After activation, give normal engineering requests. The optional `compound` command manages session, project, and global defaults.

- **Clearer architecture:** design around callers, explicit ownership, meaningful states, and interfaces that hide complexity.
- **Evidence behind changes:** reproduce failures, preserve behavior during refactoring, and verify observable results.
- **Consistent commits and PRs:** concrete titles, concise explanations, truthful validation, and no AI co-author credits across all three apps.
- **Set up once:** make Compound the default across all your projects in Codex, Cursor, and Claude Code, or limit activation to one project or chat.
- **First-repository cleanup:** inspect a repository once before its first coding change, apply safe verified cleanup, and report larger improvements as a backlog.
- **Focused context:** load the relevant reference when needed; keep a shared source across all three hosts.
- **Knowledge that compounds:** retain useful ideas, replace weaker guidance, and remove duplication as the toolkit evolves.

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

After installation, start a **new chat** in each app before using the commands. Claude Code can also load the install with `/reload-plugins`. If a plugin is missing after installation, reopen the app and check its plugin manager.

## Enable once, then work normally

After the user-scope installs above, run global setup **once from any one app**. Choose one command from the first row; you do not need to run it in all three:

| Action | Codex | Cursor | Claude Code |
| --- | --- | --- | --- |
| All projects on this machine | `$compound setup global` | `/compound setup global` | `/compound-skills:compound setup global` |
| Check global defaults | `$compound status global` | `/compound status global` | `/compound-skills:compound status global` |
| Remove global defaults | `$compound disable global` | `/compound disable global` | `/compound-skills:compound disable global` |

Global setup saves the Codex and Claude defaults together and adds only Compound’s local state directory to the native Codex/Cursor write-path lists so first-use completion can be remembered. Cursor includes its default in the plugin: install at user scope and keep the `compound-default` rule set to **Always** in Customize → Rules. New chats across your projects use Compound without repeating a command or adding files to every repository. Only a small routing rule stays active; detailed guidance loads when relevant.

Before the first write-authorized engineering task in a repository, Compound runs a bounded onboarding pass: inspect the structure and existing checks, audit hygiene, apply high-confidence cleanup, and verify changes. It preserves existing uncommitted work and leaves larger architecture changes for review. Read-only requests remain read-only. Completion is remembered locally across all three apps, so it does not repeat in every chat or add a marker to Git. See [first-use behavior](skills/compound/references/onboarding.md).

| App | Global rule |
| --- | --- |
| Codex | `~/.codex/AGENTS.md`, plus an existing nonempty `AGENTS.override.md` |
| Cursor | Bundled `compound-default` rule, enabled as Always in the user-scoped plugin |
| Claude Code | `~/.claude/rules/compound-skills.md` |

Custom `CODEX_HOME` and `CLAUDE_CONFIG_DIR` locations are respected. Saved Codex and Claude rules stay on this machine; repeat setup on another machine or profile. Keep the plugin installed and enabled in each app. Host settings and project-specific guidance can change how defaults apply; setup checks saved rules and reports Cursor as host-managed, without verifying runtime loading.

`disable global` removes the managed Codex and Claude defaults. For Cursor, change `compound-default` to Manual or disable it in Customize. Independent project defaults remain in place.

For a smaller scope, `compound setup` applies to one project and `compound session` applies to the current chat. A bare `compound` invocation also activates the chat. Use the same host command prefixes shown above. Session activation writes no files; project setup preserves existing instructions in a managed `AGENTS.md` section and handles Codex overrides and legacy Claude compatibility. See [activation details](skills/compound/references/activation.md).

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

Architecture guidance favors simpler responsibilities and less reader effort. A long file alone is insufficient reason to split it. Independent work can be delegated when useful and supported; returned artifacts still need inspection.

After activation, Compound guides engineering tasks without a repeated command. Its one-time onboarding pass provides bounded cleanup before the first coding change; later work follows the task you authorize. Explanations and reviews stay read-only. It does not run background restructuring.

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

The toolkit has one discoverable skill, focused references, and executable checks. There is no required model, MCP server, external plugin, or automatic hook.

From a source checkout, stage intended changes when using Git, then run:

```sh
python3 scripts/check.py --json
```

The package checker validates host manifests, skill frontmatter, local links, and release content, including common credential and private-path patterns. It also reports discovery descriptions, entrypoint bodies, optional references, metadata, and scripts separately. Counts are UTF-8 bytes and words; token costs depend on the model's tokenizer and host framing.

Python 3.11+ is required for the bundled scripts. First-use completion is stored in `~/.cache/compound-skills/onboarding.sqlite3`; `COMPOUND_SKILLS_STATE_DIR` can select a different local state directory. Local development tests and evaluation artifacts are intentionally excluded from the distributed package.

## Credits

Adapted selectively from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), with lineage from the earlier Karpathy-inspired guidelines. See [SOURCES.md](SOURCES.md), [third-party notices](THIRD_PARTY_NOTICES.md), and [MIT license](LICENSE).
