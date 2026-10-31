import unittest
from datetime import date

from invoicekit.money import Money
from invoicekit.proration import days_in_month, prorate
from invoicekit.terms import InvalidTerms, due_date, end_of_month


class TermsTests(unittest.TestCase):
    def test_net_days(self):
        self.assertEqual(due_date(date(2024, 3, 15), "NET 30"), date(2024, 4, 14))
        self.assertEqual(due_date(date(2024, 3, 15), "net 7"), date(2024, 3, 22))

    def test_end_of_month(self):
        self.assertEqual(end_of_month(date(2024, 4, 5)), date(2024, 4, 30))
        self.assertEqual(end_of_month(date(2023, 2, 1)), date(2023, 2, 28))
        self.assertEqual(due_date(date(2024, 2, 10), "EOM"), date(2024, 2, 29))

    def test_net_days_after_end_of_month(self):
        self.assertEqual(due_date(date(2024, 3, 10), "NET 15 EOM"), date(2024, 4, 15))
        self.assertEqual(due_date(date(2024, 6, 30), "NET 30 EOM"), date(2024, 7, 30))

    def test_due_on_receipt(self):
        self.assertEqual(due_date(date(2024, 5, 2), "Due on receipt"), date(2024, 5, 2))

    def test_invalid_terms(self):
        for terms in ("NET X", "NET 30 BOM", "2/10 NET 30", ""):
            with self.assertRaises(InvalidTerms):
                due_date(date(2024, 1, 1), terms)


class ProrationTests(unittest.TestCase):
    def test_full_month_is_the_monthly_price(self):
        self.assertEqual(prorate(Money.of("30.00"), date(2024, 6, 1), date(2024, 6, 30)), Money.of("30.00"))

    def test_partial_month_counts_both_ends(self):
        self.assertEqual(prorate(Money.of("30.00"), date(2024, 6, 16), date(2024, 6, 30)), Money.of("15.00"))
        self.assertEqual(prorate(Money.of("31.00"), date(2024, 7, 9), date(2024, 7, 9)), Money.of("1.00"))
        self.assertEqual(prorate(Money.of("100.00"), date(2023, 2, 1), date(2023, 2, 14)), Money.of("50.00"))

    def test_validation(self):
        with self.assertRaises(ValueError):
            prorate(Money.of("30.00"), date(2024, 6, 20), date(2024, 7, 5))
        with self.assertRaises(ValueError):
            prorate(Money.of("30.00"), date(2024, 6, 20), date(2024, 6, 5))

    def test_days_in_month(self):
        self.assertEqual(days_in_month(2023, 2), 28)
        self.assertEqual(days_in_month(2023, 4), 30)
        self.assertEqual(days_in_month(2023, 12), 31)
        with self.assertRaises(ValueError):
            days_in_month(2023, 13)


if __name__ == "__main__":
    unittest.main()
