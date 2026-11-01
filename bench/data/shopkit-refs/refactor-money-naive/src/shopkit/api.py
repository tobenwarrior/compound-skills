"""Validation of amounts sent to the public refunds API."""
from __future__ import annotations

from .money import parse_money


class InvalidAmount(ValueError):
    pass


def refund_amount(payload: dict) -> int:
    """The refund in cents from an API payload such as {"amount": "12.50"}."""
    try:
        cents = parse_money(str(payload["amount"]))
    except ValueError:
        raise InvalidAmount(payload["amount"]) from None
    if cents <= 0:
        raise InvalidAmount(payload["amount"])
    return cents
