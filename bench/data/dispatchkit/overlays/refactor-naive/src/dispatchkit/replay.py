from .packaging import package_event


def replay(record: dict[str, object], transport: object) -> object:
    return transport.send(package_event(record))
