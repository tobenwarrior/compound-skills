"""Bounded, conservative lexical outlines for languages without AST support.

This is deliberately a heuristic (not an AST or LSP): it recognizes common
source-level declarations while masking ordinary comments and string literals.
It is intended for repository maps, not parsing, indexing, or refactoring.
"""

from __future__ import annotations

import re

SUPPORTED_LANGUAGES = frozenset({
    "go", "rust", "java", "c", "cpp", "csharp", "ruby", "php", "swift", "kotlin",
})
MAX_SOURCE_CHARS = 256 * 1024
MAX_LINE_CHARS = 8192
MAX_SYMBOLS = 512

_IDENTIFIER = r"[A-Za-z_$][\w$]*"
_TYPE_PATTERNS: dict[str, re.Pattern[str]] = {
    "go": re.compile(r"^\s*type\s+(" + _IDENTIFIER + r")\b"),
    "rust": re.compile(r"^\s*(?:(?:pub(?:\s*\([^)]*\))?|unsafe|extern|async)\s+)*(struct|enum|trait|union|type)\s+(" + _IDENTIFIER + r")\b"),
    "java": re.compile(r"^\s*(?:(?:public|protected|private|abstract|static|final|strictfp|sealed|non-sealed)\s+)*(?:@interface|(class|interface|enum|record))\s+(" + _IDENTIFIER + r")\b"),
    "c": re.compile(r"^\s*(?:(?:typedef|static|extern)\s+)*(struct|union|enum)\s+(" + _IDENTIFIER + r")\b"),
    "cpp": re.compile(r"^\s*(?:(?:typedef|static|extern|final|sealed)\s+)*(class|struct|union|enum)\s+(?:(?:class|struct)\s+)?(" + _IDENTIFIER + r")\b"),
    "csharp": re.compile(r"^\s*(?:(?:public|protected|private|internal|abstract|static|sealed|partial|readonly|ref|new)\s+)*(?:(record)(?:\s+(?:class|struct))?|(class|interface|struct|enum|delegate))\s+(" + _IDENTIFIER + r")\b"),
    "ruby": re.compile(r"^\s*(?:class|module)\s+([A-Z][\w]*(?:::[A-Z][\w]*)*)\b"),
    "php": re.compile(r"^\s*(?:(?:abstract|final|readonly)\s+)*(class|interface|trait|enum)\s+(" + _IDENTIFIER + r")\b"),
    "swift": re.compile(r"^\s*(?:(?:public|private|internal|fileprivate|open|final|indirect|actor)\s+)*(class|struct|enum|protocol|actor|typealias)\s+(?!(?:[a-z]+\s+)*(?:func|var|subscript)\b)(" + _IDENTIFIER + r")\b"),
    "kotlin": re.compile(r"^\s*(?:(?:public|private|protected|internal|open|final|abstract|sealed|data|value|expect|actual|annotation|enum)\s+)*(class|interface|object)\s+(" + _IDENTIFIER + r")\b"),
}

_FUNCTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "go": re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(" + _IDENTIFIER + r")(?:\s*\[[^\]\n]*\])?\s*\("),
    "rust": re.compile(r"^\s*(?:(?:pub(?:\s*\([^)]*\))?|unsafe|async|const|extern)\s+)*fn\s+([A-Za-z_]\w*)\s*(?:<[^;{}]*>)?\s*\("),
    "ruby": re.compile(r"^\s*def\s+(?:(?:self)\.)?([A-Za-z_]\w*[!?=]?)"),
    "php": re.compile(r"^\s*(?:(?:public|protected|private|static|final|abstract)\s+)*function\s+(?:&\s*)?([A-Za-z_]\w*)\s*\("),
    "swift": re.compile(r"^\s*(?:(?:public|private|internal|fileprivate|open|static|class|override|mutating|nonmutating|final|dynamic|discardableResult)\s+)*func\s+([A-Za-z_]\w*)\s*\("),
    "kotlin": re.compile(r"^\s*(?:(?:public|private|protected|internal|open|final|abstract|override|inline|infix|operator|suspend|tailrec|external|expect|actual)\s+)*fun\s+(?:<[^>]+>\s*)?(?:[\w$.<>?]+\.)?([A-Za-z_]\w*)\s*\("),
}

