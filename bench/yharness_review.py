#!/usr/bin/env python3
"""Offline grader for the pinned Flask review fixture.

Check triggers and impacts within individual findings. A shared file citation
can supply the path for a finding's line reference. Verify the source pin before
accepting any answer. Source-check additional claims before publishing results.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


SCHEMA = "yharness-review-offline-6"
EXPECTED_PARENT = "49943b5a94413a530761350f04e896f76e8d620e"
EXPECTED_TREE = "719747b4621bddad647f0fbe89325ee1443b12d7"
STATIC_FOLDERS_LINES = range(413, 443)


RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "D1": {
        "section": (r"d1\b", r"late[- ]binding", r"closure", r"last folder", r"folder route"),
        "trigger": (
            r"(loop|iteration|for each|per[- ]folder).{0,100}(directory|folder|variable)",
            r"(directory|folder).{0,100}(loop|iteration|closure|request)",
            r"defined in the loop",
        ),
        "impact": (
            r"(?:last|final) (folder|directory|path)",
            r"all (prefix|route|folder).{0,80}last",
            r"every (prefix|route).{0,80}(same|last)",
            r"serves?.{0,80}last (folder|directory)",
        ),
    },
    "D2": {
        "section": (r"d2\b", r"max[_ -]?age", r"cach(?:e|ing)", r"caching option"),
        "trigger": (
            r"max[_ -]?age\s+or",
            r"max[_ -]?age.{0,80}(fals|truth|zero|0)",
            r"\b0\b.{0,80}max[_ -]?age",
            r"falsy",
        ),
        "impact": (
            r"(ignore|treat|fall back|use).{0,80}(0|zero)",
            r"(cache|cach).{0,100}(remain|still|enabled|not disabled|cannot|does not)",
            r"does not disable cach",
            r"cannot disable cach",
            r"falls? through.{0,80}(default|config|cache)",
            r"\b(?:0|zero)\b.{0,40}\bis (?:discarded|ignored)\b.{0,90}\bdefault cach(?:e|ing)(?: policy)? is (?:used|applied)\b",
            r"cache-control.{0,100}(public|max-age)",
            r"never works",
        ),
    },
    "D3": {
        "section": (r"d3\b", r"path traversal", r"directory traversal", r"arbitrary file"),
        "trigger": (
            r"\bsend_file\b[^.!?]{0,120}\b(?:os\.path\.join|path\.join|join)",
            r"\bjoin(?:s|ed|ing)?\b[^.!?]{0,120}\bsend_file\b",
            r"(?:request|requested|untrusted|user)[^.!?]{0,100}(?:path|filename)[^.!?]{0,120}send_file",
            r"(os\.path\.join|path\.join|join)[^.!?]{0,120}\b(directory|filename)\b",
            r"<path:filename>",
            r"\.\..{0,40}(segment|path|filename)",
        ),
        "impact": (
            r"path traversal",
            r"(read|access|escape|outside).{0,100}(folder|directory|root|path|file)",
            r"outside the (folder|directory)",
            r"escape the (folder|directory)",
        ),
    },
}

ALLOWED_EXTRA = (
    (r"missing (file|resource)", r"(file|notfound|404|500)"),
    (r"filenotfounderror", r"(404|500|missing|error)"),
    (r"test", r"(only|one|single|cover|coverage|traversal|max[_ -]?age)"),
    (r"endpoint", r"(nested|duplicate|prefix|url_for)"),
    (r"strong reference", r"app"),
    (r"versionadded", r"(version|number|3\.2)"),
)
UNSUPPORTED_MARKERS = (
    r"\bblueprint(s)?\b",
    r"not registered",
    r"missing (method|endpoint)",
    r"never (called|used|registered)",
)
META = (
    r"^((do not|don't) merge|merge|review|three|all three|no other|no additional)",
    r"\b(no|none|without) (other|additional|unsupported) (finding|problem|issue)s?\b",
)


def clean(text: str) -> str:
    """Normalize markdown punctuation and whitespace for evidence matching."""
    text = text.replace("`", "").replace("**", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def _block_ranges(text: str) -> list[tuple[int, int, str]]:
    """Return blank-line blocks with source offsets and normalized text."""
    normalized = text.replace("\r\n", "\n")
    result = []
    for block in re.finditer(r"(?ms)(?:\A|\n\s*\n+)(.+?)(?=\n\s*\n+|\Z)", normalized):
        lines = [line.strip() for line in block.group(1).splitlines() if line.strip()]
        if lines:
            result.append((block.start(1), block.end(1), clean(" ".join(lines))))
    return result


def blocks(text: str) -> list[str]:
    """Return blank-line blocks without joining separate findings."""
    return [block for _, _, block in _block_ranges(text)]


def has_any(text: str, patterns: tuple[str, ...]) -> bool:
    """Return whether normalized text contains one of the supplied regexes."""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def location(text: str) -> bool:
    """Require the changed caller and a source path or line reference."""
    path = has_any(text, (r"(?:src/)?flask/app\.py", r"app\.py"))
    caller = has_any(text, (r"add_static_folders", r"flask\.add_static_folders", r"\bview\b"))
    cite = caller or has_any(text, (r"(?:app\.py|add_static_folders)[ :#-]+\d+", r"\bline\s+\d+"))
    return path and cite


def _headings(text: str) -> list[tuple[int, str]]:
    """Return Markdown heading offsets and normalized labels."""
    return [
        (match.start(), clean(match.group(2)))
        for match in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", text.replace("\r\n", "\n"))
    ]


def _section_category(label: str) -> str | None:
    """Classify a finding from its heading or numbered-item lead."""
    for name in ("D1", "D2", "D3"):
        if has_any(label, RULES[name]["section"]):
            return name
    return None


def _explicit_finding_heading(label: str) -> bool:
    """Return whether a heading identifies a finding rather than a summary."""
    if has_any(label, (r"\bd[123]\b", r"^\d+[.)]", r"\b(critical|high|medium|low|blocking)\b")):
        return True
    return not has_any(label, (r"summary", r"overview", r"review", r"findings?", r"evidence"))


def _list_items(text: str) -> list[tuple[int, str]]:
    """Split adjacent top-level or indented Markdown list items."""
    normalized = text.replace("\r\n", "\n")
    starts = [
        match.start()
        for match in re.finditer(r"(?m)^[ \t]*(?:[-*+]|\d+[.)])[ \t]+", normalized)
    ]
    headings = [offset for offset, _ in _headings(normalized)]
    items: list[tuple[int, str]] = []
    for index, start in enumerate(starts):
        ends = [offset for offset in (*starts[index + 1 :], *headings) if offset > start]
        end = min(ends, default=len(normalized))
        item = normalized[start:end]
        paragraph = re.search(r"\n[ \t]*\n(?![ \t])", item)
        if paragraph is not None:
            end = start + paragraph.start()
        items.append((start, normalized[start:end]))
    return items


def _shared_context(text: str) -> str:
    """Return a shared source citation without joining finding evidence."""
    normalized = text.replace("\r\n", "\n")
    starts = [start for start, _ in _list_items(normalized)]
    if not starts:
        starts = [offset for offset, _ in _headings(normalized)]
    preamble = clean(normalized[:min(starts)]) if starts else ""
    if location(preamble):
        return preamble

    citations = re.findall(r"([\w./-]+\.[a-zA-Z]\w*)[:#]L?(\d{1,4})\b", normalized)
    paths = {path for path, _ in citations}
    flask_paths = {
        path for path in paths
        if path in {"flask/app.py", "src/flask/app.py"} or path.endswith("/src/flask/app.py")
    }
    if paths - flask_paths - {"app.py"} or len(flask_paths - {"flask/app.py", "src/flask/app.py"}) > 1:
        return preamble
    for path, line in citations:
        if path in flask_paths and int(line) in STATIC_FOLDERS_LINES:
            return f"{preamble} {path}:{line}"
    return preamble


def finding_sections(text: str, context: str | None = None) -> list[tuple[str, str, list[str]]]:
    """Extract finding-local sections and their normalized blocks.

    Headed reviews use the heading through the next heading. Plain numbered
    reviews use one block per list item. The classifier never uses a
    later finding's text to classify an earlier finding.
    """
    normalized = text.replace("\r\n", "\n")
    context = _shared_context(normalized) if context is None else clean(context)
    headings = _headings(normalized)
    headed: list[tuple[str, str, list[str]]] = []
    explicit_ranges: list[tuple[int, int]] = []
    for index, (offset, label) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(normalized)
        category = _section_category(label)
        if category is not None and _explicit_finding_heading(label):
            raw = normalized[offset:end]
            headed.append((category, raw, blocks(raw)))
            explicit_ranges.append((offset, end))

    listed: list[tuple[str, str, list[str]]] = []
    seen = {(category, clean(raw)) for category, raw, _ in headed}
    for start, item in _list_items(normalized):
        if any(begin <= start < end for begin, end in explicit_ranges):
            continue
        evidence = clean(item)
        matches = [
            name for name in RULES if all(_checks(name, evidence, context).values())
        ]
        lead = clean(item.splitlines()[0])
        title = re.split(r":\s+", lead, maxsplit=1)[0]
        lead_category = _section_category(title) or _section_category(lead)
        if len(matches) > 1 or (matches and lead_category not in (None, matches[0])):
            continue
        category = matches[0] if matches else lead_category
        if category is not None and (category, evidence) not in seen:
            listed.append((category, item, [evidence]))
            seen.add((category, evidence))

    headed_blocks = {block for _, _, section_blocks in headed for block in section_blocks}
    item_ranges = [(start, start + len(item)) for start, item in _list_items(normalized)]
    heading_ranges = [
        (offset, headings[index + 1][0] if index + 1 < len(headings) else len(normalized))
        for index, (offset, _) in enumerate(headings)
    ]
    for block_start, block_end, block in _block_ranges(normalized):
        if any(block_start < end and block_end > start for start, end in (*item_ranges, *heading_ranges)):
            continue
        if block in headed_blocks:
            continue
        matches = [name for name in RULES if all(_checks(name, block, context).values())]
        if len(matches) == 1 and (matches[0], block) not in seen:
            listed.append((matches[0], block, [block]))
            seen.add((matches[0], block))
    return headed + listed


def _finding_location(evidence: str, context: str) -> bool:
    """Check a finding's source citation or combine a shared path with its local line."""
    if location(evidence):
        return True
    if not location(context):
        return False
    if has_any(context, (r"\badd_static_folders\b",)):
        return True
    if not has_any(context, (r"\bflask/app\.py\b",)):
        return False
    return any(int(line) in STATIC_FOLDERS_LINES for line in re.findall(r"\blines?\s+(\d{1,4})\b", evidence))


