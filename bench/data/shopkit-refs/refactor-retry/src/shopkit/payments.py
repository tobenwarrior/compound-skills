"""Card charges through the payment gateway."""
from __future__ import annotations

import time
from typing import Callable

from .errors import GatewayTimeout
from .retrying import retry

# Only a timeout is safe to retry: after a lost connection the charge may already have gone through.
_RETRY_ON = (GatewayTimeout,)
_DELAYS = (0.5, 1.0)


def charge(gateway, card_token: str, amount_cents: int, idempotency_key: str, *,
           sleep: Callable[[float], None] = time.sleep) -> str:
    """Charge a card and return the gateway's charge id."""
    if amount_cents <= 0:
        raise ValueError("amount must be positive")
    return retry(lambda: gateway.charge(card_token, amount_cents, idempotency_key), retry_on=_RETRY_ON, delays=_DELAYS,
                 sleep=sleep)
