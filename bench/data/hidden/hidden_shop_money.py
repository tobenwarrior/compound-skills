import unittest

from shopkit.api import InvalidAmount, refund_amount
from shopkit.importing import read_price_list


class HiddenMoneyTests(unittest.TestCase):
    def test_supplier_prices_accept_symbols_and_accounting_negatives(self):
        text = 'sku,price\nA1,"$1,234.50"\nB2,(12.00)\nC3,0.125\nD4,12.345\n'
        self.assertEqual(read_price_list(text), {"A1": 123450, "B2": -1200, "C3": 13, "D4": 1235})

    def test_api_amounts_round_half_to_even(self):
        self.assertEqual(refund_amount({"amount": "0.125"}), 12)
        self.assertEqual(refund_amount({"amount": "12.345"}), 1234)

    def test_api_rejects_symbols_and_malformed_grouping(self):
        for value in ("$5.00", "(5.00)", "1,23.00", "5.00 USD"):
            with self.subTest(value=value), self.assertRaises(InvalidAmount):
                refund_amount({"amount": value})
