import unittest

from dispatchkit.router import Router


class EncodedRouteRegressionTests(unittest.TestCase):
    def test_encoded_route_is_decoded_before_handler_lookup(self) -> None:
        router = Router()
        router.register("/hooks/acme/billing", lambda payload: f"received:{payload['id']}")

        result = router.dispatch("/hooks/acme%2Fbilling?source=partner", {"id": "42"})

        self.assertEqual(result.status, 200)
        self.assertEqual(result.body, "received:42")
