"""Supplier price lists imported from CSV."""
from __future__ import annotations

import csv
import io
from decimal import ROUND_HALF_UP, Decimal


def _parse_price(text: str) -> int:
    """Supplier price to cents."""
    cleaned = text.strip().replace(",", "").replace("$", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    cents = int((Decimal(cleaned) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return -cents if negative else cents


def read_price_list(text: str) -> dict[str, int]:
    """Map each SKU in a supplier CSV (columns sku, price) to its price in cents."""
    return {row["sku"]: _parse_price(row["price"]) for row in csv.DictReader(io.StringIO(text))}
