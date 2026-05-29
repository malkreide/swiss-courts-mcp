"""Protocol-Version-Pinning + Drift-Erkennung (ARCH-012)."""

from __future__ import annotations

from mcp.types import LATEST_PROTOCOL_VERSION

from swiss_courts_mcp.server import PROTOCOL_VERSION


def test_protocol_version_is_pinned():
    assert PROTOCOL_VERSION == "2025-11-25"


def test_no_drift_against_installed_sdk():
    # Schlägt fehl, wenn das SDK eine neuere Protocol-Version mitbringt.
    # Dann: PROTOCOL_VERSION + CHANGELOG + README bewusst nachziehen.
    assert PROTOCOL_VERSION == LATEST_PROTOCOL_VERSION, (
        "MCP-SDK-Protocol-Version weicht vom Pin ab — bewusst aktualisieren "
        "(server.PROTOCOL_VERSION, CHANGELOG, README)."
    )
