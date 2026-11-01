"""Calling again after a transient failure."""
from __future__ import annotations

from typing import Callable, TypeVar

from .errors import ConnectionLost, GatewayTimeout

T = TypeVar("T")

_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_MAX_DELAY = 5.0


def retry(call: Callable[[], T], sleep: Callable[[float], None]) -> T:
    """Call up to five times, backing off between attempts."""
    delay = _BASE_DELAY
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return call()
        except (ConnectionLost, GatewayTimeout):
            if attempt == _MAX_ATTEMPTS:
                raise
            sleep(delay)
            delay = min(delay * 2, _MAX_DELAY)
    raise AssertionError("unreachable")
