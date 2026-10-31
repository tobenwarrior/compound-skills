"""AST-normalized digests of a project's src/ and tests/, shared by the exec shim and the harness."""
import ast
import hashlib
from pathlib import Path


def digest(repo: Path, area: str) -> str:
    h = hashlib.sha256()
    base = repo / area
    if not base.exists():
        return "missing"
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts or not path.is_file():
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
