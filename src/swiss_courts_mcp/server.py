"""
Swiss Courts MCP Server
========================
MCP-Server für Schweizer Gerichtsentscheide via entscheidsuche.ch.
Aggregiert Urteile des Bundesgerichts, Bundesverwaltungsgerichts,
Bundesstrafgerichts und kantonaler Gerichte aller 26 Kantone.

Datenquelle: https://entscheidsuche.ch
Lizenz: Freie Nutzung (kein API-Key nötig)

Synergie mit fedlex-mcp: Gesetze (SR) + Rechtsprechung = vollständige Rechtsrecherche.

Transport: Dual — stdio (lokal) und streamable-http (Cloud)
"""

from __future__ import annotations

import sys
from enum import StrEnum

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from swiss_courts_mcp import api_client

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

MAX_RESULTS_DEFAULT = 20
MAX_RESULTS_LIMIT = 50

SOURCE_FOOTER = "\n---\n*Quelle: entscheidsuche.ch — Schweizer Gerichtsentscheide*"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Canton(StrEnum):
    """Schweizer Kantone."""
    ZH = "ZH"
    BE = "BE"
    LU = "LU"
    UR = "UR"
    SZ = "SZ"
    OW = "OW"
    NW = "NW"
    GL = "GL"
    ZG = "ZG"
    FR = "FR"
    SO = "SO"
    BS = "BS"
    BL = "BL"
    SH = "SH"
    AR = "AR"
    AI = "AI"
    SG = "SG"
    GR = "GR"
    AG = "AG"
    TG = "TG"
    TI = "TI"
    VD = "VD"
    VS = "VS"
    NE = "NE"
    GE = "GE"
    JU = "JU"


class CourtLevel(StrEnum):
    """Gerichtsebene (Bund)."""
    BUNDESGERICHT = "bundesgericht"
    BUNDESVERWALTUNGSGERICHT = "bundesverwaltungsgericht"
    BUNDESSTRAFGERICHT = "bundesstrafgericht"
    BUNDESPATENTGERICHT = "bundespatentgericht"


class Language(StrEnum):
    """Sprachen."""
    DE = "de"
    FR = "fr"
    IT = "it"


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "swiss_courts_mcp",
    instructions=(
        "MCP-Server für Schweizer Gerichtsentscheide via entscheidsuche.ch. "
        "Zugriff auf Urteile des Bundesgerichts (BGer), Bundesverwaltungsgerichts (BVGer), "
        "Bundesstrafgerichts (BStGer) und kantonaler Gerichte aller 26 Kantone. "
        "Ideal in Kombination mit fedlex-mcp für vollständige Rechtsrecherche "
        "(Gesetzestext + Rechtsprechung). "
        "Alle Daten stammen von entscheidsuche.ch (öffentlich, kein API-Key nötig)."
    ),
)


# ---------------------------------------------------------------------------
# Input-Modelle
# ---------------------------------------------------------------------------


class SearchDecisionsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description=(
            "Suchbegriff(e) für Volltextsuche in Gerichtsentscheiden. "
            "Unterstützt: \"exakte Phrasen\", AND/OR Operatoren. "
            "Beispiele: 'Datenschutz', 'Mietrecht Kündigung', '\"faire Verfahren\"'"
        ),
        min_length=2,
        max_length=500,
    )
    canton: Canton | None = Field(
        default=None,
        description="Kanton filtern (z.B. 'ZH', 'BE', 'GE'). Leer = alle Kantone.",
    )
    court_level: CourtLevel | None = Field(
        default=None,
        description=(
            "Gerichtsebene: 'bundesgericht', 'bundesverwaltungsgericht', "
            "'bundesstrafgericht', 'bundespatentgericht'. Leer = alle Ebenen."
        ),
    )
    language: Language = Field(
        default=Language.DE,
        description="Ergebnissprache für Titel/Abstract: 'de', 'fr', 'it'.",
    )
    date_from: str | None = Field(
        default=None,
        description="Frühestes Datum (ISO: YYYY-MM-DD), z.B. '2020-01-01'.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    date_to: str | None = Field(
        default=None,
        description="Spätestes Datum (ISO: YYYY-MM-DD), z.B. '2025-12-31'.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    limit: int = Field(
        default=MAX_RESULTS_DEFAULT,
        ge=1,
        le=MAX_RESULTS_LIMIT,
        description=f"Maximale Trefferzahl (1–{MAX_RESULTS_LIMIT}).",
    )


class GetDecisionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    signature: str = Field(
        ...,
        description=(
            "Eindeutige Signatur des Entscheids, "
            "z.B. 'CH_BGer_005_5F-23-2025_2025-07-01' oder 'ZH_Obergericht_...'. "
            "Wird von search_court_decisions zurückgegeben."
        ),
        min_length=5,
        max_length=200,
    )
    language: Language = Field(
        default=Language.DE,
        description="Sprache für Titel/Abstract.",
    )


class SearchBGerInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description="Suchbegriff(e) in Bundesgerichtsentscheiden.",
        min_length=2,
        max_length=500,
    )
    chamber: str | None = Field(
        default=None,
        description=(
            "BGer-Abteilung filtern, z.B. "
            "'I. öffentlich-rechtliche Abteilung', 'II. zivilrechtliche Abteilung'. "
            "Leer = alle Abteilungen."
        ),
    )
    date_from: str | None = Field(
        default=None,
        description="Frühestes Datum (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    date_to: str | None = Field(
        default=None,
        description="Spätestes Datum (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    language: Language = Field(default=Language.DE)
    limit: int = Field(default=MAX_RESULTS_DEFAULT, ge=1, le=MAX_RESULTS_LIMIT)


class SearchByLawInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    law_reference: str = Field(
        ...,
        description=(
            "Gesetzesreferenz für die Praxis-Suche. "
            "Beispiele: 'Art. 8 BV', 'Art. 328 OR', 'Art. 25 DSG', '§ 123 StGB'. "
            "Synergie mit fedlex-mcp: Gesetz nachschlagen, dann Praxis dazu finden."
        ),
        min_length=3,
        max_length=200,
    )
    language: Language = Field(default=Language.DE)
    date_from: str | None = Field(
        default=None, description="Frühestes Datum (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    date_to: str | None = Field(
        default=None, description="Spätestes Datum (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    limit: int = Field(default=MAX_RESULTS_DEFAULT, ge=1, le=MAX_RESULTS_LIMIT)


class ListCourtsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    canton: Canton | None = Field(
        default=None,
        description="Gerichte eines bestimmten Kantons. Leer = alle Gerichte.",
    )


class RecentDecisionsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    canton: Canton | None = Field(default=None, description="Kanton filtern.")
    court_level: CourtLevel | None = Field(default=None, description="Gerichtsebene filtern.")
    language: Language = Field(default=Language.DE)
    limit: int = Field(default=MAX_RESULTS_DEFAULT, ge=1, le=MAX_RESULTS_LIMIT)


class DecisionStatsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    canton: Canton | None = Field(default=None, description="Kanton filtern.")
    year: int | None = Field(
        default=None,
        description="Jahr filtern, z.B. 2024.",
        ge=2000,
        le=2030,
    )


# ---------------------------------------------------------------------------
# Formatierung
# ---------------------------------------------------------------------------


def format_hit(hit: dict, idx: int) -> str:
    """Formatiert einen einzelnen Treffer als Markdown."""
    refs = ", ".join(hit["references"]) if hit["references"] else "—"
    abstract = hit["abstract"]
    if len(abstract) > 300:
        abstract = abstract[:297] + "..."

    lines = [
        f"### {idx}. {hit['court']}",
        f"- **Datum:** {hit['date']}",
        f"- **Referenz:** {refs}",
        f"- **Signatur:** `{hit['signature']}`",
    ]
    if hit["title"]:
        lines.append(f"- **Titel:** {hit['title']}")
    if abstract:
        lines.append(f"- **Zusammenfassung:** {abstract}")
    lines.append(f"- **Link:** [Volltext]({hit['url']})")
    return "\n".join(lines)


def format_decision_detail(hit: dict) -> str:
    """Formatiert einen einzelnen Entscheid als detaillierte Markdown-Ansicht."""
    refs = ", ".join(hit["references"]) if hit["references"] else "—"
    lines = [
        "## Gerichtsentscheid",
        "",
        "| Feld | Wert |",
        "|------|------|",
        f"| **Gericht** | {hit['court']} |",
        f"| **Kanton** | {hit['canton']} |",
        f"| **Datum** | {hit['date']} |",
        f"| **Referenz** | {refs} |",
        f"| **Signatur** | `{hit['signature']}` |",
        f"| **Sprache** | {hit['language']} |",
        f"| **Volltext** | [Link]({hit['url']}) |",
    ]
    if hit["title"]:
        lines.extend(["", "### Titel", hit["title"]])
    if hit["abstract"]:
        lines.extend(["", "### Zusammenfassung", hit["abstract"]])
    return "\n".join(lines)


def result_header(count: int, total: int, desc: str) -> str:
    """Standardisierter Ergebnisheader."""
    if total > count:
        return f"## {desc}\n**Treffer:** {count} von {total} angezeigt\n"
    return f"## {desc}\n**Treffer:** {total}\n"


# ---------------------------------------------------------------------------
# Tool 1: Volltextsuche
# ---------------------------------------------------------------------------


@mcp.tool(
    name="search_court_decisions",
    annotations={
        "title": "Gerichtsentscheide suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def search_court_decisions(params: SearchDecisionsInput) -> str:
    """Volltextsuche in Schweizer Gerichtsentscheiden.

    Durchsucht Urteile aller Schweizer Gerichte (Bund + Kantone) via entscheidsuche.ch.
    Unterstützt Filter nach Kanton, Gerichtsebene, Datumsbereich.
    """
    try:
        body = api_client.build_search_body(
            query=params.query,
            canton=params.canton.value if params.canton else None,
            court_level=params.court_level.value if params.court_level else None,
            date_from=params.date_from,
            date_to=params.date_to,
            size=params.limit,
        )
        result = await api_client.search_decisions(body)
        total = api_client.extract_total(result)

        if total == 0:
            return f"Keine Entscheide gefunden für: **{params.query}**\n\nTipps:\n- Andere Suchbegriffe versuchen\n- Filter entfernen (Kanton, Datum)" + SOURCE_FOOTER

        hits = [
            api_client.extract_hit(h, params.language.value)
            for h in result.get("hits", {}).get("hits", [])
        ]

        parts = [result_header(len(hits), total, f"Gerichtsentscheide: «{params.query}»")]
        for i, hit in enumerate(hits, 1):
            parts.append(format_hit(hit, i))

        return "\n\n".join(parts) + SOURCE_FOOTER

    except Exception as e:
        return api_client.handle_error(e)


# ---------------------------------------------------------------------------
# Tool 2: Einzelnes Urteil
# ---------------------------------------------------------------------------


@mcp.tool(
    name="get_court_decision",
    annotations={
        "title": "Gerichtsentscheid abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_court_decision(params: GetDecisionInput) -> str:
    """Ruft einen einzelnen Gerichtsentscheid anhand seiner Signatur ab.

    Die Signatur wird von search_court_decisions zurückgegeben.
    Liefert vollständige Metadaten inkl. Titel, Abstract, Gericht und Link zum Volltext.
    """
    try:
        hit_raw = await api_client.get_decision_by_id(params.signature)
        if not hit_raw:
            return f"Entscheid nicht gefunden: `{params.signature}`\n\nBitte Signatur prüfen."

        hit = api_client.extract_hit(hit_raw, params.language.value)
        return format_decision_detail(hit) + SOURCE_FOOTER

    except Exception as e:
        return api_client.handle_error(e)


# ---------------------------------------------------------------------------
# Tool 3: BGer-Spezialsuche
# ---------------------------------------------------------------------------


@mcp.tool(
    name="search_bger_decisions",
    annotations={
        "title": "Bundesgerichtsentscheide suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def search_bger_decisions(params: SearchBGerInput) -> str:
    """Sucht gezielt in Bundesgerichtsentscheiden (BGer/BGE).

    Optionaler Filter nach Abteilung (z.B. 'I. öffentlich-rechtliche Abteilung').
    Das Bundesgericht ist die höchste richterliche Instanz der Schweiz.
    """
    try:
        # BGer + BGE Prefixes
        prefixes = ["CH_BGer", "CH_BGE"]

        # Bei Abteilungsfilter den Suchbegriff erweitern
        query = params.query
        if params.chamber:
            query = f"{query} \"{params.chamber}\""

        body = api_client.build_search_body(
            query=query,
            court_prefixes=prefixes,
            date_from=params.date_from,
            date_to=params.date_to,
            size=params.limit,
        )
        result = await api_client.search_decisions(body)
        total = api_client.extract_total(result)

        if total == 0:
            return f"Keine Bundesgerichtsentscheide gefunden für: **{params.query}**" + SOURCE_FOOTER

        hits = [
            api_client.extract_hit(h, params.language.value)
            for h in result.get("hits", {}).get("hits", [])
        ]

        parts = [result_header(len(hits), total, f"Bundesgericht: «{params.query}»")]
        for i, hit in enumerate(hits, 1):
            parts.append(format_hit(hit, i))

        return "\n\n".join(parts) + SOURCE_FOOTER

    except Exception as e:
        return api_client.handle_error(e)


# ---------------------------------------------------------------------------
# Tool 4: Suche nach Gesetzesartikel
# ---------------------------------------------------------------------------


@mcp.tool(
    name="search_by_law_reference",
    annotations={
        "title": "Entscheide zu Gesetzesartikel suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def search_by_law_reference(params: SearchByLawInput) -> str:
    """Sucht Gerichtsentscheide die einen bestimmten Gesetzesartikel zitieren.

    Mehrstufige Suche: exakte Phrase (höchste Relevanz) + Artikelnummer/Kürzel
    (breitere Abdeckung). Findet auch Varianten wie 'Artikel 8 BV', 'art. 8 Cst.'

    Synergie mit fedlex-mcp: Zuerst Gesetz nachschlagen (fedlex_search_laws),
    dann Praxis dazu finden (search_by_law_reference).

    Beispiele: 'Art. 8 BV' (Rechtsgleichheit), 'Art. 328 OR' (Persönlichkeitsschutz),
    'Art. 25 DSG' (Auskunftsrecht).
    """
    try:
        body = api_client.build_law_reference_body(
            law_reference=params.law_reference,
            date_from=params.date_from,
            date_to=params.date_to,
            size=params.limit,
        )
        result = await api_client.search_decisions(body)
        total = api_client.extract_total(result)

        if total == 0:
            return (
                f"Keine Entscheide gefunden zu: **{params.law_reference}**\n\n"
                f"Tipps:\n"
                f"- Schreibweise prüfen (z.B. 'Art. 8 BV' statt 'Art.8BV')\n"
                f"- Andere Formulierung versuchen (z.B. '8 BV' statt 'Art. 8 BV')\n"
                f"- Mit fedlex-mcp die korrekte Gesetzesbezeichnung nachschlagen"
            ) + SOURCE_FOOTER

        hits = [
            api_client.extract_hit(h, params.language.value)
            for h in result.get("hits", {}).get("hits", [])
        ]

        parts = [result_header(
            len(hits), total,
            f"Rechtsprechung zu {params.law_reference}"
        )]
        for i, hit in enumerate(hits, 1):
            parts.append(format_hit(hit, i))

        return "\n\n".join(parts) + SOURCE_FOOTER

    except Exception as e:
        return api_client.handle_error(e)


# ---------------------------------------------------------------------------
# Tool 5: Gerichte auflisten
# ---------------------------------------------------------------------------


@mcp.tool(
    name="list_courts",
    annotations={
        "title": "Verfügbare Gerichte auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def list_courts(params: ListCourtsInput) -> str:
    """Listet alle in entscheidsuche.ch indexierten Gerichte auf.

    Zeigt Bundesgerichte und kantonale Gerichte hierarchisch.
    Optional nach Kanton filterbar.
    """
    try:
        taxonomy = await api_client.get_court_taxonomy()

        lines = ["## Verfügbare Gerichte\n"]

        if isinstance(taxonomy, dict):
            # Facetten_alle.json hat verschiedene mögliche Strukturen
            # Wir verarbeiten sie pragmatisch
            filtered = {}
            for key, value in taxonomy.items():
                if params.canton:
                    if key.upper() == params.canton.value or key.startswith(params.canton.value):
                        filtered[key] = value
                else:
                    filtered[key] = value

            if not filtered:
                return f"Keine Gerichte gefunden für Kanton: {params.canton}" + SOURCE_FOOTER

            # Bundesgerichte zuerst
            federal_keys = [k for k in filtered if k.startswith("CH")]
            cantonal_keys = sorted([k for k in filtered if not k.startswith("CH")])

            if federal_keys and not params.canton:
                lines.append("### Bundesgerichte")
                for key in sorted(federal_keys):
                    val = filtered[key]
                    if isinstance(val, dict):
                        name = val.get("name", val.get("label", key))
                        lines.append(f"- **{key}**: {name}")
                    elif isinstance(val, str):
                        lines.append(f"- **{key}**: {val}")
                    elif isinstance(val, list):
                        lines.append(f"- **{key}**: {len(val)} Untergerichte")
                lines.append("")

            if cantonal_keys:
                lines.append("### Kantonale Gerichte")
                for key in cantonal_keys:
                    val = filtered[key]
                    if isinstance(val, dict):
                        name = val.get("name", val.get("label", key))
                        lines.append(f"- **{key}**: {name}")
                    elif isinstance(val, str):
                        lines.append(f"- **{key}**: {val}")
                    elif isinstance(val, list):
                        lines.append(f"- **{key}**: {len(val)} Gerichte")

        elif isinstance(taxonomy, list):
            for entry in taxonomy:
                if isinstance(entry, dict):
                    canton_code = entry.get("canton", entry.get("id", ""))
                    name = entry.get("name", entry.get("label", ""))
                    if params.canton and canton_code.upper() != params.canton.value:
                        continue
                    lines.append(f"- **{canton_code}**: {name}")

        return "\n".join(lines) + SOURCE_FOOTER

    except Exception as e:
        return api_client.handle_error(e)


# ---------------------------------------------------------------------------
# Tool 6: Neueste Entscheide
# ---------------------------------------------------------------------------


@mcp.tool(
    name="get_recent_decisions",
    annotations={
        "title": "Neueste Gerichtsentscheide",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_recent_decisions(params: RecentDecisionsInput) -> str:
    """Gibt die neuesten Gerichtsentscheide zurück.

    Chronologisch sortiert (neueste zuerst). Filterbar nach Kanton und Gerichtsebene.
    Nützlich um aktuelle Rechtsprechungsentwicklungen zu verfolgen.
    """
    try:
        body = api_client.build_search_body(
            canton=params.canton.value if params.canton else None,
            court_level=params.court_level.value if params.court_level else None,
            size=params.limit,
        )
        result = await api_client.search_decisions(body)
        total = api_client.extract_total(result)

        if total == 0:
            return "Keine aktuellen Entscheide gefunden." + SOURCE_FOOTER

        hits = [
            api_client.extract_hit(h, params.language.value)
            for h in result.get("hits", {}).get("hits", [])
        ]

        desc = "Neueste Gerichtsentscheide"
        if params.canton:
            desc += f" — Kanton {params.canton.value}"
        if params.court_level:
            level_names = {
                "bundesgericht": "Bundesgericht",
                "bundesverwaltungsgericht": "Bundesverwaltungsgericht",
                "bundesstrafgericht": "Bundesstrafgericht",
                "bundespatentgericht": "Bundespatentgericht",
            }
            desc += f" — {level_names.get(params.court_level.value, params.court_level.value)}"

        parts = [result_header(len(hits), total, desc)]
        for i, hit in enumerate(hits, 1):
            parts.append(format_hit(hit, i))

        return "\n\n".join(parts) + SOURCE_FOOTER

    except Exception as e:
        return api_client.handle_error(e)


# ---------------------------------------------------------------------------
# Tool 7: Statistiken
# ---------------------------------------------------------------------------


@mcp.tool(
    name="get_decision_statistics",
    annotations={
        "title": "Entscheid-Statistiken",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_decision_statistics(params: DecisionStatsInput) -> str:
    """Gibt Statistiken über die Anzahl indexierter Gerichtsentscheide zurück.

    Zeigt Gesamtzahl und Verteilung. Optional filterbar nach Kanton oder Jahr.
    """
    try:
        # Aggregations-Query für Statistiken
        body: dict = {
            "size": 0,  # Keine Dokumente, nur Aggregationen
            "aggs": {
                "by_canton": {
                    "terms": {"field": "hierarchy.keyword", "size": 50}
                },
                "by_year": {
                    "date_histogram": {
                        "field": "date",
                        "calendar_interval": "year",
                        "order": {"_key": "desc"},
                        "min_doc_count": 1,
                    }
                },
            },
        }

        filter_clauses: list[dict] = []
        if params.canton:
            filter_clauses.append({"term": {"hierarchy.keyword": params.canton.value}})
        if params.year:
            filter_clauses.append({
                "range": {
                    "date": {
                        "gte": f"{params.year}-01-01",
                        "lte": f"{params.year}-12-31",
                    }
                }
            })

        if filter_clauses:
            body["query"] = {"bool": {"filter": filter_clauses}}
        else:
            body["query"] = {"match_all": {}}

        result = await api_client.search_decisions(body)
        total = api_client.extract_total(result)

        lines = ["## Entscheid-Statistiken\n"]
        lines.append(f"**Gesamtzahl:** {total:,} Entscheide")

        if params.canton:
            lines.append(f"**Filter:** Kanton {params.canton.value}")
        if params.year:
            lines.append(f"**Filter:** Jahr {params.year}")

        # Aggregationen auswerten
        aggs = result.get("aggregations", {})

        canton_buckets = aggs.get("by_canton", {}).get("buckets", [])
        if canton_buckets:
            lines.extend(["", "### Nach Kanton/Gericht", ""])
            lines.append("| Kanton/Gericht | Anzahl |")
            lines.append("|----------------|--------|")
            for bucket in canton_buckets[:20]:
                key = bucket.get("key", "")
                count = bucket.get("doc_count", 0)
                lines.append(f"| {key} | {count:,} |")

        year_buckets = aggs.get("by_year", {}).get("buckets", [])
        if year_buckets:
            lines.extend(["", "### Nach Jahr", ""])
            lines.append("| Jahr | Anzahl |")
            lines.append("|------|--------|")
            for bucket in year_buckets[:10]:
                key_str = bucket.get("key_as_string", "")
                year_val = key_str[:4] if key_str else str(bucket.get("key", ""))
                count = bucket.get("doc_count", 0)
                lines.append(f"| {year_val} | {count:,} |")

        return "\n".join(lines) + SOURCE_FOOTER

    except Exception as e:
        return api_client.handle_error(e)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def main():
    """Startet den MCP-Server mit Dual-Transport (stdio oder streamable-http)."""
    if "--http" in sys.argv:
        port = 8000
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
