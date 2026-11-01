"""Facets shown beside search results, with keys used in filter URLs."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .text import slugify


@dataclass(frozen=True)
class Facet:
    label: str
    count: int

    @property
    def key(self) -> str:
        return slugify(self.label, ascii_only=False)


def facets(labels: list[str]) -> list[Facet]:
    counts = Counter(labels)
    return [Facet(label, count) for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def filter_url(facet: Facet, field: str = "brand") -> str:
    return f"/search?{field}={facet.key}"
