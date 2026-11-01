"""Validation of amounts sent to the public refunds API."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN

from .money import parse_money

# Plain or comma-grouped numbers only: no currency symbols and no accounting parentheses.
_AMOUNT = re.compile(r"^-?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$")


class InvalidAmount(ValueError):
    pass


def refund_amount(payload: dict) -> int:
    """The refund in cents from an API payload such as {"amount": "12.50"}."""
    text = str(payload["amount"]).strip()
    if not _AMOUNT.match(text):
        raise InvalidAmount(payload["amount"])
    cents = parse_money(text, rounding=ROUND_HALF_EVEN, accounting=False)
    if cents <= 0:
        raise InvalidAmount(payload["amount"])
    return cents
