# Changelog

Notable changes to Compound Skills, newest first. Every change is in the Git history; benchmark numbers come from [bench/](bench/README.md) and are explained in the [README](README.md#benchmark).

## 0.14.0 (2026-10-31)

- The always-on rule now asks agents to reproduce a reported bug and show its regression test failing before fixing it, and to pin current behavior with a test before a refactor. Against 0.13.0 in the same runs, Claude Sonnet 5.5 reproduced the bug first in 15 of 15 fixes instead of 1, and both Claude Opus 5.5 and Sonnet finished the refactor safely in 5 of 5 runs instead of 2 and 0, at 1.06× and 1.03× 0.13.0's cost.
- Rules saved by an earlier `setup` or `setup-global` keep the old text until you update and run it again.
- The benchmark is now tracked in `bench/`, with four real Flask and click bugs as harder tasks, so every guidance change can be measured before it ships.

## 0.13.0 (2026-10-31)

- The map query is now the first repository search of a coding task, before any other search, read, or edit.
- Focus ranking weighs distinctive query words in paths, symbols, and the text of the leading candidate files.

## 0.12.1 (2026-10-31)

- Code map viewer fixes for tablets and phones: the inspector docks beside the graph on tablets, drawers stay put when the window narrows, keyboard focus stays on the chosen row and panel, and long names stay inside their panels.

## 0.12.0 (2026-10-30)

- Symbol lookup, more language outlines, and an opt-in adapter for a trusted language server.
- Graph hover focus, live dragging, and smooth zoom in the code map viewer.
- Frontend work keeps every tooltip within two visible lines.
- Hardening from a full review of the map, lookup, audit, setup, and onboarding helpers: bounded Git inventories, CR-only line endings, JS and TS comments and regexes, repository names that are not UTF-8, Windows service startup, and clearer notes when a limit hides data.

## Earlier

0.1 to 0.11 built the plugin: activation for a session, project, or all projects across Claude Code, Codex, and Cursor; the one-time repository check-up; shared Git and pull request conventions; and the code map with its live viewer.
