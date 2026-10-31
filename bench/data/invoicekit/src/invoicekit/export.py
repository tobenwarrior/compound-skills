"""Exporting invoices as CSV rows and JSON documents."""
from __future__ import annotations

import csv
import io
import json

from .invoice import Invoice

CSV_HEADER = ["invoice", "customer", "description", "quantity", "unit_price", "net", "tax", "currency"]


def to_csv(invoices: list[Invoice]) -> str:
    """One row per invoice line, with a header row."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for invoice in invoices:
        for line in invoice.lines:
            writer.writerow([
                invoice.number,
                invoice.customer,
                line.description,
                str(line.quantity),
                str(line.unit_price.amount),
                str(line.net.amount),
                str(line.tax.amount),
                invoice.currency,
            ])
    return buffer.getvalue()


def to_dict(invoice: Invoice) -> dict:
    return {
        "number": invoice.number,
        "customer": invoice.customer,
        "currency": invoice.currency,
        "status": invoice.status.value,
        "issued_on": invoice.issued_on.isoformat() if invoice.issued_on else None,
        "due_on": invoice.due_on.isoformat() if invoice.due_on else None,
        "lines": [
            {
                "description": line.description,
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price.amount),
                "tax_code": line.tax_code,
                "net": str(line.net.amount),
                "tax": str(line.tax.amount),
            }
            for line in invoice.lines
        ],
        "subtotal": str(invoice.subtotal.amount),
        "tax_total": str(invoice.tax_total.amount),
        "total": str(invoice.total.amount),
    }


def to_json(invoice: Invoice) -> str:
    return json.dumps(to_dict(invoice), indent=2, ensure_ascii=False)
