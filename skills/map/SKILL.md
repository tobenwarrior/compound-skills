---
name: map
description: "Trace Python code with exact file, symbol and line citations, or open the live repository map."
license: MIT
---

# Map

`<compound-skill-dir>` is the absolute path to `skills/compound` under this plugin’s root.

For exact Python citations, find unknown files with native search. Before answering, batch candidate lines or literal statements in one read-only lookup:

```bash
python3 -B "<compound-skill-dir>/scripts/symbol_lookup.py" --repo "<repo-root>" --location "<file:line>" --match "<file>" "<statement>" --excerpt 0
```

Use either option or mix them, up to 12 queries. Results follow query order and give the enclosing symbol. Omit `--excerpt` when you only need the locations. If lookup is unavailable, verify the enclosing definition in source. [Lookup details](../compound/references/map.md#symbol-lookup)

For a bare map invocation or a visual request, open the current repository's live viewer:

```bash
python3 -B "<compound-skill-dir>/scripts/map_server.py" open --repo "<repo-root>"
```

Add `--query "<focus>"` for a requested file or topic. Use `--no-open` when opening is unwanted. If browser launch fails, give the user the localhost URL printed by the command. Repeated opens reuse the service and index. Do not generate HTML snapshots or run onboarding cleanup for a viewing request.

For `map status` or `map stop`, run the helper's corresponding subcommand without `--repo`. Stopping closes the shared viewer service for all registered projects. Report the observed result. Details and coverage limits: [code maps](../compound/references/map.md).
