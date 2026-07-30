"""Server-Factory: stdio default ohne Auth, HTTP mit Auth (SEC-009, SCALE-002)."""

from __future__ import annotations

import pytest
from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette

from swiss_courts_mcp.config import Settings
from swiss_courts_mcp.server import create_mcp, register_prompts, register_tools


def test_stdio_server_builds_without_auth():
    mcp = create_mcp(Settings(), http=False)
    assert mcp is not None


def test_http_server_with_auth_builds():
    settings = Settings(
        auth_enabled=True,
        auth_secret="x" * 32,
        host="0.0.0.0",  # noqa: S104 — Container-Szenario
        stateless_http=True,
        required_scopes=["courts:read"],
    )
    mcp = create_mcp(settings, http=True)
    assert mcp is not None


@pytest.mark.parametrize("stateless", [True, False])
def test_stateless_http_reaches_the_app(monkeypatch, stateless):
    """SCALE-002: horizontale Skalierung ohne Sticky-Sessions.

    In 1.x war ``stateless_http`` ein MCPServer-Konstruktor-Argument und liess
    sich an ``mcp.settings`` ablesen. In 2.x ist es ein Kwarg von
    ``streamable_http_app()`` — ein Ort, an dem es beim Migrieren leicht
    verloren geht, ohne dass ein Test es merkt. Darum wird hier der Kwarg
    selbst geprüft, nicht mehr ein Zwischenzustand.

    Beide Werte werden geprüft: der Default ist ``True``, ein fest
    verdrahtetes ``stateless_http=True`` würde also nur mit dem True-Fall
    unentdeckt durchgehen.
    """
    import swiss_courts_mcp.server as srv

    captured: dict = {}

    def _fake_app(self, **kwargs):
        captured.update(kwargs)
        return Starlette()

    monkeypatch.setattr(MCPServer, "streamable_http_app", _fake_app)
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: None)
    srv._run_http(
        Settings(host="0.0.0.0", stateless_http=stateless)  # noqa: S104 — Container
    )
    assert captured["stateless_http"] is stateless
    # Der Bind muss mitreisen: 2.x schaltet sonst eine Loopback-Allow-List
    # scharf, und ein 0.0.0.0-Bind würde jede echte Anfrage mit 421 abweisen.
    assert captured["host"] == "0.0.0.0"  # noqa: S104


def test_settings_no_longer_carries_stateless_http():
    """Der 1.x-Leseweg ist weg — und er schlägt laut fehl, nicht still."""
    mcp = create_mcp(Settings(stateless_http=True), http=True)
    assert not hasattr(mcp.settings, "stateless_http")
    with pytest.raises(ValueError, match='has no field "stateless_http"'):
        mcp.settings.stateless_http = True


def test_http_server_without_auth_builds():
    mcp = create_mcp(Settings(stateless_http=True), http=True)
    assert mcp is not None


async def test_all_tools_registered():
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer("t")
    register_tools(mcp)
    register_prompts(mcp)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "search_court_decisions", "get_court_decision", "search_bger_decisions",
        "search_by_law_reference", "list_courts", "get_recent_decisions",
        "get_decision_statistics", "get_fallback_status",
    }
    # ARCH-008: zweites Primitiv (Prompt) vorhanden.
    prompts = await mcp.list_prompts()
    assert any(p.name == "rechtsrecherche" for p in prompts)


async def test_tool_annotations_read_only():
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer("t")
    register_tools(mcp)
    tools = await mcp.list_tools()
    for t in tools:
        assert t.annotations is not None
        assert t.annotations.read_only_hint is True
        assert t.annotations.open_world_hint is True


async def test_tools_have_no_auto_output_schema():
    # SDK-002: structured_output=False — die Tools liefern eigenes
    # structuredContent via CallToolResult, kein auto-generiertes Schema.
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer("t")
    register_tools(mcp)
    for t in await mcp.list_tools():
        assert t.output_schema is None
