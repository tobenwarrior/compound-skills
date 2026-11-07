"""Digests of a project's Python source and tests for benchmark observations."""
import ast
import hashlib
from pathlib import Path


def digest(repo: Path, area: str, *, exact: bool = False) -> str:
    h = hashlib.sha256()
    base = repo / area
    if exact and base.is_symlink():
        raise OSError("cannot observe a symlinked source tree")
    if not base.exists():
        return "missing"
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if exact and path.is_symlink():
            raise OSError("cannot observe a symlinked source file")
        if not path.is_file():
            continue
        if exact:
            name = str(path.relative_to(repo)).encode("utf-8", "surrogateescape")
            h.update(name + b"\0" + hashlib.sha256(path.read_bytes()).digest())
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        try:
            normal = ast.dump(ast.parse(text))
        except SyntaxError:
            normal = text
        h.update(str(path.relative_to(repo)).encode() + b"\0" + normal.encode() + b"\0")
    return h.hexdigest()[:16]
