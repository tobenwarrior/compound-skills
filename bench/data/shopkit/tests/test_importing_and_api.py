import unittest

from shopkit.api import InvalidAmount, refund_amount
from shopkit.importing import read_price_list


class ImportTests(unittest.TestCase):
    def test_read_price_list(self):
        text = 'sku,price\nA1,12.50\nB2,"1,234.00"\n'
        self.assertEqual(read_price_list(text), {"A1": 1250, "B2": 123400})


class ApiTests(unittest.TestCase):
    def test_refund_amount(self):
        self.assertEqual(refund_amount({"amount": "12.50"}), 1250)
        self.assertEqual(refund_amount({"amount": "1,234.50"}), 123450)

    def test_refund_amount_must_be_positive(self):
        with self.assertRaises(InvalidAmount):
            refund_amount({"amount": "0"})

    def test_refund_amount_must_be_a_number(self):
        with self.assertRaises(InvalidAmount):
            refund_amount({"amount": "twelve"})
