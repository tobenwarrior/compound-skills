# Compound Skills

A compact engineering toolkit for **Codex, Cursor, and Claude Code**. Useful ideas accumulate through selective integration; overlapping instructions get consolidated.

Two skills share one portable source:

| Skill | Use |
| --- | --- |
| `compound` | Investigate, design, implement, debug, refactor, review, and verify software |
| `compound-integrate` | Evaluate another skill pack, merge useful guidance, or test a smaller version for a newer model |

The engineering skill loads the relevant reference when needed. It has no required model, MCP server, external plugin, or automatic hook. The bundled repository checker reports hygiene heuristics; it does not prove architectural quality.

## Install

### Codex

```sh
codex plugin marketplace add tobenwarrior/compound-skills
codex plugin add compound-skills@compound-skills
```

Use `$compound` or `$compound-integrate`.

### Claude Code

```text
/plugin marketplace add tobenwarrior/compound-skills
/plugin install compound-skills@compound-skills
```

Use `/compound-skills:compound` or `/compound-skills:compound-integrate`.

### Cursor

In Customize, use **From GitHub Repository** to add `tobenwarrior/compound-skills`, then install the plugin. Use `/compound` or `/compound-integrate`. See [Cursor's plugin documentation](https://cursor.com/docs/plugins).

## Keep it compact

Give `compound-integrate` a source and the problem its guidance should solve. It checks provenance, overlap, portability, observed behavior, and context cost before retaining material. Newer models can justify shorter instructions only after evaluation.

From a checkout, inspect package structure, links, release-content checks, and context measurements:

```sh
python3 scripts/check.py --json
```

The report separates discovery descriptions, skill entrypoints, optional references, and executable resources. It measures words and bytes, not a model-independent token count. Python 3.11+ is needed for the bundled checks. Local development tests are intentionally ignored and not distributed.

## Credits

Adapted selectively from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), with lineage from the earlier Karpathy-inspired guidelines. See [SOURCES.md](SOURCES.md), [third-party notices](THIRD_PARTY_NOTICES.md), and [MIT license](LICENSE).
