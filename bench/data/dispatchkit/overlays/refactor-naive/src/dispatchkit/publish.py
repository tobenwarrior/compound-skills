from .packaging import package_event


def publish(event: dict[str, object], transport: object) -> object:
    return transport.send(package_event(event))
