"""Exercise host-only Flask SERVER_NAME without opening a server socket."""

import pytest
import werkzeug.serving


@pytest.mark.parametrize(
    ("port", "expected_port"),
    [pytest.param(None, 5000, id="default-port"), pytest.param(0, 0, id="explicit-zero")],
)
def test_host_only_server_name(app, monkeypatch, port, expected_port):
    received = []

    def record(hostname, port, *args, **kwargs):
        received.append((hostname, port))

    monkeypatch.setattr(werkzeug.serving, "run_simple", record)
    app.config["SERVER_NAME"] = "example.test"
    app.run(port=port)
    assert received == [("example.test", expected_port)]
