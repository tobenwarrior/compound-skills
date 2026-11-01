import unittest

from shopkit.errors import ConnectionLost, GatewayTimeout
from shopkit.payments import charge
from shopkit.webhooks import deliver


class FakeGateway:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def charge(self, card_token, amount_cents, idempotency_key):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def post(self, url, payload):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def no_wait(seconds):
    pass


class PaymentTests(unittest.TestCase):
    def test_charge_returns_the_charge_id(self):
        self.assertEqual(charge(FakeGateway("ch_1"), "tok", 500, "order-1", sleep=no_wait), "ch_1")

    def test_charge_tries_again_after_a_timeout(self):
        gateway = FakeGateway(GatewayTimeout(), "ch_2")
        self.assertEqual(charge(gateway, "tok", 500, "order-2", sleep=no_wait), "ch_2")
        self.assertEqual(gateway.calls, 2)

    def test_charge_rejects_amounts_that_are_not_positive(self):
        with self.assertRaises(ValueError):
            charge(FakeGateway(), "tok", 0, "order-3", sleep=no_wait)


class WebhookTests(unittest.TestCase):
    def test_deliver_returns_the_status(self):
        self.assertEqual(deliver(FakeClient(200), "https://merchant.example/hook", {"id": 1}, sleep=no_wait), 200)

    def test_deliver_tries_again_after_a_lost_connection(self):
        client = FakeClient(ConnectionLost(), 204)
        self.assertEqual(deliver(client, "https://merchant.example/hook", {"id": 2}, sleep=no_wait), 204)
        self.assertEqual(client.calls, 2)
