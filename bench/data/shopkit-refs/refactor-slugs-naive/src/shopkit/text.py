"""Turning names and labels into keys for URLs."""
from __future__ import annotations

import re
import unicodedata

_MAX_SLUG = 50


def slugify(text: str) -> str:
    """Lowercase ASCII URL key: accents stripped, other characters hyphenated, at most 50 characters."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    if len(slug) > _MAX_SLUG:
        slug = slug[:_MAX_SLUG].rsplit("-", 1)[0]
    return slug
