"""Parsing money amounts written as text."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def parse_money(text: str, *, rounding: str = ROUND_HALF_UP, accounting: bool = True) -> int:
    """Amount text to cents, ignoring "$" and thousands commas; with accounting, "(12.00)" is -1200."""
    cleaned = text.strip().replace(",", "").replace("$", "")
    negative = accounting and cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    cents = int((Decimal(cleaned) * 100).quantize(Decimal("1"), rounding=rounding))
    return -cents if negative else cents
