---
name: map
description: "Trace Python code with exact file, symbol and line citations, or open the live repository map."
license: MIT
---

# Map

`<compound-skill-dir>` is the absolute path to `skills/compound` under this plugin’s root.

For exact Python citations, find unknown files with native search. Use one query per citation. Locate a literal statement with `--match "<file>" "<statement>"`, or get the enclosing symbol for a known line with `--location "<file:line>"`.

```bash
python3 -B "<compound-skill-dir>/scripts/symbol_lookup.py" --repo "<repo-root>" --match "<file>" "<statement>" --excerpt 0
```

Batch up to 12 distinct queries in one call. Results follow query order and give the enclosing symbol. Omit `--excerpt` when you only need the locations. If lookup is unavailable, verify the enclosing definition in source. [Lookup details](../compound/references/map.md#symbol-lookup)

For a bare map invocation or a visual request, open the current repository's live viewer:

```bash
python3 -B "<compound-skill-dir>/scripts/map_server.py" open --repo "<repo-root>"
```

Add `--query "<focus>"` for a requested file or topic. Use `--no-open` when opening is unwanted. If browser launch fails, give the user the localhost URL printed by the command. Repeated opens reuse the service and index. Do not generate HTML snapshots or run onboarding cleanup for a viewing request.

For `map status` or `map stop`, run the helper's corresponding subcommand without `--repo`. Stopping closes the shared viewer service for all registered projects. Report the observed result. Details and coverage limits: [code maps](../compound/references/map.md).
