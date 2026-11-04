def _make_envelope(event: dict[str, object]) -> dict[str, object]:
    if not event.get("topic"):
        raise ValueError("publish topic required")
    if "payload" not in event:
        raise ValueError("publish payload required")
    return {
        "topic": event["topic"],
        "payload": event["payload"],
        "attempt": 1,
        "mode": "live",
    }


def publish(event: dict[str, object], transport: object) -> object:
    return transport.send(_make_envelope(event))
