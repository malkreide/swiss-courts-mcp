"""Tests für den API-Client (swiss_courts_mcp.api_client)."""

import pytest

from swiss_courts_mcp.api_client import (
    build_id_query,
    build_law_reference_body,
    build_search_body,
    extract_hit,
    extract_total,
    handle_error,
    parse_law_reference,
)


# ---------------------------------------------------------------------------
# Query-Builder Tests
# ---------------------------------------------------------------------------


class TestBuildSearchBody:
    """Tests für build_search_body()."""

    def test_minimal_query(self):
        body = build_search_body(query="Datenschutz")
        assert body["size"] == 20
        assert body["from"] == 0
        assert body["sort"] == [{"date": {"order": "desc"}}]
        assert "simple_query_string" in str(body["query"])

    def test_match_all_without_query(self):
        body = build_search_body()
        assert body["query"] == {"match_all": {}}

    def test_canton_filter(self):
        body = build_search_body(query="Mietrecht", canton="ZH")
        bool_q = body["query"]["bool"]
        assert "filter" in bool_q
        assert any("hierarchy.keyword" in str(f) for f in bool_q["filter"])

    def test_court_level_filter(self):
        body = build_search_body(query="Test", court_level="bundesgericht")
        bool_q = body["query"]["bool"]
        filter_clauses = bool_q.get("filter", [])
        # Should have prefix filter for CH_BGer and CH_BGE
        assert any("prefix" in str(f) or "should" in str(f) for f in filter_clauses)

    def test_date_range(self):
        body = build_search_body(
            query="Test",
            date_from="2020-01-01",
            date_to="2024-12-31",
        )
        bool_q = body["query"]["bool"]
        filter_clauses = bool_q.get("filter", [])
        range_clause = next(f for f in filter_clauses if "range" in f)
        assert range_clause["range"]["date"]["gte"] == "2020-01-01"
        assert range_clause["range"]["date"]["lte"] == "2024-12-31"

    def test_size_limit(self):
        body = build_search_body(query="Test", size=100)
        assert body["size"] == 50  # MAX_SIZE cap

    def test_offset(self):
        body = build_search_body(query="Test", offset=20)
        assert body["from"] == 20

    def test_custom_court_prefixes(self):
        body = build_search_body(query="Test", court_prefixes=["CH_BVGE"])
        bool_q = body["query"]["bool"]
        filter_clauses = bool_q.get("filter", [])
        assert any("CH_BVGE" in str(f) for f in filter_clauses)

    def test_combined_filters(self):
        body = build_search_body(
            query="Strafrecht",
            canton="BE",
            date_from="2023-01-01",
        )
        bool_q = body["query"]["bool"]
        assert "must" in bool_q
        assert "filter" in bool_q
        assert len(bool_q["filter"]) == 2  # canton + date


class TestBuildIdQuery:
    """Tests für build_id_query()."""

    def test_id_query(self):
        body = build_id_query("CH_BGer_005_5F-23-2025_2025-07-01")
        assert body["size"] == 1
        assert body["query"]["term"]["_id"] == "CH_BGer_005_5F-23-2025_2025-07-01"


# ---------------------------------------------------------------------------
# Gesetzesreferenz-Parser Tests
# ---------------------------------------------------------------------------


class TestParseLawReference:
    """Tests für parse_law_reference()."""

    def test_standard_format(self):
        result = parse_law_reference("Art. 8 BV")
        assert result["article"] == "8"
        assert result["law"] == "BV"

    def test_or_article(self):
        result = parse_law_reference("Art. 328 OR")
        assert result["article"] == "328"
        assert result["law"] == "OR"

    def test_with_absatz(self):
        result = parse_law_reference("Art. 25 Abs. 1 DSG")
        assert result["article"] == "25"
        assert result["law"] == "DSG"

    def test_paragraph_sign(self):
        result = parse_law_reference("§ 123 StGB")
        assert result["article"] == "123"
        assert result["law"] == "StGB"

    def test_artikel_long_form(self):
        result = parse_law_reference("Artikel 8 BV")
        assert result["article"] == "8"
        assert result["law"] == "BV"

    def test_article_with_letter(self):
        result = parse_law_reference("Art. 25a DSG")
        assert result["article"] == "25a"
        assert result["law"] == "DSG"

    def test_unparseable(self):
        result = parse_law_reference("some random text")
        assert result["article"] == ""
        assert result["law"] == ""
        assert result["original"] == "some random text"

    def test_original_preserved(self):
        result = parse_law_reference("Art. 8 BV")
        assert result["original"] == "Art. 8 BV"


