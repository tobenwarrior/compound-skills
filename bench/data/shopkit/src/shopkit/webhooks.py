"""Order webhooks delivered to merchant endpoints."""
from __future__ import annotations

import time
from typing import Callable

from .errors import ConnectionLost, GatewayTimeout

_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_MAX_DELAY = 5.0


def _retry_delivery(post: Callable[[], int], sleep: Callable[[float], None]) -> int:
    """Post a webhook, backing off between attempts."""
    delay = _BASE_DELAY
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return post()
        except (ConnectionLost, GatewayTimeout):
            if attempt == _MAX_ATTEMPTS:
                raise
            sleep(delay)
            delay = min(delay * 2, _MAX_DELAY)
    raise AssertionError("unreachable")


def deliver(client, url: str, payload: dict, *, sleep: Callable[[float], None] = time.sleep) -> int:
    """Deliver an order event and return the merchant's HTTP status."""
    return _retry_delivery(lambda: client.post(url, payload), sleep)
