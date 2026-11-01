"""Validation of amounts sent to the public refunds API."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, Decimal

_AMOUNT = re.compile(r"^-?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$")


class InvalidAmount(ValueError):
    pass


def _parse_amount(value: str) -> int:
    """API amount to cents."""
    text = value.strip()
    if not _AMOUNT.match(text):
        raise InvalidAmount(value)
    return int((Decimal(text.replace(",", "")) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def refund_amount(payload: dict) -> int:
    """The refund in cents from an API payload such as {"amount": "12.50"}."""
    cents = _parse_amount(str(payload["amount"]))
    if cents <= 0:
        raise InvalidAmount(payload["amount"])
    return cents
