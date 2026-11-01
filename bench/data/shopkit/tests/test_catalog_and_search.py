import unittest

from shopkit.catalog import Product, catalog_urls
from shopkit.search import Facet, facets, filter_url


class CatalogTests(unittest.TestCase):
    def test_product_url_uses_the_name_and_sku(self):
        self.assertEqual(Product("MUG-1", "Blue Mug", 1200).url, "/products/blue-mug-mug-1")

    def test_catalog_urls(self):
        products = [Product("T1", "Green Tea", 800), Product("T2", "Black Tea", 900)]
        self.assertEqual(catalog_urls(products), {"T1": "/products/green-tea-t1", "T2": "/products/black-tea-t2"})


class SearchTests(unittest.TestCase):
    def test_facets_are_counted_and_sorted(self):
        result = facets(["Acme", "Zest", "Acme", "Dark Roast"])
        self.assertEqual([(facet.label, facet.count) for facet in result], [("Acme", 2), ("Dark Roast", 1), ("Zest", 1)])

    def test_filter_url_uses_the_facet_key(self):
        self.assertEqual(filter_url(Facet("Dark Roast", 3)), "/search?brand=dark-roast")
