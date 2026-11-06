---
name: map
description: "Use for Python answers that require file, symbol and line citations, or to open the live repository map."
license: MIT
---

# Map

Use the directory containing this SKILL.md as `<map-skill-dir>`.

For Python file, symbol and line answers, locate the statements with narrow native search. Follow the requested call path when a statement has several matches. Before answering, verify the enclosing definitions in one batched lookup. Locate a literal statement with `--match "<file>" "<statement>"` or get the enclosing symbol for a known line with `--location "<file:line>"`.

For a scoped search and lookup in one call, use the Git matches as input.

```bash
git -C "<repo-root>" grep -n -z -I -F --no-color -e "<statement>" -- "<python-file>" |
  python3 -B "<map-skill-dir>/scripts/map.py" lookup --repo "<repo-root>" --grep-input --excerpt 0
```

Batch up to 12 queries in one call. Omit `--excerpt` when you only need locations. If lookup is unavailable, verify the enclosing definition in source. [Lookup details](../compound/references/map.md#symbol-lookup)

For a focused read-only map, query the repository. The query reuses existing cache entries without starting a service or writing state.

```bash
python3 -B "<map-skill-dir>/scripts/map.py" query --repo "<repo-root>" --query "<task terms>"
```

For a bare map invocation or a visual request, open the current repository's live viewer.

```bash
python3 -B "<map-skill-dir>/scripts/map.py" open --repo "<repo-root>"
```

Add `--query "<focus>"` for a requested file or topic. Use `--no-open` when opening is unwanted. If browser launch fails, give the user the localhost URL printed by the command. Repeated opens reuse the service and index. Do not generate HTML snapshots or run onboarding cleanup for a viewing request.

For `map status` or `map stop`, use the corresponding subcommand without `--repo`. Stopping closes the shared viewer service for all registered projects. Report the observed result. [Coverage and limits](../compound/references/map.md)
