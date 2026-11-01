"""Errors raised by the payment gateway and merchant endpoints."""


class GatewayTimeout(Exception):
    """The remote side did not answer in time; the request was not processed."""


class ConnectionLost(Exception):
    """The connection dropped after the request was sent."""
