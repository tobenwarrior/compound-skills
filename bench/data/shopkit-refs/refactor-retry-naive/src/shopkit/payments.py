"""Card charges through the payment gateway."""
from __future__ import annotations

import time
from typing import Callable

from .retrying import retry


def charge(gateway, card_token: str, amount_cents: int, idempotency_key: str, *,
           sleep: Callable[[float], None] = time.sleep) -> str:
    """Charge a card and return the gateway's charge id."""
    if amount_cents <= 0:
        raise ValueError("amount must be positive")
    return retry(lambda: gateway.charge(card_token, amount_cents, idempotency_key), sleep)
