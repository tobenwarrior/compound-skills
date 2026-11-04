import unittest

from dispatchkit.publish import publish
from dispatchkit.replay import replay
from dispatchkit.router import Router


class CaptureTransport:
    def __init__(self) -> None:
        self.envelopes: list[dict[str, object]] = []

    def send(self, envelope: dict[str, object]) -> dict[str, object]:
        self.envelopes.append(envelope)
        return envelope


class DispatchKitTests(unittest.TestCase):
    def test_router_matches_plain_paths_and_reports_misses(self) -> None:
        router = Router()
        router.register("/hooks/acme/billing", lambda payload: f"received:{payload['id']}")

        self.assertEqual(router.dispatch("/hooks/acme/billing", {"id": "1"}).body, "received:1")
        self.assertEqual(router.dispatch("/hooks/acme/unknown", {"id": "1"}).status, 404)

    def test_publish_and_replay_send_topic_and_payload(self) -> None:
        transport = CaptureTransport()
        publish({"topic": "orders", "payload": {"id": "1"}}, transport)
        replay({"topic": "orders", "payload": {"id": "1"}}, transport)

        self.assertEqual(transport.envelopes[0]["topic"], "orders")
        self.assertEqual(transport.envelopes[0]["payload"], {"id": "1"})
        self.assertEqual(transport.envelopes[1]["topic"], "orders")
        self.assertEqual(transport.envelopes[1]["payload"], {"id": "1"})
