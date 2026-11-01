"""Products and their page URLs."""
from __future__ import annotations

from dataclasses import dataclass

from .text import slugify

@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_cents: int

    @property
    def url(self) -> str:
        return f"/products/{slugify(self.name)}-{self.sku.lower()}"

def catalog_urls(products: list[Product]) -> dict[str, str]:
    return {product.sku: product.url for product in products}
