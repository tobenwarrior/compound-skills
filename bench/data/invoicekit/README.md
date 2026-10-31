# invoicekit

Money, sales tax, discounts, payment terms, proration and invoices for a small billing service.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m invoicekit due 2024-03-15 "NET 30"
```

Amounts are `decimal.Decimal` values rounded to the currency's minor unit. Python 3.11+, no dependencies.
