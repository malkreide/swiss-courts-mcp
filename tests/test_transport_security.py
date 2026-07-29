"""Eingehende Host/Origin-Prüfung des HTTP-Transports (SEC-005, eingehend).

Das SDK lässt den DNS-Rebinding-Schutz aus, solange ``transport_security``
ungesetzt ist. Dieser Server hat ihn nie gesetzt — es gab also gar keine
Host-Prüfung. Diese Tests halten das neue Verhalten fest und schlagen fehl,
wenn der Schutz wieder wegfällt.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from swiss_courts_mcp.config import Settings
from swiss_courts_mcp.server import build_transport_security, create_mcp

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def test_loopback_bind_enables_protection():
    sec = build_transport_security(Settings(host="127.0.0.1", port=8000))
    assert sec is not None
    assert sec.enable_dns_rebinding_protection is True
    assert "127.0.0.1:8000" in sec.allowed_hosts


def test_non_local_bind_without_allowlist_stays_off():
    """0.0.0.0 ohne Allow-List: der erreichbare Name ist hier nicht bekannt,
    Raten würde jede echte Anfrage abweisen. Schutz bleibt aus, Aufrufer warnt."""
    assert build_transport_security(Settings(host="0.0.0.0", port=8000)) is None


def test_non_local_bind_with_allowlist_enables_protection():
    sec = build_transport_security(
        Settings(host="0.0.0.0", port=8000, allowed_hosts=["mcp.example.ch"])
    )
    assert sec is not None
    assert "mcp.example.ch" in sec.allowed_hosts
    assert "127.0.0.1:8000" in sec.allowed_hosts  # Health-Checks bleiben möglich


def test_configured_cors_origin_passes_transport_check():
    sec = build_transport_security(
        Settings(host="127.0.0.1", port=8000, cors_origins=["https://claude.ai"])
    )
    assert "https://claude.ai" in sec.allowed_origins


def test_wildcard_cors_is_not_copied():
    sec = build_transport_security(Settings(host="127.0.0.1", port=8000, cors_origins=["*"]))
    assert "*" not in sec.allowed_origins


def _post_with_host(host_header: str):
    settings = Settings(host="127.0.0.1", port=8000)
    server = create_mcp(settings, http=True)
    server.settings.transport_security = build_transport_security(settings)
    with TestClient(server.streamable_http_app()) as client:
        return client.post("/mcp", headers={"Host": host_header, **_HEADERS}, json=_INIT)


def test_allowed_host_is_served():
    assert _post_with_host("127.0.0.1:8000").status_code == 200


def test_foreign_host_is_rejected():
    assert _post_with_host("evil.example.com").status_code == 421


def test_right_host_wrong_port_is_rejected():
    """Der tragende Fall: eine zurückfallende Localhost-Policy würde
    ``evil.example.com`` ebenfalls abweisen. Nur richtiger Hostname mit
    falschem Port beweist, dass die port-genaue Allow-List wirklich hängt."""
    assert _post_with_host("127.0.0.1:9999").status_code == 421


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_all_loopback_forms_are_local(host):
    assert build_transport_security(Settings(host=host, port=8000)) is not None
