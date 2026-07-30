"""Protocol-Version-Pinning + Drift-Erkennung (ARCH-012).

mcp 2.x bedient **zwei Protokoll-Ären** über denselben Server
(`serve_dual_era_loop`; die erste Anfrage des Clients entscheidet):

* die **Legacy-Ära** mit `initialize`-Handshake — das, was heutige Clients
  sprechen. Sie deckelt bei `LATEST_HANDSHAKE_VERSION`.
* die **Modern-Ära** mit Per-Request-Envelope. Sie erreicht
  `LATEST_MODERN_VERSION`.

`LATEST_PROTOCOL_VERSION` ist in 2.x ein Alias auf die *Modern*-Version, nicht
auf die Handshake-Version. Der ursprüngliche Drift-Guard verglich `PROTOCOL_VERSION`
dagegen und schlug nach dem SDK-Upgrade fehl — nicht fälschlich: das SDK bringt
tatsächlich eine neuere Revision mit. Nur beschreibt `PROTOCOL_VERSION` die
Handshake-Ära, also wird jetzt gegen beide Konstanten geprüft, statt eine
stillschweigend zu ignorieren.

Nachgemessen, nicht aus Konstantennamen geschlossen: ein Legacy-`initialize`
mit `protocolVersion: "2026-07-28"` bekommt von diesem Server `2025-11-25`
zurück (siehe `test_handshake_caps_at_the_pinned_version`).
"""

from __future__ import annotations

import json

import pytest
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from starlette.testclient import TestClient

from swiss_courts_mcp.config import Settings
from swiss_courts_mcp.server import PROTOCOL_VERSION, create_mcp

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def test_protocol_version_is_pinned():
    assert PROTOCOL_VERSION == "2025-11-25"


def test_no_handshake_drift_against_installed_sdk():
    """Der eigentliche Guard: die Ära, die bestehende Clients sprechen.

    Schlägt fehl, wenn das SDK den Handshake-Deckel hebt. Dann:
    PROTOCOL_VERSION + CHANGELOG + README bewusst nachziehen.
    """
    assert PROTOCOL_VERSION == LATEST_HANDSHAKE_VERSION, (
        "Handshake-Protocol-Version des SDK weicht vom Pin ab — bewusst "
        "aktualisieren (server.PROTOCOL_VERSION, CHANGELOG, README)."
    )


def test_modern_era_revision_is_known_and_newer():
    """Hält fest, dass die Modern-Ära über den Pin hinausgeht.

    Das ist kein Fehler, sondern der Grund, warum der Guard oben auf die
    Handshake-Konstante zeigt: `LATEST_PROTOCOL_VERSION` ist in 2.x ein Alias
    auf diese Modern-Version. Steigt sie weiter, fällt das hier auf.
    """
    assert LATEST_MODERN_VERSION == "2026-07-28"
    assert LATEST_MODERN_VERSION > PROTOCOL_VERSION


def _initialize(requested: str) -> str | None:
    """Ein Legacy-`initialize` durch den echten ASGI-Stack, Antwort-Version."""
    server = create_mcp(Settings(host="127.0.0.1", port=8000), http=True)
    with TestClient(server.streamable_http_app(host="127.0.0.1")) as client:
        response = client.post(
            "/mcp",
            headers={"Host": "127.0.0.1:8000", **_HEADERS},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": requested,
                    "capabilities": {},
                    "clientInfo": {"name": "legacy-client", "version": "1"},
                },
            },
        )
        body = response.text
        for line in body.splitlines():  # SSE-Framing abziehen
            if line.startswith("data: "):
                body = line[len("data: ") :]
        return json.loads(body).get("result", {}).get("protocolVersion")


@pytest.mark.parametrize(
    "requested", ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"]
)
def test_handshake_echoes_supported_client_versions(requested):
    """Ältere Clients behalten ihre Revision — die Migration bricht sie nicht."""
    assert _initialize(requested) == requested


def test_handshake_caps_at_the_pinned_version():
    """Der tragende Fall.

    Ein Client, der die Modern-Revision über den Legacy-Handshake anfragt,
    bekommt den Deckel zurück. Genau das macht `PROTOCOL_VERSION` zur richtigen
    Beschreibung dieser Ära — und nur dieser Test schlägt fehl, wenn das SDK
    den Deckel später verschiebt.
    """
    assert _initialize("2026-07-28") == PROTOCOL_VERSION
