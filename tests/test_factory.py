"""Server-Factory: stdio default ohne Auth, HTTP mit Auth (SEC-009, SCALE-002)."""

from __future__ import annotations

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
    # SCALE-002: stateless_http aktiviert horizontale Skalierung ohne Sticky-Sessions.
    assert mcp.settings.stateless_http is True


def test_http_server_without_auth_builds():
    mcp = create_mcp(Settings(stateless_http=True), http=True)
    assert mcp is not None


async def test_all_tools_registered():
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("t")
    register_tools(mcp)
    register_prompts(mcp)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "search_court_decisions", "get_court_decision", "search_bger_decisions",
        "search_by_law_reference", "list_courts", "get_recent_decisions",
        "get_decision_statistics",
    }
    # ARCH-008: zweites Primitiv (Prompt) vorhanden.
    prompts = await mcp.list_prompts()
    assert any(p.name == "rechtsrecherche" for p in prompts)


async def test_tool_annotations_read_only():
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("t")
    register_tools(mcp)
    tools = await mcp.list_tools()
    for t in tools:
        assert t.annotations is not None
        assert t.annotations.readOnlyHint is True
        assert t.annotations.openWorldHint is True
