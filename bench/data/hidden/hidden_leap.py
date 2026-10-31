import unittest
from datetime import date

from invoicekit import Money, prorate


class HiddenLeapTests(unittest.TestCase):
    def test_rest_of_leap_february(self):
        self.assertEqual(prorate(Money.of("29.00"), date(2024, 2, 15), date(2024, 2, 29)), Money.of("15.00"))

    def test_whole_leap_february_is_the_monthly_price(self):
        self.assertEqual(prorate(Money.of("29.00"), date(2024, 2, 1), date(2024, 2, 29)), Money.of("29.00"))
        self.assertEqual(prorate(Money.of("29.00"), date(2000, 2, 1), date(2000, 2, 29)), Money.of("29.00"))

    def test_century_years_follow_the_gregorian_rule(self):
        self.assertEqual(prorate(Money.of("28.00"), date(1900, 2, 1), date(1900, 2, 28)), Money.of("28.00"))
        self.assertEqual(prorate(Money.of("28.00"), date(2100, 2, 15), date(2100, 2, 28)), Money.of("14.00"))

    def test_other_months_unchanged(self):
        self.assertEqual(prorate(Money.of("30.00"), date(2024, 6, 16), date(2024, 6, 30)), Money.of("15.00"))
        self.assertEqual(prorate(Money.of("100.00"), date(2023, 2, 1), date(2023, 2, 14)), Money.of("50.00"))
