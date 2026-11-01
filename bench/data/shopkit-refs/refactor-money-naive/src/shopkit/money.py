"""Parsing money amounts written as text."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def parse_money(text: str) -> int:
    """Amount text to cents: "$1,234.50" is 123450 and "(12.00)" is -1200."""
    cleaned = text.strip().replace(",", "").replace("$", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    try:
        cents = int((Decimal(cleaned) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except InvalidOperation:
        raise ValueError(f"not an amount: {text!r}") from None
    return -cents if negative else cents
