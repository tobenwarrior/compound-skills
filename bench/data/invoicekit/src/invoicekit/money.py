"""Money values in one currency, always rounded to that currency's minor unit."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Sequence

from .currency import Currency, get_currency


def quantize(amount: Decimal, currency: Currency) -> Decimal:
    """Round to the currency's minor unit with banker's rounding."""
    return amount.quantize(currency.minor_unit, rounding=ROUND_HALF_EVEN)


class CurrencyMismatch(ValueError):
    pass


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    @classmethod
    def of(cls, amount: object, code: str = "USD") -> Money:
        currency = get_currency(code)
        return cls(quantize(Decimal(str(amount)), currency), currency)

    @classmethod
    def zero(cls, code: str = "USD") -> Money:
        return cls.of(0, code)

    def _same(self, other: Money) -> None:
        if other.currency != self.currency:
            raise CurrencyMismatch(f"{self.currency.code} and {other.currency.code} cannot be combined")

    def __add__(self, other: Money) -> Money:
        self._same(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._same(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __mul__(self, factor: object) -> Money:
        return Money(quantize(self.amount * Decimal(str(factor)), self.currency), self.currency)

    __rmul__ = __mul__

    def __lt__(self, other: Money) -> bool:
        self._same(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._same(other)
        return self.amount <= other.amount

    def is_zero(self) -> bool:
        return self.amount == 0

    def allocate(self, ratios: Sequence[int]) -> list[Money]:
        """Split into parts proportional to ratios without losing or creating minor units.

        Leftover minor units go to the first parts, one each, so the parts always add up to self.
        """
        if not ratios or any(ratio < 0 for ratio in ratios) or sum(ratios) == 0:
            raise ValueError("ratios must be non-negative and not all zero")
        unit = self.currency.minor_unit
        units = int(self.amount / unit)
        total = sum(ratios)
        shares = [int(units * ratio / total) for ratio in ratios]
        remainder = units - sum(shares)
        for index in range(remainder):
            shares[index] += 1
        return [Money(Decimal(share) * unit, self.currency) for share in shares]

    def __str__(self) -> str:
        sign = "-" if self.amount < 0 else ""
        return f"{sign}{self.currency.symbol}{abs(self.amount):,.{self.currency.digits}f}"


def total(values: Sequence[Money], code: str = "USD") -> Money:
    result = Money.zero(values[0].currency.code if values else code)
    for value in values:
        result = result + value
    return result
