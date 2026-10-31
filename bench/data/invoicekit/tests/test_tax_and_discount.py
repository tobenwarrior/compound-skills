import unittest
from decimal import Decimal

from invoicekit.discount import Discount
from invoicekit.money import Money
from invoicekit.tax import UnknownTaxCode, net_from_gross, rate_for, tax_for


class TaxTests(unittest.TestCase):
    def test_standard_and_reduced_rates(self):
        self.assertEqual(tax_for(Money.of("100.00"), "standard"), Money.of("8.25"))
        self.assertEqual(tax_for(Money.of("19.99"), "reduced"), Money.of("1.00"))
        self.assertEqual(tax_for(Money.of("12.34"), "standard"), Money.of("1.02"))

    def test_zero_rated_and_exempt(self):
        self.assertEqual(tax_for(Money.of("50.00"), "zero"), Money.of("0.00"))
        self.assertEqual(tax_for(Money.of("50.00"), "exempt"), Money.of("0.00"))
        self.assertIsNone(rate_for("exempt"))

    def test_unknown_code(self):
        with self.assertRaises(UnknownTaxCode):
            tax_for(Money.of("1.00"), "luxury")

    def test_net_from_tax_inclusive_price(self):
        self.assertEqual(net_from_gross(Money.of("108.25"), "standard"), Money.of("100.00"))
        self.assertEqual(net_from_gross(Money.of("21.00"), "reduced"), Money.of("20.00"))
        self.assertEqual(net_from_gross(Money.of("9.99"), "exempt"), Money.of("9.99"))

    def test_other_currencies(self):
        self.assertEqual(tax_for(Money.of("1210", "JPY"), "standard"), Money.of("100", "JPY"))


class DiscountTests(unittest.TestCase):
    def test_percent_then_fixed(self):
        discount = Discount(percent=Decimal("10"), fixed=Money.of("5.00"))
        self.assertEqual(discount.apply(Money.of("100.00")), Money.of("85.00"))

    def test_never_below_zero(self):
        self.assertEqual(Discount(fixed=Money.of("50.00")).apply(Money.of("20.00")), Money.of("0.00"))

    def test_no_discount(self):
        self.assertEqual(Discount().apply(Money.of("12.34")), Money.of("12.34"))

    def test_validation(self):
        with self.assertRaises(ValueError):
            Discount(percent=Decimal("120"))
        with self.assertRaises(ValueError):
            Discount(fixed=Money.of("-1"))


if __name__ == "__main__":
    unittest.main()
