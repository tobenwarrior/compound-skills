# Activation

These modes configure when Compound guides engineering work. They do not authorize unrelated changes to the project.

## Current chat

A bare invocation or `session` enables Compound for subsequent engineering tasks in this chat until the user opts out. Treat that choice as a standing session preference; users can give normal task requests afterward. Apply the core skill and load only the references each task needs. Acknowledge activation briefly and continue any supplied task.

The session activation step writes no files; subsequent tasks retain their normal authorization. A new chat needs its own activation unless project defaults are enabled. A request to stop using Compound in this chat overrides the session preference without changing project defaults.

## Project defaults

For `setup`, establish the intended project root from the task and repository. Ask only if the destination is ambiguous. Invoke the bundled [helper](../scripts/project_setup.py) through Python 3.11+, using the skill's actual install directory:

```bash
python3 <installed-skill-dir>/scripts/project_setup.py enable --project-root <project-root>
```

Read its JSON result. The helper preserves unrelated instructions and manages a small section in `AGENTS.md`. It also handles an existing nonempty root `AGENTS.override.md` and, when legacy Claude instructions shadow `AGENTS.md`, a project rule at `.claude/rules/compound.md`. It does not edit ancestor instructions or global settings. Conflicting unmanaged files and malformed markers need resolution before setup can finish.

Enable session mode immediately too. Explain that future chats use the project instructions with Compound installed and enabled in that host. These are model instructions under the host's normal project settings, not guaranteed enforcement or a background optimizer. Report changed files and any warnings; do not claim activation when setup failed or remains partial.

## Inspect or remove defaults

`status` is read-only:

```bash
python3 <installed-skill-dir>/scripts/project_setup.py status --project-root <project-root>
```

`disable` removes only the helper's managed project sections:

```bash
python3 <installed-skill-dir>/scripts/project_setup.py disable --project-root <project-root>
```

Preserve unrelated instructions. Also end the current chat's Compound preference when disabling it. After any project change, report the actual helper result. Other open chats may need a new session to rebuild their instruction context.
