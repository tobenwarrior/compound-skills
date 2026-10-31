"""Prorating monthly subscription prices for partial months."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from .money import Money

_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def days_in_month(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    return _DAYS_IN_MONTH[month - 1]


def prorate(monthly: Money, start: date, end: date) -> Money:
    """The share of a monthly price for the days from start through end, inclusive.

    Both dates must fall in the same calendar month.
    """
    if (start.year, start.month) != (end.year, end.month):
        raise ValueError("start and end must be in the same month")
    if end < start:
        raise ValueError("end must not be before start")
    used = (end - start).days + 1
    month_days = days_in_month(start.year, start.month)
    if used == month_days:
        return monthly
    return monthly * (Decimal(used) / Decimal(month_days))
