"""Command line: `python3 -m invoicekit total invoice.json` and `... due 2024-03-15 "NET 30"`."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal

from .discount import Discount
from .invoice import Invoice, Line
from .money import Money
from .terms import due_date


def load(path: str) -> Invoice:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    invoice = Invoice(number=data["number"], customer=data["customer"], currency=data.get("currency", "USD"),
                      terms=data.get("terms", "NET 30"))
    for item in data["lines"]:
        discount = Discount(percent=Decimal(str(item.get("discount_percent", 0))))
        invoice.add(Line(item["description"], Decimal(str(item["quantity"])),
                         Money.of(item["unit_price"], invoice.currency), item.get("tax_code", "standard"), discount))
    return invoice


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="invoicekit")
    commands = parser.add_subparsers(dest="command", required=True)
    total = commands.add_parser("total", help="print an invoice's totals")
    total.add_argument("path")
    due = commands.add_parser("due", help="print the due date for an issue date and terms")
    due.add_argument("issued")
    due.add_argument("terms")
    args = parser.parse_args(argv)
    if args.command == "total":
        invoice = load(args.path)
        print(f"Subtotal: {invoice.subtotal}")
        print(f"Tax:      {invoice.tax_total}")
        print(f"Total:    {invoice.total}")
    else:
        print(due_date(date.fromisoformat(args.issued), args.terms).isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())
