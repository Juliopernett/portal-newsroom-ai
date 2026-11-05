"""Guard against the server being used to reach internal addresses (SSRF).

Sprint Fuentes (2026-10-29). Radar sources are URLs an operator types in,
and the server fetches them. Without a check, a source pointing at
`http://127.0.0.1:...` or the cloud metadata address (`169.254.169.254`)
would make this app read internal services on the operator's behalf.
Only public `http`/`https` hosts are allowed: every address the name
resolves to must be a normal public one.

`get_seguro` closes the redirect gap: it follows redirects by hand and
validates every hop, so a public site can't bounce the server to an
internal address. (Residual risk: DNS rebinding between the check and the
connection — acceptable for this internal tool.)
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests

_MAX_REDIRECTS = 5


class UrlNoPermitidaError(ValueError):
    """The URL is not a public http(s) address."""


def validar_url_publica(url: str) -> None:
    """Raise `UrlNoPermitidaError` unless `url` is a public http(s) address."""
    partes = urlparse(url.strip())
    if partes.scheme not in ("http", "https"):
        raise UrlNoPermitidaError("La dirección debe empezar por http:// o https://")
    host = partes.hostname
    if not host:
        raise UrlNoPermitidaError("La dirección no tiene un dominio válido")
    try:
        direcciones = socket.getaddrinfo(host, partes.port or None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UrlNoPermitidaError(f"No se pudo resolver el dominio '{host}'") from exc
    for *_, sockaddr in direcciones:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UrlNoPermitidaError("La dirección apunta a una red interna, no está permitida")


def get_seguro(url: str, *, timeout: int, **kwargs) -> requests.Response:
    """`requests.get` that validates `url` and every redirect hop as public.

    Raises `UrlNoPermitidaError` for a non-public address and
    `requests.TooManyRedirects` past `_MAX_REDIRECTS`. The caller owns the
    returned response (use it as a context manager with `stream=True`).
    """
    actual = url
    for _ in range(_MAX_REDIRECTS + 1):
        validar_url_publica(actual)
        response = requests.get(actual, timeout=timeout, allow_redirects=False, **kwargs)
        if response.is_redirect and response.headers.get("location"):
            actual = urljoin(actual, response.headers["location"])
            response.close()
            continue
        return response
    raise requests.TooManyRedirects(f"Más de {_MAX_REDIRECTS} redirecciones")
