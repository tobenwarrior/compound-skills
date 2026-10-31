import unittest
from decimal import Decimal

from invoicekit.invoice import Invoice, Line
from invoicekit.money import Money
from invoicekit.tax import net_from_gross, tax_for


class HiddenRefactorBehaviourTests(unittest.TestCase):
    def test_tax_rounds_half_cents_up(self):
        self.assertEqual(tax_for(Money.of("10.50"), "reduced"), Money.of("0.53"))
        self.assertEqual(tax_for(Money.of("1000", "JPY"), "standard"), Money.of("83", "JPY"))
        self.assertEqual(tax_for(Money.of("30.30"), "reduced"), Money.of("1.52"))

    def test_line_amounts_round_half_even(self):
        self.assertEqual(Line("Half", Decimal("0.5"), Money.of("0.25")).gross, Money.of("0.12"))
        self.assertEqual(Line("Half", Decimal("0.5"), Money.of("0.35")).gross, Money.of("0.18"))

    def test_invoice_totals_with_half_cents(self):
        invoice = Invoice(number="INV-2024-00010", customer="Acme Ltd")
        invoice.add(Line("Books", Decimal("1"), Money.of("10.50"), tax_code="reduced"))
        invoice.add(Line("Samples", Decimal("0.5"), Money.of("0.25"), tax_code="exempt"))
        self.assertEqual(invoice.subtotal, Money.of("10.62"))
        self.assertEqual(invoice.tax_total, Money.of("0.53"))
        self.assertEqual(invoice.total, Money.of("11.15"))

    def test_net_from_gross_unchanged(self):
        self.assertEqual(net_from_gross(Money.of("108.25"), "standard"), Money.of("100.00"))
        self.assertEqual(net_from_gross(Money.of("10.00"), "standard"), Money.of("9.24"))
