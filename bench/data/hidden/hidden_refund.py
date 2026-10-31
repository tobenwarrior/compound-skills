import unittest
from decimal import Decimal

from invoicekit.money import Money


class HiddenRefundTests(unittest.TestCase):
    def test_negative_split_keeps_every_cent(self):
        parts = Money.of("-100.00").allocate([1, 1, 1])
        self.assertEqual(sum(part.amount for part in parts), Decimal("-100.00"))
        self.assertLessEqual(max(p.amount for p in parts) - min(p.amount for p in parts), Decimal("0.01"))

    def test_negative_uneven_ratios(self):
        self.assertEqual(sum(part.amount for part in Money.of("-0.05").allocate([70, 30])), Decimal("-0.05"))
        self.assertEqual(sum(part.amount for part in Money.of("-1000", "JPY").allocate([1, 2, 3])), Decimal("-1000"))

    def test_positive_splits_unchanged(self):
        self.assertEqual([part.amount for part in Money.of("100.00").allocate([1, 1, 1])],
                         [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])
        self.assertEqual([part.amount for part in Money.of("0.05").allocate([70, 30])], [Decimal("0.04"), Decimal("0.01")])
