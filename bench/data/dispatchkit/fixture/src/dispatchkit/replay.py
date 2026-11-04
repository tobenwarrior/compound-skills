def _replay_envelope(record: dict[str, object]) -> dict[str, object]:
    if not record.get("topic"):
        raise ValueError("replay topic required")
    if "payload" not in record:
        raise ValueError("replay payload required")
    return {
        "topic": record["topic"],
        "payload": record["payload"],
        "attempt": record.get("attempt", 0),
        "mode": "replay",
    }


def replay(record: dict[str, object], transport: object) -> object:
    return transport.send(_replay_envelope(record))
