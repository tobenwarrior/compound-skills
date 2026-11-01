import unittest

from shopkit.errors import ConnectionLost, GatewayTimeout
from shopkit.payments import charge
from shopkit.webhooks import deliver


class Fake:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def _next(self, *args):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    charge = _next
    post = _next


class HiddenRetryTests(unittest.TestCase):
    def test_a_charge_is_not_retried_after_a_lost_connection(self):
        gateway, waits = Fake(ConnectionLost(), "ch_1"), []
        with self.assertRaises(ConnectionLost):
            charge(gateway, "tok", 500, "order-1", sleep=waits.append)
        self.assertEqual((gateway.calls, waits), (1, []))

    def test_a_charge_gives_up_after_three_timeouts(self):
        gateway, waits = Fake(GatewayTimeout(), GatewayTimeout(), GatewayTimeout(), "ch_2"), []
        with self.assertRaises(GatewayTimeout):
            charge(gateway, "tok", 500, "order-2", sleep=waits.append)
        self.assertEqual((gateway.calls, waits), (3, [0.5, 1.0]))

    def test_delivery_backs_off_up_to_five_seconds(self):
        client, waits = Fake(ConnectionLost(), GatewayTimeout(), ConnectionLost(), ConnectionLost(), 200), []
        self.assertEqual(deliver(client, "https://merchant.example/hook", {"id": 1}, sleep=waits.append), 200)
        self.assertEqual((client.calls, waits), (5, [1.0, 2.0, 4.0, 5.0]))

    def test_delivery_gives_up_after_five_attempts(self):
        client, waits = Fake(*[ConnectionLost() for _ in range(6)]), []
        with self.assertRaises(ConnectionLost):
            deliver(client, "https://merchant.example/hook", {"id": 2}, sleep=waits.append)
        self.assertEqual(client.calls, 5)
