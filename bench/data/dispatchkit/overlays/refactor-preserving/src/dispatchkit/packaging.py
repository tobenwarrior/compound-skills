def package_event(topic: object, payload: object, attempt: int, mode: str) -> dict[str, object]:
    return {"topic": topic, "payload": payload, "attempt": attempt, "mode": mode}
