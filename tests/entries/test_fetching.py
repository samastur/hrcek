"""Fetching an image from an address somebody typed.

The address is hostile until proved otherwise: it may point at the
machine we are running on, at something else on the home network, or at
a cloud metadata endpoint that hands out credentials. These tests are
the security boundary — read them before changing `fetching.py`.
"""

import io

import pytest
from PIL import Image

from hrcek.core.errors import HrcekError
from hrcek.entries import fetching


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 15), (9, 9, 9)).save(buffer, format="PNG")
    return buffer.getvalue()


# --- addresses we must refuse ------------------------------------------


@pytest.mark.parametrize(
    "address",
    [
        "file:///etc/passwd",
        "ftp://example.com/a.png",
        "gopher://example.com/a.png",
        "data:image/png;base64,iVBORw0KGgo=",
        "javascript:alert(1)",
        "//example.com/a.png",
        "not a url at all",
        "",
    ],
)
def test_only_http_and_https_are_allowed(address):
    with pytest.raises(HrcekError) as raised:
        fetching.fetch(address)
    assert raised.value.error_code.code == "HRC-IMAGE-0004"


@pytest.mark.parametrize(
    "resolved",
    [
        "127.0.0.1",  # loopback
        "::1",  # loopback, v6
        "10.0.0.5",  # private
        "192.168.1.10",  # private
        "172.16.0.3",  # private
        "169.254.169.254",  # cloud metadata
        "fd00::1",  # unique local, v6
        "fe80::1",  # link local, v6
        "0.0.0.0",  # noqa: S104 — unspecified, refused not bound
        "224.0.0.1",  # multicast
        "100.64.0.1",  # carrier-grade NAT
    ],
)
def test_addresses_that_resolve_inward_are_refused(resolved, monkeypatch):
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: [resolved])
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://looks-innocent.example.com/a.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0005"


def test_a_public_address_is_allowed(monkeypatch):
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: ["93.184.216.34"])
    monkeypatch.setattr(fetching, "_read", lambda *a, **k: (200, {}, _png()))
    assert fetching.fetch("https://example.com/a.png") == _png()


def test_one_public_and_one_private_answer_is_still_refused(monkeypatch):
    # A host that answers with both must not be reachable through the
    # public one: the connection could still land on the private address.
    monkeypatch.setattr(
        fetching, "_resolve", lambda host, port: ["93.184.216.34", "127.0.0.1"]
    )
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://split-horizon.example.com/a.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0005"


# --- redirects ---------------------------------------------------------


def test_a_redirect_to_a_private_address_is_refused(monkeypatch):
    monkeypatch.setattr(
        fetching,
        "_resolve",
        lambda host, port: ["127.0.0.1"] if "internal" in host else ["93.184.216.34"],
    )
    monkeypatch.setattr(
        fetching,
        "_read",
        lambda *a, **k: (302, {"location": "https://internal.example.com/x"}, b""),
    )
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://example.com/a.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0005"


def test_endless_redirects_stop(monkeypatch):
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: ["93.184.216.34"])
    monkeypatch.setattr(
        fetching,
        "_read",
        lambda *a, **k: (302, {"location": "https://example.com/again"}, b""),
    )
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://example.com/a.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0006"


def test_a_redirect_to_another_scheme_is_refused(monkeypatch):
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: ["93.184.216.34"])
    monkeypatch.setattr(
        fetching,
        "_read",
        lambda *a, **k: (302, {"location": "file:///etc/passwd"}, b""),
    )
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://example.com/a.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0004"


# --- the response itself -----------------------------------------------


def test_a_failure_status_is_reported(monkeypatch):
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: ["93.184.216.34"])
    monkeypatch.setattr(fetching, "_read", lambda *a, **k: (404, {}, b"nope"))
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://example.com/a.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0006"


def test_a_body_over_the_cap_is_refused(monkeypatch):
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: ["93.184.216.34"])

    def _too_much(*args, **kwargs):
        raise fetching.TooMuchDataError

    monkeypatch.setattr(fetching, "_read", _too_much)
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://example.com/big.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0002"


def test_a_network_failure_becomes_a_registered_error(monkeypatch):
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: ["93.184.216.34"])

    def _broken(*args, **kwargs):
        raise OSError("connection reset")

    monkeypatch.setattr(fetching, "_read", _broken)
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://example.com/a.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0006"


def test_a_host_that_does_not_resolve_is_reported(monkeypatch):
    def _unknown(host, port):
        raise OSError("name or service not known")

    monkeypatch.setattr(fetching, "_resolve", _unknown)
    with pytest.raises(HrcekError) as raised:
        fetching.fetch("https://nowhere.example.com/a.png")
    assert raised.value.error_code.code == "HRC-IMAGE-0006"


def test_the_connection_goes_to_the_address_that_was_checked(monkeypatch):
    """No second resolution between the check and the connection.

    Resolving again inside the socket layer is what makes DNS rebinding
    work: the answer that passed the check is not the answer connected
    to. The socket must be opened to the checked address itself.
    """
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: ["93.184.216.34"])
    connected: list[tuple[str, int]] = []

    class _Socket:
        def close(self):
            pass

    def _create_connection(address, timeout=None):
        connected.append(address)
        return _Socket()

    monkeypatch.setattr(fetching.socket, "create_connection", _create_connection)
    monkeypatch.setattr(
        fetching.http.client.HTTPConnection,
        "request",
        lambda self, *a, **k: None,
    )

    class _Response:
        status = 200

        def getheaders(self):
            return []

        def read(self, size):
            return b""

    monkeypatch.setattr(
        fetching.http.client.HTTPConnection,
        "getresponse",
        lambda self: _Response(),
    )
    fetching.fetch("http://example.com/a.png")

    assert connected == [("93.184.216.34", 80)], "connected by name, not by address"


def test_the_content_type_header_is_not_trusted(monkeypatch):
    # A lying header must not matter: only the bytes decide, and that
    # check belongs to imaging.prepare, which the caller runs next.
    monkeypatch.setattr(fetching, "_resolve", lambda host, port: ["93.184.216.34"])
    monkeypatch.setattr(
        fetching,
        "_read",
        lambda *a, **k: (200, {"content-type": "text/html"}, _png()),
    )
    assert fetching.fetch("https://example.com/a.png") == _png()
