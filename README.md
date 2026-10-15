# Compound Skills

**Build cleaner software. Keep your agent's context focused.**

A compact engineering plugin for **Codex, Cursor, and Claude Code**. Get practical guidance for architecture, implementation, debugging, refactoring, and review—and a process for improving that guidance as you discover better skills.

| Command | What you get |
| --- | --- |
| `compound` | Enable guidance for a session or project, then route engineering tasks to the relevant workflow |
| `compound-integrate` | Evaluate incoming skill packs, consolidate overlap, and test shorter instructions |

- **Clearer architecture:** design around callers, explicit ownership, meaningful states, and interfaces that hide complexity.
- **Evidence behind changes:** reproduce failures, preserve behavior during refactoring, and verify observable results.
- **Set up once:** keep Compound active for the current chat or make it the default for future chats in a project.
- **Focused context:** load the relevant reference when needed; keep a shared source across all three hosts.
- **Knowledge that compounds:** retain useful ideas, replace weaker guidance, and remove duplication as the toolkit evolves.

## Install

### Codex

```sh
codex plugin marketplace add tobenwarrior/compound-skills
codex plugin add compound-skills@compound-skills
```

Commands: `$compound` and `$compound-integrate`. Choose an activation mode below.

### Claude Code

```text
/plugin marketplace add tobenwarrior/compound-skills
/plugin install compound-skills@compound-skills
```

Commands: `/compound-skills:compound` and `/compound-skills:compound-integrate`. Choose an activation mode below.

### Cursor

In Customize, use **From GitHub Repository** to add `tobenwarrior/compound-skills`, then install the plugin. Commands: `/compound` and `/compound-integrate`. Choose an activation mode below. See [Cursor's plugin documentation](https://cursor.com/docs/plugins).

## Enable once, then work normally

After installation, activate Compound once for your chat or project:

| Scope | Codex | Cursor | Claude Code |
| --- | --- | --- | --- |
| Current chat | `$compound session` | `/compound session` | `/compound-skills:compound session` |
| Project, including future chats | `$compound setup` | `/compound setup` | `/compound-skills:compound setup` |
| Check project defaults | `$compound status` | `/compound status` | `/compound-skills:compound status` |
| Remove project defaults | `$compound disable` | `/compound disable` | `/compound-skills:compound disable` |

A bare `compound` invocation also enables the current chat. Once active, give normal engineering requests; you do not need to repeat the command for every task.

**Session mode** writes no files and lasts for the current chat. **Project setup** adds a small managed section to `AGENTS.md`, preserving existing instructions. New chats in that project pick up the default through their host's project instructions. Keep the plugin installed and enabled in each app you use.

Setup handles an existing nonempty Codex `AGENTS.override.md` and adds a small Claude project rule when legacy Claude instructions would hide `AGENTS.md`. It preserves unrelated content, supports repeated setup, and changes no global settings. Host settings can override project instructions. See [activation details](skills/compound/references/activation.md).

## Eight engineering workflows

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

Architecture guidance favors simpler responsibilities and less reader effort. A long file alone is insufficient reason to split it. Independent work can be delegated when useful and supported; returned artifacts still need inspection.

After activation, Compound guides engineering tasks without a repeated command. Explanations and reviews stay read-only; architecture changes follow the task you authorize. It does not run background restructuring.

## Try it on your project

Invoke the appropriate command for your host, then give it a task like:

| Goal | Example task |
| --- | --- |
| Improve architecture | Audit this project's architecture. Implement the highest-value simplifications, preserve existing behavior, and verify the changes. |
| Fix a stubborn bug | Reproduce this failure, identify its cause, make the smallest correction, and replay the original case. |
| Review a change | Review this diff for correctness, ownership, retry behavior, and unnecessary complexity. Report concrete findings without editing. |
| Add a skill pack | Evaluate this skill pack: SOURCE_URL. Merge useful missing guidance, remove overlap, preserve attribution, and report the context change. |
| Compact for a newer model | Compare shorter instructions against the current version using the same behavioral cases. Keep reductions supported by the results. |

Use `compound` for the first three examples and `compound-integrate` for the last two.

## Add knowledge without duplicating it

`compound-integrate` provides a repeatable intake process:

1. Identify the concrete failure the incoming guidance addresses.
2. Check its source, revision, license, assumptions, and overlap with existing guidance.
3. Merge a missing idea, replace weaker wording, keep a specialized reference on demand, or reject redundant material.
4. Compare actual outputs using representative tasks, including a case where the candidate should remain inactive.
5. Remove superseded instructions, measure the context change, and update [SOURCES.md](SOURCES.md).

For newer models, use unchanged behavioral cases to evaluate compression. A shorter version is retained when the observed results support it. Imported instructions are treated as source material; they cannot grant permission to publish, delete, message others, or change settings.

## Repository hygiene with a practical adoption path

The bundled Python 3.11+ [checker](skills/compound/scripts/repo_audit.py) audits repository-root clutter, scratch files and directories, source-size thresholds, worktree accumulation, `.gitignore` gaps, scripts without textual references, and some ignored agent litter.

It supports configurable rules, JSON output, strict mode, and a baseline for adopting an existing messy repository. Accepted findings remain visible as backlog; new findings and growth of baselined oversized files become active again. Audits are read-only; `--write-baseline` explicitly writes the baseline file.

These findings are review heuristics. They do not prove architectural quality or dead code. Confirm callers and behavior before removing files. See the [audit guide](skills/compound/references/repo-hygiene.md) for commands and configuration.

## Inspect the plugin's context cost

The toolkit has two discoverable skills, focused references, and executable checks. There is no required model, MCP server, external plugin, or automatic hook.

From a source checkout, stage intended changes when using Git, then run:

```sh
python3 scripts/check.py --json
```

The package checker validates host manifests, skill frontmatter, local links, and release content, including common credential and private-path patterns. It also reports discovery descriptions, entrypoint bodies, optional references, metadata, and scripts separately. Counts are UTF-8 bytes and words; token costs depend on the model's tokenizer and host framing.

Python 3.11+ is required for the bundled setup and check scripts. Local development tests and evaluation artifacts are intentionally excluded from the distributed package.

## Credits

Adapted selectively from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), with lineage from the earlier Karpathy-inspired guidelines. See [SOURCES.md](SOURCES.md), [third-party notices](THIRD_PARTY_NOTICES.md), and [MIT license](LICENSE).
