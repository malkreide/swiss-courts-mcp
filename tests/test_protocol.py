"""Protocol-Version-Pinning + Drift-Erkennung (ARCH-012).

mcp 2.x bedient **zwei Protokoll-Ären** über denselben Server
(`serve_dual_era_loop`; die erste Anfrage des Clients entscheidet):

* die **Legacy-Ära** mit `initialize`-Handshake. Sie deckelt bei
  `LATEST_HANDSHAKE_VERSION`, und `HANDSHAKE_PROTOCOL_VERSION` pinnt diesen
  Deckel.
* die **Modern-Ära** mit Per-Request-Envelope. Sie erreicht
  `LATEST_MODERN_VERSION`, und `MODERN_PROTOCOL_VERSION` pinnt sie.

`LATEST_PROTOCOL_VERSION` ist in 2.x ein Alias auf die *Modern*-Version, nicht
auf die Handshake-Version. Der ursprüngliche Drift-Guard verglich eine einzelne
`PROTOCOL_VERSION` dagegen und schlug nach dem SDK-Upgrade fehl — nicht
fälschlich: das SDK bringt tatsächlich eine neuere Revision mit. Nur beschrieb
diese Konstante die Handshake-Ära. Seither wird gegen **beide** Konstanten
geprüft, jede gegen die Ära, die sie beschreibt.

Nachgemessen, nicht aus Konstantennamen geschlossen: ein Legacy-`initialize`
mit `protocolVersion: "2026-07-28"` bekommt von diesem Server `2025-11-25`
zurück (siehe `test_handshake_caps_at_the_pinned_version`). Was die
Modern-Ära am Draht tut, steht in `tests/test_modern_era.py`.
"""

from __future__ import annotations

import json

import pytest
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from starlette.testclient import TestClient

from swiss_courts_mcp.config import Settings
from swiss_courts_mcp.server import (
    HANDSHAKE_PROTOCOL_VERSION,
    MODERN_PROTOCOL_VERSION,
    PROTOCOL_VERSIONS,
    create_mcp,
)

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def test_protocol_versions_are_pinned():
    assert HANDSHAKE_PROTOCOL_VERSION == "2025-11-25"
    assert MODERN_PROTOCOL_VERSION == "2026-07-28"


def test_both_eras_are_named_and_ordered():
    """Die Doku-Tupel führt beide Ären, älteste zuerst.

    Eine einzelne Konstante konnte nur eine Ära benennen; dass es jetzt zwei
    sind, ist der Punkt der Änderung und gehört deshalb in eine Zusicherung.
    """
    assert PROTOCOL_VERSIONS == (HANDSHAKE_PROTOCOL_VERSION, MODERN_PROTOCOL_VERSION)
    assert HANDSHAKE_PROTOCOL_VERSION < MODERN_PROTOCOL_VERSION


def test_no_handshake_drift_against_installed_sdk():
    """Guard für die Ära, die ältere Clients sprechen.

    Schlägt fehl, wenn das SDK den Handshake-Deckel hebt. Dann:
    HANDSHAKE_PROTOCOL_VERSION + CHANGELOG + README bewusst nachziehen.
    """
    assert HANDSHAKE_PROTOCOL_VERSION == LATEST_HANDSHAKE_VERSION, (
        "Handshake-Protocol-Version des SDK weicht vom Pin ab — bewusst "
        "aktualisieren (server.HANDSHAKE_PROTOCOL_VERSION, CHANGELOG, README)."
    )


def test_no_modern_drift_against_installed_sdk():
    """Derselbe Guard für die Modern-Ära — vorher gab es ihn nicht.

    Die frühere Fassung hielt `LATEST_MODERN_VERSION == "2026-07-28"` in einem
    Test fest, der die Konstante nur *beobachtete*: nichts im Server-Code
    benannte diese Revision, also konnte auch nichts nachgezogen werden. Jetzt
    steht auf beiden Seiten ein Pin, und ein SDK-Bump zeigt auf die Stelle, die
    zu ändern ist.
    """
    assert MODERN_PROTOCOL_VERSION == LATEST_MODERN_VERSION, (
        "Modern-Protocol-Version des SDK weicht vom Pin ab — bewusst "
        "aktualisieren (server.MODERN_PROTOCOL_VERSION, CHANGELOG, README)."
    )


def test_the_modern_era_is_the_newer_one():
    """Hält die Reihenfolge der Ären fest, nicht bloss zwei Zahlen.

    Solange das gilt, ist der Handshake-Deckel wirklich ein Deckel und nicht
    die neuere Revision — das ist die Annahme, auf der
    `test_handshake_caps_at_the_pinned_version` ruht.
    """
    assert LATEST_MODERN_VERSION > LATEST_HANDSHAKE_VERSION


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


@pytest.mark.parametrize("requested", ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"])
def test_handshake_echoes_supported_client_versions(requested):
    """Ältere Clients behalten ihre Revision — die Migration bricht sie nicht."""
    assert _initialize(requested) == requested


def test_handshake_caps_at_the_pinned_version():
    """Der tragende Fall der Legacy-Ära.

    Ein Client, der die Modern-Revision über den Legacy-Handshake anfragt,
    bekommt den Deckel zurück. Genau das macht `HANDSHAKE_PROTOCOL_VERSION` zur
    richtigen Beschreibung dieser Ära — und nur dieser Test schlägt fehl, wenn
    das SDK den Deckel später verschiebt.

    Er sagt ausdrücklich NICHT, dass der Server 2026-07-28 nicht spricht: der
    Handshake ist der falsche Weg dorthin. Welchen Weg es gibt, misst
    `tests/test_modern_era.py`.
    """
    assert _initialize(MODERN_PROTOCOL_VERSION) == HANDSHAKE_PROTOCOL_VERSION
