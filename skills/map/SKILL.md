---
name: map
description: "Use for Python file, symbol and line citations with scripts/map.py lookup --find, or to open the live repository map."
license: MIT
---

# Map

Use the directory containing this SKILL.md as `<map-skill-dir>`.

For Python file, symbol and line answers, reuse evidence that gives the statement and its enclosing symbol. Search for missing statements and verify their owners in one lookup with `--find`. Follow the requested call path when a statement has several matches. Use `--match "<file>" "<statement>"` for a known file or `--location "<file:line>"` for a known line.

```bash
python3 -B "<map-skill-dir>/scripts/map.py" lookup --repo "<repo-root>" --find "<statement>" --path "<file>"
```

Repeat `--find` and `--path` for shared scopes, or omit `--path` to search all tracked Python files. When statements have different scopes, batch `--find-in "<file-or-directory>" "<statement>"` pairs. Both modes return up to 12 matches. For existing Git search output use `--grep-input`. If lookup is unavailable, verify the enclosing definition in source. [Lookup details](../compound/references/map.md#symbol-lookup)

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