# The C-family and JVM method rule requires an explicit return type, avoiding
# most ordinary calls. Constructors are added separately only for known types.
_METHOD_PATTERN = re.compile(
    r"^\s*(?:(?:public|protected|private|internal|static|final|abstract|virtual|override|async|extern|unsafe|inline|constexpr|consteval|constinit|friend|virtual|explicit|synchronized|native|default|sealed|new|partial|readonly|volatile|register|typedef|inline|extern|auto)\s+)*"
    r"(?:<[^;{}]+>\s+)?"
    r"(?:[\w:$~*&<>.,?\[\]]+\s+)+"
    r"((?:[A-Za-z_$][\w$]*::)*(?:~?[A-Za-z_$][\w$]*))\s*\("
)
_CONSTRUCTOR_PATTERN = re.compile(
    r"^\s*(?:(?:public|protected|private|internal|static|explicit|inline|constexpr|async)\s+)*"
    r"(~?[A-Za-z_$][\w$]*)\s*\("
)
_CONTROL_NAMES = {
    "if", "for", "while", "switch", "catch", "return", "throw", "new", "delete",
    "sizeof", "typeof", "instanceof", "do", "else", "case", "assert", "lock",
    "using", "yield", "await", "super", "this", "where", "when", "match",
}
_COMMENT_STYLES = {
    "go": ("//", "/*"), "rust": ("//", "/*"), "java": ("//", "/*"),
    "c": ("//", "/*"), "cpp": ("//", "/*"), "csharp": ("//", "/*"),
    "ruby": ("#",), "php": ("//", "/*", "#"), "swift": ("//", "/*"),
    "kotlin": ("//", "/*"),
}


def split_lines(text: str) -> list[str]:
    """Split on \\n, \\r\\n, and \\r only, as editors, compilers, and Git count lines.

    str.splitlines() also breaks on form feeds and Unicode separators, which
    would shift every later line number.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return lines[:-1] if lines[-1] == "" else lines


def _mask_comments_and_strings(source: str, language: str) -> str:
    """Blank comments/literals while preserving offsets and line numbers."""
    chars = list(source)
    line_comments = _COMMENT_STYLES[language]
    block_depth = 0
    quote = ""
    triple = False
    escaped = False
    ruby_doc = False
    i = 0
    length = len(source)

    def blank(start: int, end: int) -> None:
        for pos in range(start, end):
            if chars[pos] != "\n":
                chars[pos] = " "

    while i < length:
        if ruby_doc:
            if source[i] == "\n":
                i += 1
                continue
            line_end = source.find("\n", i)
            if line_end < 0:
                line_end = length
            if source[i:line_end].strip() == "=end":
                blank(i, line_end)
                ruby_doc = False
            else:
                blank(i, line_end)
            i = line_end
            continue

        if block_depth:
            if language in {"rust", "swift"} and source.startswith("/*", i):
                block_depth += 1
                blank(i, i + 2)
                i += 2
            elif source.startswith("*/", i):
                block_depth -= 1
                blank(i, i + 2)
                i += 2
            else:
                if source[i] != "\n":
                    chars[i] = " "
                i += 1
            continue

        if quote:
            delimiter = quote * (3 if triple else 1)
            if escaped:
                if source[i] != "\n":
                    chars[i] = " "
                escaped = False
                i += 1
            elif source[i] == "\\":
                chars[i] = " "
                escaped = True
                i += 1
            elif source.startswith(delimiter, i):
                blank(i, i + len(delimiter))
                i += len(delimiter)
                quote = ""
                triple = False
            else:
                if source[i] != "\n":
                    chars[i] = " "
                i += 1
            continue

        # C++ raw strings and Rust raw/byte-raw strings.
        raw_start = None
        raw_end = None
        if language == "cpp" and source.startswith('R"', i):
            open_paren = source.find("(", i + 2, min(length, i + 20))
            if open_paren >= 0:
                delimiter = source[i + 2:open_paren]
                if not any(char.isspace() or char in "()\\" for char in delimiter):
                    raw_start = open_paren + 1
                    raw_end = ")" + delimiter + '"'
        elif language == "rust":
            match = re.match(r"(?:b)?r(#+)?\"", source[i:i + 20])
            if match:
                raw_start = i + match.end()
                raw_end = '"' + (match.group(1) or "")
        if raw_start is not None and raw_end is not None:
            blank(i, raw_start)
            close = source.find(raw_end, raw_start)
            if close < 0:
                blank(raw_start, length)
                return "".join(chars)
            blank(raw_start, close + len(raw_end))
            i = close + len(raw_end)
            continue

        if language == "ruby" and source[i] == "=" and (i == 0 or source[i - 1] == "\n"):
            line_end = source.find("\n", i)
            if line_end < 0:
                line_end = length
            if source[i:line_end].strip() == "=begin":
                blank(i, line_end)
                ruby_doc = True
                i = line_end
                continue

        if source.startswith("/*", i):
            block_depth = 1
            blank(i, i + 2)
            i += 2
            continue
        line_marker = next((marker for marker in line_comments if source.startswith(marker, i)), None)
        if line_marker:
            line_end = source.find("\n", i)
            if line_end < 0:
                line_end = length
            blank(i, line_end)
            i = line_end
            continue

        if source.startswith('"""', i) and language in {"java", "swift", "kotlin", "csharp"}:
            quote, triple = '"', True
            blank(i, i + 3)
            i += 3
            continue
        if source[i] in {'"', "'", "`"}:
            char = source[i]
            if char == "`" and language not in {"go", "rust", "cpp", "csharp"}:
                i += 1
                continue
            # Rust and C-family apostrophes are char literals only if closed;
            # Rust lifetimes such as 'a are therefore left as code.
            if char == "'" and language in {"rust", "c", "cpp", "java", "csharp", "kotlin"}:
                end = i + 1
                if end < length and source[end] == "\\":
                    end += 2
                else:
                    end += 1
                if end >= length or source[end] != "'":
                    i += 1
                    continue
            quote = char
            triple = False
            chars[i] = " "
            i += 1
            continue
        i += 1
    return "".join(chars)


