"""Discounts applied to an invoice line before tax."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .money import Money


@dataclass(frozen=True)
class Discount:
    """A percentage off (0-100), a fixed amount off, or both.

    The percentage applies first, then the fixed amount, and a discount never takes a line below zero.
    """

    percent: Decimal = Decimal(0)
    fixed: Money | None = None

    def __post_init__(self) -> None:
        if not Decimal(0) <= self.percent <= Decimal(100):
            raise ValueError("percent must be between 0 and 100")
        if self.fixed is not None and self.fixed.amount < 0:
            raise ValueError("fixed discount cannot be negative")

    def apply(self, amount: Money) -> Money:
        reduced = amount - amount * (self.percent / Decimal(100))
        if self.fixed is not None:
            reduced = reduced - self.fixed
        if reduced.amount < 0:
            return Money.zero(amount.currency.code)
        return reduced


NO_DISCOUNT = Discount()
