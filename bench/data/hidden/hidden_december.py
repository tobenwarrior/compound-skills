import unittest
from datetime import date

from invoicekit import due_date


class HiddenDecemberTests(unittest.TestCase):
    def test_net_30_eom_issued_in_december(self):
        self.assertEqual(due_date(date(2024, 12, 10), "NET 30 EOM"), date(2025, 1, 30))

    def test_eom_in_december(self):
        self.assertEqual(due_date(date(2024, 12, 5), "EOM"), date(2024, 12, 31))
        self.assertEqual(due_date(date(2023, 12, 1), "EOM"), date(2023, 12, 31))
        self.assertEqual(due_date(date(2024, 12, 31), "NET 15 EOM"), date(2025, 1, 15))

    def test_other_months_unchanged(self):
        self.assertEqual(due_date(date(2024, 3, 10), "NET 15 EOM"), date(2024, 4, 15))
        self.assertEqual(due_date(date(2024, 11, 20), "NET 30 EOM"), date(2024, 12, 30))
        self.assertEqual(due_date(date(2024, 2, 10), "EOM"), date(2024, 2, 29))
