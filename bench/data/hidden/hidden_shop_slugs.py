import unittest

from shopkit.catalog import Product
from shopkit.search import Facet


class HiddenSlugTests(unittest.TestCase):
    def test_product_urls_stay_ascii(self):
        self.assertEqual(Product("A1", "Crème Brûlée Torch", 1).url, "/products/creme-brulee-torch-a1")
        self.assertEqual(Product("B2", "Mug (Large, 350 ml)", 1).url, "/products/mug-large-350-ml-b2")

    def test_long_product_names_are_cut_at_a_word(self):
        product = Product("C3", "Handmade Stoneware Coffee Mug With Speckled Glaze And Gift Box", 1)
        self.assertEqual(product.url, "/products/handmade-stoneware-coffee-mug-with-speckled-glaze-c3")

    def test_facet_keys_keep_letters_and_punctuation(self):
        self.assertEqual(Facet("Café", 1).key, "café")
        self.assertEqual(Facet("C++", 1).key, "c++")
        self.assertEqual(Facet("  Dark_Roast  ", 1).key, "dark-roast")
        self.assertEqual(Facet("Ünïcode Ünion", 1).key, "ünïcode-ünion")
