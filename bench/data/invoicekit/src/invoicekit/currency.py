"""Currencies and their minor units."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Currency:
    code: str
    symbol: str
    digits: int

    @property
    def minor_unit(self) -> Decimal:
        """The smallest amount the currency can express, such as 0.01 for USD."""
        return Decimal(1).scaleb(-self.digits)


_CURRENCIES = {
    "USD": Currency("USD", "$", 2),
    "EUR": Currency("EUR", "€", 2),
    "GBP": Currency("GBP", "£", 2),
    "JPY": Currency("JPY", "¥", 0),
    "KWD": Currency("KWD", "KD", 3),
}


class UnknownCurrency(ValueError):
    pass


def get_currency(code: str) -> Currency:
    try:
        return _CURRENCIES[code.upper()]
    except KeyError:
        raise UnknownCurrency(f"unknown currency {code!r}") from None


def supported_codes() -> list[str]:
    return sorted(_CURRENCIES)
