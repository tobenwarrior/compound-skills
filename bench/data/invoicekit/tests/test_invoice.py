import unittest
from datetime import date
from decimal import Decimal

from invoicekit.discount import Discount
from invoicekit.invoice import InvalidTransition, Invoice, Line, Status
from invoicekit.money import Money


def sample() -> Invoice:
    invoice = Invoice(number="INV-2024-00001", customer="Acme Ltd")
    invoice.add(Line("Consulting, March", Decimal("12"), Money.of("150.00")))
    invoice.add(Line("Books", Decimal("3"), Money.of("19.99"), tax_code="reduced"))
    invoice.add(Line("Support plan", Decimal("1"), Money.of("400.00"), discount=Discount(percent=Decimal("25"))))
    return invoice


class LineTests(unittest.TestCase):
    def test_gross_net_and_tax(self):
        line = Line("Widget", Decimal("2.5"), Money.of("3.99"), discount=Discount(percent=Decimal("10")))
        self.assertEqual(line.gross, Money.of("9.98"))
        self.assertEqual(line.net, Money.of("8.98"))
        self.assertEqual(line.tax, Money.of("0.74"))

    def test_quantity_must_be_positive(self):
        with self.assertRaises(ValueError):
            Line("Nothing", Decimal("0"), Money.of("1.00"))


class InvoiceTotalsTests(unittest.TestCase):
    def test_totals(self):
        invoice = sample()
        self.assertEqual(invoice.subtotal, Money.of("2159.97"))
        self.assertEqual(invoice.discount_total, Money.of("100.00"))
        self.assertEqual(invoice.tax_total, Money.of("176.25"))
        self.assertEqual(invoice.total, Money.of("2336.22"))

    def test_currency_must_match(self):
        invoice = Invoice(number="INV-2024-00002", customer="Acme Ltd", currency="EUR")
        with self.assertRaises(ValueError):
            invoice.add(Line("Widget", Decimal("1"), Money.of("1.00", "USD")))

    def test_empty_invoice_totals_are_zero(self):
        invoice = Invoice(number="INV-2024-00003", customer="Acme Ltd", currency="GBP")
        self.assertTrue(invoice.total.is_zero())
        self.assertEqual(invoice.total.currency.code, "GBP")


class InvoiceStatusTests(unittest.TestCase):
    def test_issue_pay(self):
        invoice = sample()
        invoice.issue(date(2024, 3, 15))
        self.assertIs(invoice.status, Status.ISSUED)
        self.assertEqual(invoice.due_on, date(2024, 4, 14))
        invoice.mark_paid()
        self.assertIs(invoice.status, Status.PAID)

    def test_cannot_issue_empty_or_pay_draft(self):
        with self.assertRaises(InvalidTransition):
            Invoice(number="INV-2024-00004", customer="Acme Ltd").issue(date(2024, 3, 1))
        with self.assertRaises(InvalidTransition):
            sample().mark_paid()

    def test_cannot_add_lines_after_issue(self):
        invoice = sample()
        invoice.issue(date(2024, 3, 1))
        with self.assertRaises(InvalidTransition):
            invoice.add(Line("Late", Decimal("1"), Money.of("1.00")))

    def test_void_is_final(self):
        invoice = sample()
        invoice.void()
        with self.assertRaises(InvalidTransition):
            invoice.issue(date(2024, 3, 1))


if __name__ == "__main__":
    unittest.main()
