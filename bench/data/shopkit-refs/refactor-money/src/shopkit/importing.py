"""Supplier price lists imported from CSV."""
from __future__ import annotations

import csv
import io

from .money import parse_money


def read_price_list(text: str) -> dict[str, int]:
    """Map each SKU in a supplier CSV (columns sku, price) to its price in cents."""
    return {row["sku"]: parse_money(row["price"]) for row in csv.DictReader(io.StringIO(text))}
