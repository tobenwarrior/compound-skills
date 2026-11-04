from .packaging import package_event


def publish(event: dict[str, object], transport: object) -> object:
    if not event.get("topic"):
        raise ValueError("publish topic required")
    if "payload" not in event:
        raise ValueError("publish payload required")
    return transport.send(package_event(event["topic"], event["payload"], 1, "live"))
