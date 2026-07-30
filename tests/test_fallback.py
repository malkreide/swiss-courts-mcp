"""Tests für den Offline-Fallback (SCD-Dump), Phase 3/4.

Deckt die Pflicht-Testfälle ab:
  1. Live erfolgreich          → source == "live"           (siehe test_tools.py)
  2. Live Timeout              → Fallback → source == "dump" + coverage_note
  3. Kantonale Anfrage im Dump → ehrliche "nicht abgedeckt"-Antwort (kein
                                  leeres Resultat ohne Erklärung)
  4. Beide Quellen tot         → verständlicher Fehler (ToolError)

Plus: Download-/Build-Pfad (respx-gemockt), docref-Lookup, Statistik, Status-Tool.
Netzabhängige Tests sind mit ``@pytest.mark.live`` markiert und aus CI
ausgeschlossen (``-m "not live"``).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult

from swiss_courts_mcp import fallback, server
from swiss_courts_mcp.api_client import SEARCH_URL
from swiss_courts_mcp.server import (
    Canton,
    DecisionStatsInput,
    FallbackStatusInput,
    GetDecisionInput,
    RecentDecisionsInput,
    SearchByLawInput,
    SearchDecisionsInput,
)

FIXTURE = Path(__file__).parent / "fixtures" / "scd_sample.csv"


def text(res: CallToolResult) -> str:
    return "\n".join(c.text for c in res.content if c.type == "text")


def sc(res: CallToolResult) -> dict:
    assert res.structured_content is not None
    return res.structured_content


@pytest.fixture
def dump_store(tmp_path):
    """Ein aus der Fixture-CSV gebauter Dump-Store, als Prozess-Store gesetzt."""
    store = fallback.DumpStore(base_dir=tmp_path, record_id="test")
    rows = store.build_from_csv(FIXTURE, version="test-2024-3")
    assert rows == 4
    fallback.set_store(store)
    try:
        yield store
    finally:
        fallback.set_store(None)


# ---------------------------------------------------------------------------
# Pflicht-Testfall 2: Live Timeout → Fallback greift
# ---------------------------------------------------------------------------


@respx.mock
async def test_live_timeout_falls_back_to_dump(ctx, dump_store):
    respx.post(SEARCH_URL).mock(side_effect=httpx.ReadTimeout("timeout"))
    res = await server.search_court_decisions(SearchDecisionsInput(query="Datenschutz"), ctx)
    env = sc(res)
    assert env["source"] == "dump"
    assert env["coverage_note"]  # muss die partielle Abdeckung deklarieren
    assert env["dataset"].startswith("Swiss Federal Supreme Court Dataset")
    assert env["total"] >= 1
    md = text(res)
    assert "Offline-Modus" in md
    assert "2C_100/2020" in md  # der Datenschutz-Treffer aus der Fixture
    # Provenance pro Datensatz ist "dump".
    assert env["results"][0]["provenance"]["source"] == "dump"


@respx.mock
async def test_live_5xx_falls_back(ctx, dump_store):
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(503))
    res = await server.search_court_decisions(SearchDecisionsInput(query="Kehrichtabfuhr"), ctx)
    assert sc(res)["source"] == "dump"
    assert "1C_517/2016" in text(res)


@respx.mock
async def test_live_400_does_not_fall_back(ctx, dump_store):
    # 4xx (ausser 429) ist kein Verfügbarkeitsproblem → kein Fallback, maskiert.
    respx.post(SEARCH_URL).mock(return_value=httpx.Response(400))
    with pytest.raises(ToolError) as exc:
        await server.search_court_decisions(SearchDecisionsInput(query="xx"), ctx)
    assert "400" in str(exc.value) or "Ungültige" in str(exc.value)


# ---------------------------------------------------------------------------
# Pflicht-Testfall 3: Kantonale Anfrage im Fallback → ehrliche Nicht-Abdeckung
# ---------------------------------------------------------------------------


async def test_cantonal_query_in_dump_is_honest(ctx, dump_store, monkeypatch):
    monkeypatch.setenv("SWISS_COURTS_FORCE_DUMP", "1")
    res = await server.search_court_decisions(
        SearchDecisionsInput(query="Miete", canton=Canton.ZH), ctx
    )
    env = sc(res)
    assert env["source"] == "dump"
    assert env["total"] == 0
    assert env["count"] == 0
    # Kein leeres Resultat ohne Erklärung:
    assert "Kanton" in env["coverage_note"]
    md = text(res)
    assert "nicht abgedeckt" in md


async def test_recent_cantonal_in_dump_is_honest(ctx, dump_store, monkeypatch):
    monkeypatch.setenv("SWISS_COURTS_FORCE_DUMP", "1")
    res = await server.get_recent_decisions(RecentDecisionsInput(canton=Canton.BE), ctx)
    env = sc(res)
    assert env["source"] == "dump"
    assert env["total"] == 0
    assert "Kanton" in env["coverage_note"]


# ---------------------------------------------------------------------------
# Pflicht-Testfall 4: Beide Quellen tot → verständlicher Fehler
# ---------------------------------------------------------------------------


@respx.mock
async def test_both_sources_dead_graceful_error(ctx, tmp_path, monkeypatch):
    # Leerer Store (nicht gebaut); Zenodo NICHT gemockt → ensure_ready scheitert
    # und wird zu FallbackUnavailableError (Graceful Degradation).
    empty = fallback.DumpStore(base_dir=tmp_path / "empty", record_id="empty")
    fallback.set_store(empty)
    monkeypatch.setattr(
        empty, "ensure_ready",
        _raise_unavailable,
    )
    try:
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(503))
        with pytest.raises(ToolError) as exc:
            await server.search_court_decisions(SearchDecisionsInput(query="xx"), ctx)
        msg = str(exc.value)
        assert "Weder" in msg and "entscheidsuche.ch" in msg
        assert "Traceback" not in msg
    finally:
        fallback.set_store(None)


async def _raise_unavailable(*args, **kwargs):
    raise fallback.FallbackUnavailableError("Dump nicht ladbar (Test).")


# ---------------------------------------------------------------------------
# Download-/Build-Pfad (respx-gemockt) + Update-Erkennung
# ---------------------------------------------------------------------------


@respx.mock
async def test_ensure_ready_downloads_and_builds(tmp_path):
    record_id = "14867950"
    csv_text = FIXTURE.read_text("utf-8")
    content_url = f"https://zenodo.org/api/records/{record_id}/files/bger.csv/content"
    respx.get(f"https://zenodo.org/api/records/{record_id}").mock(
        return_value=httpx.Response(200, json={
            "id": int(record_id),
            "metadata": {"version": "2024-3"},
            "files": [
                {"key": "codebook.pdf", "links": {"self": "https://zenodo.org/x.pdf"}},
                {"key": "bger.csv", "links": {"self": content_url}},
            ],
        })
    )
    respx.get(content_url).mock(return_value=httpx.Response(200, text=csv_text))

    store = fallback.DumpStore(base_dir=tmp_path, record_id=record_id)
    assert not store.ready()
    await store.ensure_ready(client=None)
    assert store.ready()
    assert store.row_count() == 4
    total, hits = store.search("Datenschutz", None, None, 10)
    assert total == 1
    assert hits[0]["signature"] == "2C_100/2020"
    assert hits[0]["canton"] == "CH"  # föderal — nicht der Vorinstanz-Kanton


@respx.mock
async def test_ensure_ready_no_csv_file_is_unavailable(tmp_path):
    record_id = "999"
    respx.get(f"https://zenodo.org/api/records/{record_id}").mock(
        return_value=httpx.Response(200, json={"id": 999, "files": [
            {"key": "only.parquet", "links": {"self": "https://zenodo.org/x.parquet"}},
        ]})
    )
    store = fallback.DumpStore(base_dir=tmp_path, record_id=record_id)
    with pytest.raises(fallback.FallbackUnavailableError):
        await store.ensure_ready(client=None)


# ---------------------------------------------------------------------------
# docref-Lookup, Gesetzesreferenz, Statistik, Status-Tool
# ---------------------------------------------------------------------------


async def test_get_decision_dump_resolves_docref(ctx, dump_store, monkeypatch):
    monkeypatch.setenv("SWISS_COURTS_FORCE_DUMP", "1")
    res = await server.get_court_decision(GetDecisionInput(signature="1C_517/2016"), ctx)
    env = sc(res)
    assert env["source"] == "dump"
    assert env["match_type"] == "exact"
    assert env["decision"]["signature"] == "1C_517/2016"
    assert "Offline-Modus" in text(res)


async def test_get_decision_dump_unresolvable_is_honest(ctx, dump_store, monkeypatch):
    monkeypatch.setenv("SWISS_COURTS_FORCE_DUMP", "1")
    res = await server.get_court_decision(
        GetDecisionInput(signature="CH_BGer_unknown_xyz"), ctx
    )
    env = sc(res)
    assert env["source"] == "dump"
    assert env["match_type"] == "none"
    assert env["decision"] is None
    assert "nicht auflösbar" in text(res)


async def test_law_reference_dump_notes_limitation(ctx, dump_store, monkeypatch):
    monkeypatch.setenv("SWISS_COURTS_FORCE_DUMP", "1")
    res = await server.search_by_law_reference(
        SearchByLawInput(law_reference="Art. 25 DSG"), ctx
    )
    env = sc(res)
    assert env["source"] == "dump"
    # Die Fixture nennt "Art. 25 DSG" im issue des Datenschutz-Falls.
    assert env["total"] >= 1
    assert "topic/issue" in env["coverage_note"]


async def test_statistics_dump(ctx, dump_store, monkeypatch):
    monkeypatch.setenv("SWISS_COURTS_FORCE_DUMP", "1")
    res = await server.get_decision_statistics(DecisionStatsInput(), ctx)
    env = sc(res)
    assert env["source"] == "dump"
    assert env["total"] == 4
    assert env["by_canton"] == []  # föderal — keine Kantons-Dimension
    years = {b["year"] for b in env["by_year"]}
    assert "2020" in years
    assert "## Entscheid-Statistiken (Offline-Dump)" in text(res)


async def test_statistics_dump_cantonal_out_of_coverage(ctx, dump_store, monkeypatch):
    monkeypatch.setenv("SWISS_COURTS_FORCE_DUMP", "1")
    res = await server.get_decision_statistics(DecisionStatsInput(canton=Canton.ZH), ctx)
    env = sc(res)
    assert env["source"] == "dump"
    assert env["total"] == 0
    assert "nicht abgedeckt" in text(res)


async def test_get_fallback_status_tool(ctx, dump_store):
    res = await server.get_fallback_status(FallbackStatusInput(), ctx)
    env = sc(res)
    assert env["source"] == "dump"
    assert env["status"]["ready"] is True
    assert env["status"]["rows"] == 4
    md = text(res)
    assert "Abdeckung" in md
    assert "SWISS_COURTS_FORCE_DUMP=1" in md


async def test_get_fallback_status_not_ready(ctx, tmp_path):
    empty = fallback.DumpStore(base_dir=tmp_path / "nope", record_id="empty")
    fallback.set_store(empty)
    try:
        res = await server.get_fallback_status(FallbackStatusInput(), ctx)
        env = sc(res)
        assert env["status"]["ready"] is False
        assert env["status"]["rows"] == 0
    finally:
        fallback.set_store(None)


def test_out_of_coverage_note():
    assert fallback.out_of_coverage_note("ZH", None) is not None
    assert fallback.out_of_coverage_note(None, "bundesverwaltungsgericht") is not None
    assert fallback.out_of_coverage_note(None, "bundesgericht") is None
    assert fallback.out_of_coverage_note(None, None) is None


def test_docref_candidates_from_es_signature():
    cands = fallback._docref_candidates("CH_BGer_005_1C-517-2016_2017-04-12")
    assert "1C_517/2016" in cands


# ---------------------------------------------------------------------------
# Live-Tests (echte Quellen) — aus CI ausgeschlossen via -m "not live"
# ---------------------------------------------------------------------------


@pytest.mark.live
async def test_live_zenodo_record_metadata():
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await fallback._get_json(
            f"{fallback.ZENODO_API}/{fallback.DEFAULT_RECORD_ID}", client
        )
    assert any(f["key"].endswith(".csv") for f in data["files"])
    assert data["metadata"]["license"]["id"] == "cc-by-4.0"


@pytest.mark.live
async def test_live_zenodo_latest_version():
    async with httpx.AsyncClient(timeout=30.0) as client:
        info = await fallback.latest_version(client)
    assert info["latest_record"]
    assert info["latest_version"]