def _type_declaration(language: str, line: str) -> tuple[str, str] | None:
    match = _TYPE_PATTERNS[language].search(line)
    if not match:
        return None
    if language in {"java", "c", "cpp", "php", "swift", "kotlin", "rust"}:
        kind, name = match.groups()

    elif language == "csharp":
        kind = match.group(1) or match.group(2)
        name = match.group(3)
    elif language == "ruby":
        kind_match = re.search(r"\b(class|module)\b", line)
        kind, name = (kind_match.group(1), match.group(1)) if kind_match else ("class", match.group(1))
    else:  # Go
        kind, name = "type", match.group(1)
    if language == "java" and "@interface" in line:
        kind = "interface"
    if language == "kotlin" and kind == "class" and "enum" in line[:match.start(1)].split():
        kind = "enum"
    return kind.lower(), name


def _function_name(language: str, line: str, type_names: set[str]) -> str | None:
    pattern = _FUNCTION_PATTERNS.get(language)
    if pattern:
        match = pattern.search(line)
        if match:
            return match.group(1)
        return None
    if re.match(r"^\s*(?:return|throw|yield|case)\b", line):
        return None
    match = _METHOD_PATTERN.search(line)
    if match:
        name = match.group(1).split("::")[-1].lstrip("~")
        if name.lower() not in _CONTROL_NAMES:
            return name
    constructor = _CONSTRUCTOR_PATTERN.search(line)
    if constructor and ("{" in line or "=>" in line):
        name = constructor.group(1).lstrip("~")
        if name in type_names:
            return name
    return None


def outline(text: str, language: str, max_symbols: int = 512) -> tuple[list[dict], str | None]:
    """Extract likely declarations as ``{"name", "kind", "line"}`` records.

    Line numbers are 1-based. Only ``SUPPORTED_LANGUAGES`` are recognized.
    Input is capped at 256 KiB of characters (not bytes), candidate lines at
    8192 characters, and output at 512 symbols regardless of the requested limit.
    The optional note reports
    unsupported input, skipped oversized lines, or truncation/limits.
    """
    if not isinstance(text, str):
        return [], "Input must be text."
    language = language.lower() if isinstance(language, str) else ""
    if language not in SUPPORTED_LANGUAGES:
        return [], f"Unsupported language: {language or 'unknown'}."
    try:
        requested_limit = max(0, int(max_symbols))
    except (TypeError, ValueError, OverflowError):
        requested_limit = MAX_SYMBOLS
    limit = min(requested_limit, MAX_SYMBOLS)

    notes: list[str] = []
    if len(text) > MAX_SOURCE_CHARS:
        text = text[:MAX_SOURCE_CHARS]
        notes.append(f"Input truncated at {MAX_SOURCE_CHARS} characters.")
    masked = _mask_comments_and_strings(text, language)
    lines = split_lines(masked)
    declarations: list[dict] = []
    type_names: set[str] = set()
    candidates: list[tuple[int, str, str]] = []

    for line_no, line in enumerate(lines, 1):
        if len(line) > MAX_LINE_CHARS:
            notes.append(f"Skipped line {line_no} longer than {MAX_LINE_CHARS} characters.")
            continue
        type_decl = _type_declaration(language, line)
        if type_decl:
            kind, name = type_decl
            type_names.add(name)
            candidates.append((line_no, name, kind))
    for line_no, line in enumerate(lines, 1):
        if len(line) > MAX_LINE_CHARS:
            continue
        name = _function_name(language, line, type_names)
        if name and name.lower() not in _CONTROL_NAMES:
            candidates.append((line_no, name, "function"))

    seen: set[tuple[int, str, str]] = set()
    for line_no, name, kind in sorted(candidates, key=lambda item: (item[0], item[1], item[2])):
        key = (line_no, name, kind)
        if key in seen:
            continue
        seen.add(key)
        if len(declarations) >= limit:
            notes.append(f"Symbol limit reached ({limit}).")
            break
        declarations.append({"name": name, "kind": kind, "line": line_no})

    return declarations, "; ".join(dict.fromkeys(notes)) or None
