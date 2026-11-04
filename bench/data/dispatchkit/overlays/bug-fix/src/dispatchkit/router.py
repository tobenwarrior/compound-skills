from dataclasses import dataclass
from typing import Callable
from urllib.parse import unquote


@dataclass(frozen=True)
class DispatchResult:
    status: int
    body: str


class Router:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict[str, str]], str]] = {}

    def register(self, path: str, handler: Callable[[dict[str, str]], str]) -> None:
        self._handlers[path] = handler

    def dispatch(self, raw_path: str, payload: dict[str, str]) -> DispatchResult:
        path = unquote(raw_path.split("?", 1)[0])
        handler = self._handlers.get(path)
        if handler is None:
            return DispatchResult(404, "not found")
        return DispatchResult(200, handler(payload))
