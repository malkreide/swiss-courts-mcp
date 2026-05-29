"""Unit-Tests der Tool-Handler mit gemocktem HTTP (OPS-001).

Deckt die zuvor ungetesteten async Tool-Pfade ab: Erfolg, leere Treffer
(match_type=none, ARCH-003) und Fehlerpfad (ToolError + Masking, OBS-001/002).
"""

from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError

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


@respx.mock
async def test_search_success_includes_source_and_match_type(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    out = await server.search_court_decisions(SearchDecisionsInput(query="Datenschutz"), ctx)
    assert "Testurteil" in out
    assert "Treffer-Typ:** exact" in out
    assert "entscheidsuche.ch" in out
    assert "Lizenz" in out  # CH-004


@respx.mock
async def test_search_empty_reports_match_type_none(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=EMPTY_ES_RESPONSE))
    out = await server.search_court_decisions(SearchDecisionsInput(query="zzzqqq"), ctx)
    assert "Treffer-Typ: none" in out
    assert "Tipps" in out


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
    out = await server.get_court_decision(
        GetDecisionInput(signature="CH_BGer_005_test_2025-01-01"), ctx
    )
    assert "Gerichtsentscheid" in out
    assert "Quelle / Lizenz" in out  # CH-004 per-record provenance


@respx.mock
async def test_get_decision_not_found(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=EMPTY_ES_RESPONSE))
    out = await server.get_court_decision(GetDecisionInput(signature="CH_unknown_x"), ctx)
    assert "nicht gefunden" in out


@respx.mock
async def test_bger_search(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    out = await server.search_bger_decisions(SearchBGerInput(query="Haft"), ctx)
    assert "Bundesgericht" in out


@respx.mock
async def test_law_reference_search(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    out = await server.search_by_law_reference(SearchByLawInput(law_reference="Art. 8 BV"), ctx)
    assert "Art. 8 BV" in out


@respx.mock
async def test_recent_decisions(ctx):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=SAMPLE_ES_RESPONSE))
    out = await server.get_recent_decisions(RecentDecisionsInput(), ctx)
    assert "Neueste Gerichtsentscheide" in out


@respx.mock
async def test_statistics(ctx):
    stats = {"hits": {"total": {"value": 42}}, "aggregations": {
        "by_canton": {"buckets": [{"key": "ZH", "doc_count": 10}]},
        "by_year": {"buckets": [{"key_as_string": "2024-01-01", "doc_count": 5}]},
    }}
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=stats))
    out = await server.get_decision_statistics(DecisionStatsInput(), ctx)
    assert "42" in out
    assert "ZH" in out


@respx.mock
async def test_list_courts(ctx):
    respx.get(FACETS_URL).mock(return_value=httpx.Response(200, json={
        "CH_BGer": {"name": "Bundesgericht"}, "ZH": {"name": "Obergericht ZH"},
    }))
    out = await server.list_courts(ListCourtsInput(), ctx)
    assert "Bundesgericht" in out
    assert "Obergericht ZH" in out
