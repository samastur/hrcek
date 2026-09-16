"""Fetching an image from an address somebody gave us.

This is the server making a request on a stranger's instruction, which
is server-side request forgery in the making. The address may name the
machine Hrček runs on, something else on the home network, or a cloud
metadata endpoint that hands out credentials to anyone who asks. The
entries design deferred images for exactly this reason.

The rules, in order:

* http and https only. Nothing else, and never a redirect into
  something else.
* Resolve the host, then check **every** address it answers with. One
  private answer refuses the whole host: a connection could land on it.
* Connect to the address that was checked, not to the name. Resolving
  again inside the socket layer would let a DNS answer change between
  the check and the connection.
* Re-run all of it on every redirect, at most three of them.
* Give up after a few seconds, and stop reading past the byte cap.

Nothing here decides whether the bytes are an image. That is
`imaging.prepare`, which the caller runs next, and which trusts no
header either.
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from typing import Final
from urllib.parse import urljoin, urlsplit, urlunsplit

from hrcek.core.errors import HrcekError
from hrcek.entries.errors import (
    IMAGE_ADDRESS_FORBIDDEN,
    IMAGE_ADDRESS_INVALID,
    IMAGE_FETCH_FAILED,
    IMAGE_TOO_LARGE,
)
from hrcek.entries.imaging import MAX_BYTES

ALLOWED_SCHEMES: Final = ("http", "https")
MAX_REDIRECTS: Final = 3
TIMEOUT_SECONDS: Final = 5.0

OK: Final = 200
REDIRECTS: Final = (301, 302, 303, 307, 308)
IPV4: Final = 4
IPV6: Final = 6

# Read a little past the cap so going over is detected rather than
# silently truncating a file into something that looks valid.
_READ_CHUNK: Final = 64 * 1024


class TooMuchDataError(Exception):
    """The body went past the cap; raised before it is all in memory."""


def fetch(address: str) -> bytes:
    """Return the bytes at `address`, or raise a registered error."""
    target = address
    for _hop in range(MAX_REDIRECTS + 1):
        scheme, host, port, path = _parse(target)
        addresses = _resolve_or_fail(host, port)
        _check_addresses(addresses)

        try:
            # The address that was checked is the one connected to.
            status, headers, body = _read(scheme, host, port, path, addresses[0])
        except TooMuchDataError as exc:
            raise HrcekError(IMAGE_TOO_LARGE, {"limit_bytes": MAX_BYTES}) from exc
        except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
            raise HrcekError(IMAGE_FETCH_FAILED) from exc

        if status in REDIRECTS:
            location = headers.get("location", "")
            if not location:
                raise HrcekError(IMAGE_FETCH_FAILED, {"status": status})
            target = _absolute(target, location)
            continue

        if status != OK:
            raise HrcekError(IMAGE_FETCH_FAILED, {"status": status})
        return body

    raise HrcekError(IMAGE_FETCH_FAILED, {"redirects": MAX_REDIRECTS})


def _parse(address: str) -> tuple[str, str, int, str]:
    parts = urlsplit((address or "").strip())
    if parts.scheme not in ALLOWED_SCHEMES or not parts.hostname:
        raise HrcekError(IMAGE_ADDRESS_INVALID, {"scheme": parts.scheme})

    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as exc:  # a port that is not a number
        raise HrcekError(IMAGE_ADDRESS_INVALID) from exc

    path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
    return parts.scheme, parts.hostname, port, path


def _absolute(current: str, location: str) -> str:
    """Resolve a redirect target, refusing anything not http(s).

    `urljoin` would happily produce a `file://` address from a relative
    one; the scheme is therefore checked here rather than trusted.
    """
    resolved = urljoin(current, location)
    if urlsplit(resolved).scheme not in ALLOWED_SCHEMES:
        raise HrcekError(IMAGE_ADDRESS_INVALID, {"scheme": urlsplit(resolved).scheme})
    return resolved


def _resolve_or_fail(host: str, port: int) -> list[str]:
    try:
        addresses = _resolve(host, port)
    except OSError as exc:
        raise HrcekError(IMAGE_FETCH_FAILED, {"host": host}) from exc
    if not addresses:
        raise HrcekError(IMAGE_FETCH_FAILED, {"host": host})
    return addresses


def _resolve(host: str, port: int) -> list[str]:
    """Every address this host answers with. Patched in tests."""
    infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    # sockaddr[0] is the address; typeshed widens it to str | int for
    # address families we never ask for.
    return [str(info[4][0]) for info in infos]


def _check_addresses(addresses: list[str]) -> None:
    """Refuse the host unless every answer is a public address.

    All of them, not just the one we would use: a host answering with
    both a public and a private address could still be reached on the
    private one.
    """
    for raw in addresses:
        try:
            address = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise HrcekError(IMAGE_ADDRESS_FORBIDDEN, {"address": raw}) from exc

        if _is_forbidden(address):
            raise HrcekError(IMAGE_ADDRESS_FORBIDDEN, {"address": raw})


def _is_forbidden(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        address.is_private  # covers loopback, link-local, unique-local
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return True

    # Carrier-grade NAT: public-looking, but somebody else's network
    # edge, and not somewhere a family bookmark tool has business going.
    if address.version == IPV4 and address in ipaddress.ip_network("100.64.0.0/10"):
        return True

    # An IPv6 address wrapping an IPv4 one is judged by the address
    # inside it, which is how ::ffff:127.0.0.1 would otherwise slip past.
    if address.version == IPV6:
        mapped = getattr(address, "ipv4_mapped", None)
        if mapped is not None and _is_forbidden(mapped):
            return True

    return False


def _connect(scheme: str, host: str, port: int, ip: str) -> http.client.HTTPConnection:
    """A connection to `ip`, but speaking as `host`."""
    raw = socket.create_connection((ip, port), timeout=TIMEOUT_SECONDS)
    connection: http.client.HTTPConnection
    if scheme == "https":
        context = ssl.create_default_context()
        connection = http.client.HTTPSConnection(
            host, port, timeout=TIMEOUT_SECONDS, context=context
        )
        # server_hostname is the name, so the certificate is checked
        # against what the person asked for, not against an IP.
        connection.sock = context.wrap_socket(raw, server_hostname=host)
    else:
        connection = http.client.HTTPConnection(host, port, timeout=TIMEOUT_SECONDS)
        connection.sock = raw
    return connection


def _read(
    scheme: str, host: str, port: int, path: str, ip: str
) -> tuple[int, dict[str, str], bytes]:
    """One request, capped and timed. Patched in tests.

    The socket is opened to `ip` — the address that was just checked —
    and handed to the connection already made. Letting http.client
    connect by name would resolve a second time, and a DNS answer that
    changed in between is precisely the attack the checking is for.
    The name is still used for the Host header and for TLS, so
    certificate validation is unaffected.
    """
    connection = _connect(scheme, host, port, ip)
    try:
        connection.request(
            "GET",
            path,
            headers={"User-Agent": "Hrcek", "Accept": "image/*"},
        )
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}

        # A declared length over the cap is refused before reading.
        declared = headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > MAX_BYTES:
            raise TooMuchDataError

        body = bytearray()
        while True:
            chunk = response.read(_READ_CHUNK)
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise TooMuchDataError
        return response.status, headers, bytes(body)
    finally:
        connection.close()
