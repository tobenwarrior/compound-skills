"""Calling again after a transient failure."""
from __future__ import annotations

from typing import Callable, Sequence, TypeVar

T = TypeVar("T")


def retry(call: Callable[[], T], *, retry_on: tuple[type[BaseException], ...], delays: Sequence[float],
          sleep: Callable[[float], None]) -> T:
    """Call; after a failure in retry_on, wait the next delay and call again. There are len(delays) + 1 attempts."""
    for delay in delays:
        try:
            return call()
        except retry_on:
            sleep(delay)
    return call()