def _checks(category: str, evidence: str, context: str = "") -> dict[str, bool]:
    rule = RULES[category]
    return {
        "location": _finding_location(evidence, context),
        "trigger": has_any(evidence, rule["trigger"]),
        "impact": has_any(evidence, rule["impact"]),
    }


def defect_checks(text: str) -> dict[str, dict[str, object]]:
    """Check one complete finding section per defect without cross-section joins."""
    context = _shared_context(text)
    sections = finding_sections(text, context)
    output: dict[str, dict[str, object]] = {}
    for category in RULES:
        candidates = [(raw, section_blocks) for name, raw, section_blocks in sections if name == category]
        evaluated = [(raw, _checks(category, clean(raw), context)) for raw, _ in candidates]
        complete = [(raw, checks) for raw, checks in evaluated if all(checks.values())]
        if not complete:
            evidence = clean(candidates[0][0]) if candidates else ""
            checks = _checks(category, evidence, context) if evidence else {"location": False, "trigger": False, "impact": False}
            output[category] = {"met": False, "checks": checks, "evidence": evidence}
            continue
        raw, checks = complete[0]
        evidence = clean(raw)
        output[category] = {"met": all(checks.values()), "checks": checks, "evidence": evidence}
    return output


def unsupported(text: str) -> list[str]:
    """Reject unsupported claims while permitting the planted findings/extras."""
    finding_blocks = {block for _, _, section_blocks in finding_sections(text) for block in section_blocks}
    findings: list[str] = []
    for paragraph in blocks(text):
        if has_any(paragraph, UNSUPPORTED_MARKERS):
            findings.append(paragraph)
            continue
        if paragraph in finding_blocks:
            continue
        if not has_any(paragraph, (r"\b(problem|issue|bug|defect|risk|vulnerab|unsafe|wrong|fails?|cannot|should|missing)\b",)):
            continue
        if has_any(paragraph, META):
            continue
        if any(has_any(paragraph, pair) for pair in ALLOWED_EXTRA):
            continue
        if has_any(paragraph, (r"late[- ]binding|closure|max[_ -]?age|path traversal|send_file|safe_join|\.\.")):
            continue
        findings.append(paragraph)
    return findings


