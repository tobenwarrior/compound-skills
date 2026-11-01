"""Facets shown beside search results, with keys used in filter URLs."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


def _facet_key(label: str) -> str:
    """Key for a facet value in filter URLs such as ?brand=dark-roast."""
    return re.sub(r"[\s_]+", "-", label.strip().lower())


@dataclass(frozen=True)
class Facet:
    label: str
    count: int

    @property
    def key(self) -> str:
        return _facet_key(self.label)


def facets(labels: list[str]) -> list[Facet]:
    counts = Counter(labels)
    return [Facet(label, count) for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def filter_url(facet: Facet, field: str = "brand") -> str:
    return f"/search?{field}={facet.key}"