class TestBuildLawReferenceBody:
    """Tests für build_law_reference_body()."""

    def test_parsed_reference(self):
        body = build_law_reference_body("Art. 8 BV")
        should = body["query"]["bool"]["should"]
        # Mindestens 3 Klauseln: exakte Phrase, Nummer+Kürzel, nur Kürzel
        assert len(should) == 3
        # Höchster Boost für exakte Phrase
        assert should[0]["simple_query_string"]["boost"] == 10
        assert should[1]["simple_query_string"]["boost"] == 3
        assert should[2]["simple_query_string"]["boost"] == 1

    def test_unparseable_reference(self):
        body = build_law_reference_body("Bundesverfassung")
        should = body["query"]["bool"]["should"]
        # Nur exakte Phrase (kein Artikel/Kürzel geparst)
        assert len(should) == 1

    def test_sorted_by_score(self):
        body = build_law_reference_body("Art. 8 BV")
        assert body["sort"][0] == {"_score": {"order": "desc"}}

    def test_date_filter(self):
        body = build_law_reference_body("Art. 8 BV", date_from="2020-01-01")
        filters = body["query"]["bool"]["filter"]
        assert any("range" in f for f in filters)

    def test_size_capped(self):
        body = build_law_reference_body("Art. 8 BV", size=100)
        assert body["size"] == 50


# ---------------------------------------------------------------------------
# Extraktion Tests
# ---------------------------------------------------------------------------


SAMPLE_HIT = {
    "_id": "CH_BGer_005_5F-23-2025_2025-07-01",
    "_source": {
        "hierarchy": ["CH", "Bundesgericht"],
        "date": "2025-07-01",
        "reference": ["5F_23/2025"],
        "title": {
            "de": "Urteil zum Datenschutzgesetz",
            "fr": "Arrêt sur la loi sur la protection des données",
        },
        "abstract": {
            "de": "Das Bundesgericht bestätigt die Anwendung von Art. 25 DSG.",
            "fr": "Le Tribunal fédéral confirme l'application de l'art. 25 LPD.",
        },
        "attachment": {"language": "de"},
    },
}


class TestExtractHit:
    """Tests für extract_hit()."""

    def test_german_extraction(self):
        hit = extract_hit(SAMPLE_HIT, "de")
        assert hit["signature"] == "CH_BGer_005_5F-23-2025_2025-07-01"
        assert hit["date"] == "2025-07-01"
        assert hit["court"] == "Bundesgericht"
        assert hit["canton"] == "CH"
        assert hit["references"] == ["5F_23/2025"]
        assert "Datenschutzgesetz" in hit["title"]
        assert "Art. 25 DSG" in hit["abstract"]

    def test_french_extraction(self):
        hit = extract_hit(SAMPLE_HIT, "fr")
        assert "protection des données" in hit["title"]

    def test_fallback_to_german(self):
        hit = extract_hit(SAMPLE_HIT, "it")
        # Italian not available, should fall back to German
        assert "Datenschutzgesetz" in hit["title"]

    def test_empty_hierarchy(self):
        sparse = {"_id": "test", "_source": {"hierarchy": [], "date": ""}}
        hit = extract_hit(sparse, "de")
        assert hit["court"] == ""
        assert hit["canton"] == ""

    def test_string_reference(self):
        single_ref = {
            "_id": "test",
            "_source": {
                "hierarchy": ["ZH", "Obergericht"],
                "reference": "123/2025",
                "date": "2025-01-01",
            },
        }
        hit = extract_hit(single_ref, "de")
        assert hit["references"] == ["123/2025"]


class TestExtractTotal:
    """Tests für extract_total()."""

    def test_dict_total(self):
        result = {"hits": {"total": {"value": 1234}}}
        assert extract_total(result) == 1234

    def test_int_total(self):
        result = {"hits": {"total": 42}}
        assert extract_total(result) == 42

    def test_missing_total(self):
        result = {"hits": {}}
        assert extract_total(result) == 0


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestHandleError:
    """Tests für handle_error()."""

    def test_generic_error(self):
        msg = handle_error(ValueError("test"))
        assert "ValueError" in msg
        assert "test" in msg

    def test_timeout_error(self):
        import httpx
        msg = handle_error(httpx.ReadTimeout("timeout"))
        assert "Timeout" in msg

    def test_connect_error(self):
        import httpx
        msg = handle_error(httpx.ConnectError("failed"))
        assert "Verbindung" in msg


# ---------------------------------------------------------------------------
# Live API Tests (optional, mit --run-live)
# ---------------------------------------------------------------------------


@pytest.mark.live
async def test_live_search():
    """Live-Test: Suche nach 'Datenschutz'."""
    from swiss_courts_mcp.api_client import search_decisions
    body = build_search_body(query="Datenschutz", size=3)
    result = await search_decisions(body)
    total = extract_total(result)
    assert total > 0
    hits = result["hits"]["hits"]
    assert len(hits) > 0


@pytest.mark.live
async def test_live_taxonomy():
    """Live-Test: Gerichts-Taxonomie abrufen."""
    from swiss_courts_mcp.api_client import get_court_taxonomy
    taxonomy = await get_court_taxonomy()
    assert taxonomy is not None
    assert len(taxonomy) > 0
