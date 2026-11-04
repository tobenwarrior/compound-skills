from .packaging import package_event


def replay(record: dict[str, object], transport: object) -> object:
    if not record.get("topic"):
        raise ValueError("replay topic required")
    if "payload" not in record:
        raise ValueError("replay payload required")
    return transport.send(package_event(record["topic"], record["payload"], record.get("attempt", 0), "replay"))
