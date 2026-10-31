"""Invoice numbers such as INV-2024-00042, restarting each year."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Sequence:
    prefix: str = "INV"
    width: int = 5
    _last: dict[int, int] = field(default_factory=dict)

    def next(self, year: int) -> str:
        number = self._last.get(year, 0) + 1
        self._last[year] = number
        return f"{self.prefix}-{year}-{number:0{self.width}d}"

    def peek(self, year: int) -> str:
        return f"{self.prefix}-{year}-{self._last.get(year, 0) + 1:0{self.width}d}"


def parse(number: str) -> tuple[str, int, int]:
    """Split an invoice number into prefix, year and sequence number."""
    prefix, year, sequence = number.rsplit("-", 2)
    if not (year.isdigit() and sequence.isdigit()):
        raise ValueError(f"not an invoice number: {number!r}")
    return prefix, int(year), int(sequence)
