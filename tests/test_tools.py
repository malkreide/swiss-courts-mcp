"""Unit-Tests der Tool-Handler mit gemocktem HTTP (OPS-001, SDK-002).

Deckt die async Tool-Pfade ab: Erfolg, leere Treffer (match_type=none, ARCH-003),
Fehlerpfad (ToolError + Masking, OBS-001/002) und den maschinenlesbaren
structuredContent-Envelope (SDK-002).
"""

from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult

from swiss_courts_mcp import server
from swiss_courts_mcp.api_client import FACETS_URL, SEARCH_URL
from swiss_courts_mcp.server import (
    DecisionStatsInput,
    GetDecisionInput,
    ListCourtsInput,
    RecentDecisionsInput,
    SearchBGerInput,
    SearchByLawInput,
    SearchDecisionsInput,
)
from tests.conftest import EMPTY_ES_RESPONSE, SAMPLE_ES_RESPONSE


def text(res: CallToolResult) -> str:
    """Markdown-Text aus dem Tool-Result."""
    assert isinstance(res, CallToolResult)
    return "\n".join(c.text for c in res.content if c.type == "text")


def sc(res: CallToolResult) -> dict:
    """structuredContent aus dem Tool-Result (SDK-002)."""
    assert res.structuredContent is not None, "structuredContent fehlt"
    return res.structuredContent


@respx.mock
async def test_search_success_text_and_structured(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    res = await server.search_court_decisions(SearchDecisionsInput(query="Datenschutz"), ctx)
    md = text(res)
    assert "Testurteil" in md
    assert "Treffer-Typ:** exact" in md
    # SDK-002: konsistenter Envelope.
    env = sc(res)
    assert env["source"] == "entscheidsuche.ch"
    assert env["license"]  # CH-004
    assert env["match_type"] == "exact"
    assert env["count"] == 1
    assert env["total"] == 1
    assert env["results"][0]["signature"] == "CH_BGer_005_test_2025-01-01"
    assert env["results"][0]["provenance"]["source"] == "entscheidsuche.ch"


@respx.mock
async def test_search_empty_reports_match_type_none(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=EMPTY_ES_RESPONSE))
    res = await server.search_court_decisions(SearchDecisionsInput(query="zzzqqq"), ctx)
    assert "Treffer-Typ: none" in text(res)
    assert sc(res)["match_type"] == "none"
    assert sc(res)["count"] == 0


@respx.mock
async def test_search_upstream_error_raises_masked_toolerror(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(ToolError) as exc:
        await server.search_court_decisions(SearchDecisionsInput(query="xx"), ctx)
    # OBS-002: keine internen Details, nur freundliche Meldung.
    assert "503" in str(exc.value) or "nicht verfügbar" in str(exc.value)
    assert "Traceback" not in str(exc.value)


@respx.mock
async def test_get_decision_found(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    res = await server.get_court_decision(
        GetDecisionInput(signature="CH_BGer_005_test_2025-01-01"), ctx
    )
    assert "Gerichtsentscheid" in text(res)
    env = sc(res)
    assert env["match_type"] == "exact"
    assert env["decision"]["signature"] == "CH_BGer_005_test_2025-01-01"


@respx.mock
async def test_get_decision_not_found(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=EMPTY_ES_RESPONSE))
    res = await server.get_court_decision(GetDecisionInput(signature="CH_unknown_x"), ctx)
    assert "nicht gefunden" in text(res)
    assert sc(res)["decision"] is None


@respx.mock
async def test_bger_search(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    res = await server.search_bger_decisions(SearchBGerInput(query="Haft"), ctx)
    assert "Bundesgericht" in text(res)
    assert sc(res)["count"] == 1


@respx.mock
async def test_law_reference_search(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    res = await server.search_by_law_reference(SearchByLawInput(law_reference="Art. 8 BV"), ctx)
    assert "Art. 8 BV" in text(res)
    assert sc(res)["match_type"] == "exact"


@respx.mock
async def test_recent_decisions(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    res = await server.get_recent_decisions(RecentDecisionsInput(), ctx)
    assert "Neueste Gerichtsentscheide" in text(res)
    assert sc(res)["total"] == 1


@respx.mock
async def test_statistics(ctx):
    stats = {"hits": {"total": {"value": 42}}, "aggregations": {
        "by_canton": {"buckets": [{"key": "ZH", "doc_count": 10}]},
        "by_year": {"buckets": [{"key_as_string": "2024-01-01", "doc_count": 5}]},
    }}
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=stats))
    res = await server.get_decision_statistics(DecisionStatsInput(), ctx)
    assert "42" in text(res)
    env = sc(res)
    assert env["total"] == 42
    assert env["by_canton"][0] == {"key": "ZH", "count": 10}
    assert env["by_year"][0] == {"year": "2024", "count": 5}


@respx.mock
async def test_list_courts(ctx):
    respx.get(FACETS_URL).mock(return_value=httpx.Response(200, json={
        "CH_BGer": {"name": "Bundesgericht"}, "ZH": {"name": "Obergericht ZH"},
    }))
    res = await server.list_courts(ListCourtsInput(), ctx)
    assert "Bundesgericht" in text(res)
    env = sc(res)
    assert env["type"] == "court_taxonomy"
    assert env["count"] == 2
