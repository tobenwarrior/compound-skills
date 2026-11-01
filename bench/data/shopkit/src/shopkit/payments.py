"""Card charges through the payment gateway."""
from __future__ import annotations

import time
from typing import Callable

from .errors import GatewayTimeout

_ATTEMPTS = 3
_DELAYS = (0.5, 1.0)


def _retry_charge(send: Callable[[], str], sleep: Callable[[float], None]) -> str:
    """Send a charge, trying again when the gateway times out."""
    for attempt in range(_ATTEMPTS):
        try:
            return send()
        except GatewayTimeout:
            if attempt == _ATTEMPTS - 1:
                raise
            sleep(_DELAYS[attempt])
    raise AssertionError("unreachable")


def charge(gateway, card_token: str, amount_cents: int, idempotency_key: str, *,
           sleep: Callable[[float], None] = time.sleep) -> str:
    """Charge a card and return the gateway's charge id."""
    if amount_cents <= 0:
        raise ValueError("amount must be positive")
    return _retry_charge(lambda: gateway.charge(card_token, amount_cents, idempotency_key), sleep)
