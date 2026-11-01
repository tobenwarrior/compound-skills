"""Order webhooks delivered to merchant endpoints."""
from __future__ import annotations

import time
from typing import Callable

from .retrying import retry


def deliver(client, url: str, payload: dict, *, sleep: Callable[[float], None] = time.sleep) -> int:
    """Deliver an order event and return the merchant's HTTP status."""
    return retry(lambda: client.post(url, payload), sleep)
