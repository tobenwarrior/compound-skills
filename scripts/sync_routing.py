#!/usr/bin/env python3
"""Regenerate Cursor's always-on rule from Compound's default routing text."""

from pathlib import Path

from check import CURSOR_RULE_PATH, DEFAULT_ROUTING_PATH

ROOT = Path(__file__).resolve().parents[1]
CURSOR_HEADER = '---\ndescription: "Route engineering work through Compound Skills"\nalwaysApply: true\n---'

if __name__ == "__main__":
    rule = (ROOT / DEFAULT_ROUTING_PATH).read_text(encoding="utf-8").strip()
    (ROOT / CURSOR_RULE_PATH).write_text(f"{CURSOR_HEADER}\n\n{rule}\n", encoding="utf-8")
