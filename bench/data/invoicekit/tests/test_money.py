import unittest
from decimal import Decimal

from invoicekit.currency import UnknownCurrency, get_currency
from invoicekit.money import CurrencyMismatch, Money, quantize, total


class MoneyTests(unittest.TestCase):
    def test_of_rounds_to_the_minor_unit_with_bankers_rounding(self):
        self.assertEqual(Money.of("0.125").amount, Decimal("0.12"))
        self.assertEqual(Money.of("0.135").amount, Decimal("0.14"))
        self.assertEqual(Money.of("1234.5", "JPY").amount, Decimal("1234"))
        self.assertEqual(Money.of("1.0005", "KWD").amount, Decimal("1.000"))

    def test_quantize_uses_the_currency_digits(self):
        self.assertEqual(quantize(Decimal("2.345"), get_currency("USD")), Decimal("2.34"))
        self.assertEqual(quantize(Decimal("2.3456"), get_currency("KWD")), Decimal("2.346"))

    def test_arithmetic(self):
        self.assertEqual(Money.of("10.10") + Money.of("0.95"), Money.of("11.05"))
        self.assertEqual(Money.of("10.10") - Money.of("0.95"), Money.of("9.15"))
        self.assertEqual(-Money.of("3.50"), Money.of("-3.50"))
        self.assertEqual(Money.of("19.99") * 3, Money.of("59.97"))
        self.assertEqual(Money.of("10.00") * Decimal("0.333"), Money.of("3.33"))
        self.assertEqual(2 * Money.of("1.25"), Money.of("2.50"))

    def test_currencies_do_not_mix(self):
        with self.assertRaises(CurrencyMismatch):
            Money.of(1, "USD") + Money.of(1, "EUR")
        with self.assertRaises(CurrencyMismatch):
            Money.of(1, "USD") < Money.of(1, "GBP")

    def test_unknown_currency(self):
        with self.assertRaises(UnknownCurrency):
            Money.of(1, "XXX")

    def test_allocate_spreads_leftover_cents_over_the_first_parts(self):
        parts = Money.of("100.00").allocate([1, 1, 1])
        self.assertEqual([part.amount for part in parts], [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])
        self.assertEqual(total(parts), Money.of("100.00"))

    def test_allocate_by_uneven_ratios(self):
        parts = Money.of("0.05").allocate([70, 30])
        self.assertEqual([part.amount for part in parts], [Decimal("0.04"), Decimal("0.01")])
        parts = Money.of("1000", "JPY").allocate([1, 2, 3])
        self.assertEqual(sum(part.amount for part in parts), Decimal("1000"))

    def test_allocate_rejects_bad_ratios(self):
        for ratios in ([], [0, 0], [1, -1]):
            with self.assertRaises(ValueError):
                Money.of("10").allocate(ratios)

    def test_str(self):
        self.assertEqual(str(Money.of("1234.5")), "$1,234.50")
        self.assertEqual(str(Money.of("-3", "EUR")), "-€3.00")
        self.assertEqual(str(Money.of("1500", "JPY")), "¥1,500")

    def test_comparisons_and_zero(self):
        self.assertTrue(Money.of("1.00") < Money.of("1.01"))
        self.assertTrue(Money.of("1.00") <= Money.of("1.00"))
        self.assertTrue(Money.zero("EUR").is_zero())


if __name__ == "__main__":
    unittest.main()
