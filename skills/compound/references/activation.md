# Activation

These modes choose when Compound guides engineering work. Explicit project `setup` also requests a fresh assessment and verified cleanup.

## Current chat

A bare invocation or `session` enables the following guidance for the rest of the chat. Acknowledge activation briefly and apply it to any supplied task.

> Review diffs, callers and tests. Probe only if permitted and source is insufficient. After denial, source only. Bug fixes require one failing regression before source edits and a final full suite. Scoped extractions require known callers and behavior. Search the checkout. Add missing cases. Baseline once, preserve policies, retest, run required checks, review diff, finish. Use documented commands. Prevent test byproducts. Diagnose setup failures before retrying. Reuse passing checks while inputs and environment match. Honor read/edit prerequisites. Load `compound` for other refactors, features, performance and PR authoring. Follow project and user instructions. Report checks and limits. Omit AI commit attribution.

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

Read the JSON result. After successful project enable, even when routing was already enabled, run the core code-map startup and follow [repository assessment](onboarding.md) in explicit setup mode (`claim --refresh`). Global setup, session activation, status, and disable do not run this pass. Preserve unrelated instructions; stop cleanup on routing errors or partial results. Report routing, assessment, changes, checks, and deferred findings separately; a busy lease means assessment is deferred. Enable the current chat preference too.

The plugin must be installed and enabled at user scope in each app for global use. Setup does not install plugins or verify native runtime loading. New chats load defaults under normal host settings; project guidance and explicit user choices take priority. Saved Codex and Claude rules are machine-local; Cursor follows the plugin installation scope. These are model instructions, not guaranteed enforcement or background refactoring.

## Inspect or remove defaults

For `status` or `disable`, replace `enable` in the corresponding command; preserve `--global` when requested and any host selection. Status is read-only. For project status, also run `onboarding.py status --repo <project-root>` from the installed scripts directory to report whether a project `setup` assessed it; global status checks saved routing for the same installed apps as global setup and warns about outdated rules. Use `--host all` to inspect every supported host. Inspect native cache-path entries and Claude Code permission rules only when the user also asks about map access. Disable removes only the helper's managed sections in that scope, deletes files left empty, and ends the current chat preference. Global disable leaves independent project defaults intact; also remove the Claude Code permission rules that global setup added. To stop the Cursor default, change its rule to Manual or disable it in Customize; report that host-managed step separately. Report the actual helper result; existing chats may need a new session to rebuild their instruction context.
