"""Order webhooks delivered to merchant endpoints."""
from __future__ import annotations

import time
from typing import Callable

from .errors import ConnectionLost, GatewayTimeout
from .retrying import retry

_RETRY_ON = (ConnectionLost, GatewayTimeout)
_DELAYS = (1.0, 2.0, 4.0, 5.0)


def deliver(client, url: str, payload: dict, *, sleep: Callable[[float], None] = time.sleep) -> int:
    """Deliver an order event and return the merchant's HTTP status."""
    return retry(lambda: client.post(url, payload), retry_on=_RETRY_ON, delays=_DELAYS, sleep=sleep)
