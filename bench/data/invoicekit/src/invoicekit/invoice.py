"""Invoices: lines, totals, payment terms and status."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum

from .currency import Currency
from .discount import NO_DISCOUNT, Discount
from .money import Money
from .tax import tax_for
from .terms import due_date


def _round_money(amount: Decimal, currency: Currency) -> Decimal:
    """Round a line amount to the currency's minor unit."""
    return amount.quantize(currency.minor_unit, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class Line:
    description: str
    quantity: Decimal
    unit_price: Money
    tax_code: str = "standard"
    discount: Discount = NO_DISCOUNT

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

    @property
    def gross(self) -> Money:
        """Quantity times unit price, before discount and tax."""
        amount = _round_money(self.unit_price.amount * self.quantity, self.unit_price.currency)
        return Money(amount, self.unit_price.currency)

    @property
    def net(self) -> Money:
        """Gross after discount, before tax."""
        return self.discount.apply(self.gross)

    @property
    def tax(self) -> Money:
        return tax_for(self.net, self.tax_code)


class Status(Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


_TRANSITIONS = {
    Status.DRAFT: {Status.ISSUED, Status.VOID},
    Status.ISSUED: {Status.PAID, Status.VOID},
    Status.PAID: set(),
    Status.VOID: set(),
}


class InvalidTransition(RuntimeError):
    pass


@dataclass
class Invoice:
    number: str
    customer: str
    currency: str = "USD"
    terms: str = "NET 30"
    lines: list[Line] = field(default_factory=list)
    issued_on: date | None = None
    status: Status = Status.DRAFT

    def add(self, line: Line) -> None:
        if self.status is not Status.DRAFT:
            raise InvalidTransition("lines can only be added to a draft invoice")
        if line.unit_price.currency.code != self.currency:
            raise ValueError(f"line currency {line.unit_price.currency.code} does not match {self.currency}")
        self.lines.append(line)

    def _move(self, target: Status) -> None:
        if target not in _TRANSITIONS[self.status]:
            raise InvalidTransition(f"cannot move from {self.status.value} to {target.value}")
        self.status = target

    def issue(self, on: date) -> None:
        if not self.lines:
            raise InvalidTransition("cannot issue an empty invoice")
        self._move(Status.ISSUED)
        self.issued_on = on

    def mark_paid(self) -> None:
        self._move(Status.PAID)

    def void(self) -> None:
        self._move(Status.VOID)

    @property
    def due_on(self) -> date | None:
        return due_date(self.issued_on, self.terms) if self.issued_on else None

    def _sum(self, values: list[Money]) -> Money:
        result = Money.zero(self.currency)
        for value in values:
            result = result + value
        return result

    @property
    def subtotal(self) -> Money:
        """Sum of line amounts after discounts, before tax."""
        return self._sum([line.net for line in self.lines])

    @property
    def discount_total(self) -> Money:
        return self._sum([line.gross - line.net for line in self.lines])

    @property
    def tax_total(self) -> Money:
        return self._sum([line.tax for line in self.lines])

    @property
    def total(self) -> Money:
        return self.subtotal + self.tax_total
