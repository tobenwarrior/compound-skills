import contextlib
import csv
import io
import json
import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal

from invoicekit.cli import main
from invoicekit.export import CSV_HEADER, to_csv, to_dict, to_json
from invoicekit.invoice import Invoice, Line
from invoicekit.money import Money
from invoicekit.numbering import Sequence, parse


def sample() -> Invoice:
    invoice = Invoice(number="INV-2024-00007", customer="Acme Ltd")
    invoice.add(Line("Consulting, March", Decimal("2"), Money.of("150.00")))
    invoice.add(Line('Books "A" and "B"', Decimal("1"), Money.of("20.00"), tax_code="reduced"))
    return invoice


class ExportTests(unittest.TestCase):
    def test_csv_rows_survive_commas_and_quotes(self):
        rows = list(csv.reader(io.StringIO(to_csv([sample()]))))
        self.assertEqual(rows[0], CSV_HEADER)
        self.assertEqual(rows[1][2], "Consulting, March")
        self.assertEqual(rows[2][2], 'Books "A" and "B"')
        self.assertEqual([len(row) for row in rows], [8, 8, 8])

    def test_json(self):
        invoice = sample()
        invoice.issue(date(2024, 3, 1))
        data = json.loads(to_json(invoice))
        self.assertEqual(data, to_dict(invoice))
        self.assertEqual(data["total"], "345.75")
        self.assertEqual(data["due_on"], "2024-03-31")


class NumberingTests(unittest.TestCase):
    def test_sequence_restarts_each_year(self):
        sequence = Sequence()
        self.assertEqual(sequence.next(2024), "INV-2024-00001")
        self.assertEqual(sequence.next(2024), "INV-2024-00002")
        self.assertEqual(sequence.peek(2024), "INV-2024-00003")
        self.assertEqual(sequence.next(2025), "INV-2025-00001")

    def test_parse(self):
        self.assertEqual(parse("CR-2024-00042"), ("CR", 2024, 42))
        with self.assertRaises(ValueError):
            parse("INV-2024-ABC")


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(list(args)), 0)
        return out.getvalue()

    def test_due(self):
        self.assertEqual(self.run_cli("due", "2024-03-15", "NET 30").strip(), "2024-04-14")

    def test_total(self):
        document = {"number": "INV-2024-00009", "customer": "Acme Ltd",
                    "lines": [{"description": "Consulting", "quantity": 2, "unit_price": "150.00"},
                              {"description": "Books", "quantity": 1, "unit_price": "20.00", "tax_code": "reduced",
                               "discount_percent": 10}]}
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "invoice.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(document, handle)
            output = self.run_cli("total", path)
        self.assertIn("Subtotal: $318.00", output)
        self.assertIn("Tax:      $25.65", output)
        self.assertIn("Total:    $343.65", output)


if __name__ == "__main__":
    unittest.main()
