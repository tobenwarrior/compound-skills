def package_event(event: dict[str, object]) -> dict[str, object]:
    if not event.get("topic"):
        raise ValueError("topic required")
    if "payload" not in event:
        raise ValueError("payload required")
    return {"topic": event["topic"], "payload": event["payload"], "attempt": 1, "mode": "live"}
