"""Turning names and labels into keys for URLs."""
from __future__ import annotations

import re
import unicodedata


def slugify(text: str, *, ascii_only: bool = True, max_length: int | None = None) -> str:
    """Lowercase URL key.

    With ascii_only, accents are stripped and every run of other characters becomes one hyphen; otherwise letters and
    punctuation stay and only runs of spaces and underscores become hyphens. max_length cuts at the last hyphen.
    """
    if ascii_only:
        plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    else:
        slug = re.sub(r"[\s_]+", "-", text.strip().lower())
    if max_length is not None and len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0]
    return slug
