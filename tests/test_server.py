"""Tests für den MCP Server (swiss_courts_mcp.server)."""

import pytest

from swiss_courts_mcp.server import (
    Canton,
    CourtLevel,
    Language,
    format_decision_detail,
    format_hit,
    result_header,
)

# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Tests für die Enums."""

    def test_all_26_cantons(self):
        assert len(Canton) == 26

    def test_canton_values(self):
        assert Canton.ZH.value == "ZH"
        assert Canton.GE.value == "GE"
        assert Canton.TI.value == "TI"

    def test_court_levels(self):
        assert CourtLevel.BUNDESGERICHT.value == "bundesgericht"
        assert CourtLevel.BUNDESVERWALTUNGSGERICHT.value == "bundesverwaltungsgericht"

    def test_languages(self):
        assert Language.DE.value == "de"
        assert Language.FR.value == "fr"
        assert Language.IT.value == "it"


# ---------------------------------------------------------------------------
# Formatierung Tests
# ---------------------------------------------------------------------------


SAMPLE_EXTRACTED = {
    "signature": "CH_BGer_005_test",
    "date": "2025-03-15",
    "court": "Bundesgericht",
    "canton": "CH",
    "references": ["5A_123/2025"],
    "title": "Testurteil zum Mietrecht",
    "abstract": "Das Bundesgericht hat entschieden...",
    "language": "de",
    "url": "https://entscheidsuche.ch/docs/CH_BGer_005_test.html",
}


class TestFormatHit:
    """Tests für format_hit()."""

    def test_basic_format(self):
        md = format_hit(SAMPLE_EXTRACTED, 1)
        assert "### 1. Bundesgericht" in md
        assert "2025-03-15" in md
        assert "5A_123/2025" in md
        assert "`CH_BGer_005_test`" in md
        assert "Testurteil" in md
        assert "[Volltext]" in md

    def test_long_abstract_truncated(self):
        hit = {**SAMPLE_EXTRACTED, "abstract": "x" * 500}
        md = format_hit(hit, 1)
        assert "..." in md
        assert len(md) < 1000

    def test_empty_references(self):
        hit = {**SAMPLE_EXTRACTED, "references": []}
        md = format_hit(hit, 1)
        assert "—" in md


class TestFormatDecisionDetail:
    """Tests für format_decision_detail()."""

    def test_detail_format(self):
        md = format_decision_detail(SAMPLE_EXTRACTED)
        assert "## Gerichtsentscheid" in md
        assert "| **Gericht** | Bundesgericht |" in md
        assert "### Titel" in md
        assert "### Zusammenfassung" in md

    def test_no_title(self):
        hit = {**SAMPLE_EXTRACTED, "title": ""}
        md = format_decision_detail(hit)
        assert "### Titel" not in md


class TestResultHeader:
    """Tests für result_header()."""

    def test_all_shown(self):
        hdr = result_header(10, 10, "Test")
        assert "**Treffer:** 10" in hdr
        assert "von" not in hdr

    def test_partial_shown(self):
        hdr = result_header(10, 100, "Test")
        assert "10 von 100" in hdr


# ---------------------------------------------------------------------------
# Input-Modell Validierung
# ---------------------------------------------------------------------------


class TestInputModels:
    """Tests für Pydantic Input-Modelle."""

    def test_search_input_minimal(self):
        from swiss_courts_mcp.server import SearchDecisionsInput
        inp = SearchDecisionsInput(query="Datenschutz")
        assert inp.query == "Datenschutz"
        assert inp.canton is None
        assert inp.language == Language.DE
        assert inp.limit == 20

    def test_search_input_full(self):
        from swiss_courts_mcp.server import SearchDecisionsInput
        inp = SearchDecisionsInput(
            query="Mietrecht",
            canton=Canton.ZH,
            court_level=CourtLevel.BUNDESGERICHT,
            language=Language.FR,
            date_from="2020-01-01",
            date_to="2024-12-31",
            limit=10,
        )
        assert inp.canton == Canton.ZH
        assert inp.court_level == CourtLevel.BUNDESGERICHT

    def test_search_input_query_too_short(self):
        from swiss_courts_mcp.server import SearchDecisionsInput
        with pytest.raises(Exception):
            SearchDecisionsInput(query="x")

    def test_search_input_invalid_date(self):
        from swiss_courts_mcp.server import SearchDecisionsInput
        with pytest.raises(Exception):
            SearchDecisionsInput(query="Test", date_from="not-a-date")

    def test_get_decision_input(self):
        from swiss_courts_mcp.server import GetDecisionInput
        inp = GetDecisionInput(signature="CH_BGer_005_test")
        assert inp.signature == "CH_BGer_005_test"

    def test_law_reference_input(self):
        from swiss_courts_mcp.server import SearchByLawInput
        inp = SearchByLawInput(law_reference="Art. 8 BV")
        assert inp.law_reference == "Art. 8 BV"

    def test_stats_input(self):
        from swiss_courts_mcp.server import DecisionStatsInput
        inp = DecisionStatsInput(canton=Canton.BE, year=2024)
        assert inp.canton == Canton.BE
        assert inp.year == 2024

    def test_extra_fields_forbidden(self):
        from swiss_courts_mcp.server import SearchDecisionsInput
        with pytest.raises(Exception):
            SearchDecisionsInput(query="Test", unknown_field="x")
