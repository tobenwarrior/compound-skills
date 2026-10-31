"""Sales tax rates and tax computation for invoice lines."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .currency import Currency
from .money import Money

RATES: dict[str, Decimal | None] = {
    "standard": Decimal("0.0825"),
    "reduced": Decimal("0.05"),
    "zero": Decimal("0"),
    "exempt": None,
}


class UnknownTaxCode(ValueError):
    pass


def rate_for(code: str) -> Decimal | None:
    try:
        return RATES[code]
    except KeyError:
        raise UnknownTaxCode(f"unknown tax code {code!r}") from None


def _round_tax(amount: Decimal, currency: Currency) -> Decimal:
    """Round a tax amount to the currency's minor unit."""
    return amount.quantize(currency.minor_unit, rounding=ROUND_HALF_UP)


def tax_for(net: Money, code: str) -> Money:
    """Tax owed on a net (tax-exclusive) amount."""
    rate = rate_for(code)
    if rate is None:
        return Money.zero(net.currency.code)
    return Money(_round_tax(net.amount * rate, net.currency), net.currency)


def net_from_gross(gross: Money, code: str) -> Money:
    """The net amount contained in a tax-inclusive price."""
    rate = rate_for(code)
    if not rate:
        return gross
    return Money(_round_tax(gross.amount / (1 + rate), gross.currency), gross.currency)
