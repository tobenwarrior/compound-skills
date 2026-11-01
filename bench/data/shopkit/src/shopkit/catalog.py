"""Products and their page URLs."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_MAX_SLUG = 50


def _product_slug(name: str) -> str:
    """URL slug for a product page."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    if len(slug) > _MAX_SLUG:
        slug = slug[:_MAX_SLUG].rsplit("-", 1)[0]
    return slug


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_cents: int

    @property
    def url(self) -> str:
        return f"/products/{_product_slug(self.name)}-{self.sku.lower()}"


def catalog_urls(products: list[Product]) -> dict[str, str]:
    return {product.sku: product.url for product in products}
