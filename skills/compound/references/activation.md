# Activation

These modes choose when Compound guides engineering work. Explicit project `setup` also requests a fresh assessment and verified cleanup.

## Current chat

A bare invocation or `session` enables the following guidance for the rest of the chat. Acknowledge activation briefly and apply it to any supplied task.

> Review diffs, callers and tests. Probe unresolved findings when permitted. After denial, source only. Use required native Read before edits. Bugs require a targeted failing regression before source edits, then the full suite. Extra checks need project requirements or evidence gaps. For scoped extractions, cover gaps, baseline once, preserve policies, retest, review diff. Search checkout. Batch independent calls. Use documented checks, avoiding byproducts (`python -B`). Diagnose setup before retrying. Reuse passing checks while inputs and environment match. Load `compound` for broader refactors, features, performance and PR authoring. Follow project and user instructions. Report checks and limits. Omit AI commit attribution.

Review findings alone do not authorize fixes. For other tasks, select checks for the changed surface.

The activation step writes no files; later tasks retain their normal authorization. New chats need activation unless project or global defaults apply. A request to stop using Compound in this chat overrides the preference without changing saved defaults.

## Saved defaults

Use the bundled [helper](../scripts/project_setup.py) through Python 3.11+, using the skill's actual install directory.

`setup global` enables personal defaults across projects. Save routing first:

```bash
python3 <installed-skill-dir>/scripts/project_setup.py enable --global
```

It manages a small routing section in the Codex home's `AGENTS.md` and existing nonempty `AGENTS.override.md`, and a Claude user rule at `~/.claude/rules/compound-skills.md`. It respects `CODEX_HOME` and `CLAUDE_CONFIG_DIR`. Without `--host`, it selects apps whose configuration folder exists and names any it skipped. Use `--host codex`, `--host cursor`, or `--host claude` for one app, or `--host all` for every app.

After routing succeeds, configure optional map access for the selected hosts. Resolve `COMPOUND_SKILLS_STATE_DIR` (default `~/.cache/compound-skills`) and create it when permitted. Merge only its absolute path into the native write-path lists:

- Codex: `sandbox_workspace_write.writable_roots` in `$CODEX_HOME/config.toml` (default `~/.codex/config.toml`); if a named permission profile is active, use its existing filesystem rules. See [official configuration](https://developers.openai.com/codex/config-reference).
- Cursor: `additionalReadwritePaths` in `~/.cursor/sandbox.json`. See [native sandbox configuration](https://cursor.com/docs/reference/sandbox).
- Claude Code: after enabling, merge the helper's `hosts.claude.permission_rules` into `permissions.allow` in `$CLAUDE_CONFIG_DIR/settings.json` (default `~/.claude/settings.json`), so the map query and guide reads need no approval in each task. They name this install's path, so they come only from Claude Code's own copy: run from another app's copy, the helper reports none and says so. Setup again after a plugin update replaces them.

Preserve existing entries, modes, approvals, networking, and unrelated settings. Back up and validate config before writing. Skip symlinked, malformed or inaccessible config paths and report the affected host. If state access is denied, skip its write-path setup and report that the live map and project assessment state may be unavailable. Routing stays enabled where the helper succeeded. Report routing and map access separately and use a fresh session to test the saved defaults.

Cursor carries the routing rule in the native plugin. Install at user scope and leave its `compound-default` rule set to Always in Customize → Rules. Global setup reports Cursor as host-managed; it cannot verify or change that UI setting. If available, inspect it through the host UI; otherwise explain this one-time installation requirement. Do not edit Cursor's private database or claim Cursor is configured from a file written by the helper.

`setup` alone enables guidance and assesses the intended project, including previously completed projects. Establish its root from the task and repository; ask only if ambiguous. Read project instructions and record existing changed and untracked paths before writes:

```bash
python3 <installed-skill-dir>/scripts/project_setup.py enable --project-root <project-root>
```

Project setup manages `AGENTS.md`, an existing nonempty root `AGENTS.override.md`, and a project Claude rule when legacy Claude instructions shadow `AGENTS.md`. It changes no global defaults. Both project and global setup stop when the helper detects that an instruction file changed before its update. Report any already-applied paths and rerun against the latest text.

Read the JSON result. After successful project enable, even when routing was already enabled, run the core code-map startup and follow [repository assessment](onboarding.md) in explicit setup mode (`claim --refresh`). Reserve that assessment for explicit project setup. Preserve unrelated instructions; stop cleanup on routing errors or partial results. Report routing, assessment, changes, checks, and deferred findings separately; a busy lease means assessment is deferred. Enable the current chat preference too.

The plugin must be installed and enabled at user scope in each app for global use. Setup does not install plugins or verify native runtime loading. New chats load defaults under normal host settings; project guidance and explicit user choices take priority. Saved Codex and Claude rules are machine-local; Cursor follows the plugin installation scope. These are model instructions, not guaranteed enforcement or background refactoring.

## Refresh saved guidance

For an explicit `compound refresh`, resolve the project root and update its existing managed sections.

```bash
python3 <installed-skill-dir>/scripts/project_setup.py refresh --project-root <project-root>
```

For `compound refresh global`, use `refresh --global` and preserve any requested host selection. Refresh updates only existing marked blocks. Skip map startup, assessment and permission setup. Report changed paths, status, and warnings. Open a fresh chat to load the refreshed instructions. Use `setup-global` from Claude Code when its map permissions need to be refreshed for the new install path.

## Inspect or remove defaults

For `status` or `disable`, replace `enable` in the corresponding command; preserve `--global` when requested and any host selection. Status is read-only. For project status, also run `onboarding.py status --repo <project-root>` from the installed scripts directory to report whether a project `setup` assessed it; global status checks saved routing for the same installed apps as global setup and directs users with outdated rules to refresh. Use `--host all` to inspect every supported host. Inspect native cache-path entries and Claude Code permission rules only when the user also asks about map access. Disable removes only the helper's managed sections in that scope, deletes files left empty, and ends the current chat preference. Global disable leaves independent project defaults intact; also remove the Claude Code permission rules that global setup added. To stop the Cursor default, change its rule to Manual or disable it in Customize; report that host-managed step separately. Report the actual helper result; existing chats may need a new session to rebuild their instruction context.

For a Claude Code map permission check, run this from Claude Code's installed copy:

```bash
python3 -B <installed-skill-dir>/scripts/project_setup.py status --global --host claude --check-claude-permissions
```

Report `hosts.claude.permission_check` separately from saved routing. It checks whether the exact expected entries are present in user `settings.json`. Effective access also depends on Claude Code's other permission settings. If entries are missing, run `setup-global` in Claude Code when the user asks to repair them. Unavailable settings leave routing status intact.