def git(project: Path, *args: str) -> str | None:
    """Read one value from the candidate project without changing it."""
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(project), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def fixture_checks(project: Path, expected_parent: str, expected_tree: str) -> dict[str, object]:
    """Verify the project is the pinned one-commit review fixture."""
    exists = project.is_dir()
    head_tree = git(project, "rev-parse", "HEAD^{tree}") if exists else ""
    parent = git(project, "rev-parse", "HEAD^") if exists else ""
    status = git(project, "status", "--porcelain", "--untracked-files=all") if exists else ""
    count = git(project, "rev-list", "--count", f"{expected_parent}..HEAD") if exists else ""
    return {
        "exists": exists,
        "head_tree": head_tree,
        "head_tree_ok": head_tree == expected_tree,
        "parent": parent,
        "parent_ok": parent == expected_parent,
        "one_commit_ahead": count == "1",
        "clean": status == "",
    }


def grade(project: Path, answer: str, expected_parent: str = EXPECTED_PARENT, expected_tree: str = EXPECTED_TREE) -> dict[str, object]:
    """Return a stable offline verdict for one review answer."""
    fixture = fixture_checks(project, expected_parent, expected_tree)
    checks = defect_checks(answer)
    unsupported_findings = unsupported(answer)
    success = bool(
        fixture["exists"]
        and fixture["head_tree_ok"]
        and fixture["parent_ok"]
        and fixture["one_commit_ahead"]
        and fixture["clean"]
        and bool(answer.strip())
        and all(item["met"] for item in checks.values())
        and not unsupported_findings
    )
    return {
        "schema": SCHEMA,
        "success": success,
        "fixture": fixture,
        "checks": {name: {"met": item["met"], "checks": item["checks"]} for name, item in checks.items()},
        "unsupported_findings": unsupported_findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--answer", required=True, type=Path)
    parser.add_argument("--parent", default=EXPECTED_PARENT)
    parser.add_argument("--tree", default=EXPECTED_TREE)
    args = parser.parse_args()
    try:
        answer = args.answer.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        answer = ""
    verdict = grade(args.project, answer, args.parent, args.tree)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
