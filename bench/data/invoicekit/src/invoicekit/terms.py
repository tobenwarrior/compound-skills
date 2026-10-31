"""Payment terms such as "NET 30", "EOM" and "NET 15 EOM"."""
from __future__ import annotations

from datetime import date, timedelta


class InvalidTerms(ValueError):
    pass


def end_of_month(day: date) -> date:
    """The last day of the month containing day."""
    first_of_next = date(day.year, day.month % 12 + 1, 1)
    return first_of_next - timedelta(days=1)


def due_date(issued: date, terms: str) -> date:
    """When an invoice issued on `issued` is due.

    - "NET n": n days after the issue date.
    - "EOM": the last day of the issue month.
    - "NET n EOM": n days after the last day of the issue month.
    - "DUE ON RECEIPT": the issue date.
    """
    words = terms.upper().split()
    if words == ["DUE", "ON", "RECEIPT"]:
        return issued
    if words == ["EOM"]:
        return end_of_month(issued)
    if len(words) in (2, 3) and words[0] == "NET" and words[1].isdigit():
        days = int(words[1])
        if len(words) == 3:
            if words[2] != "EOM":
                raise InvalidTerms(f"unsupported terms {terms!r}")
            return end_of_month(issued) + timedelta(days=days)
        return issued + timedelta(days=days)
    raise InvalidTerms(f"unsupported terms {terms!r}")
