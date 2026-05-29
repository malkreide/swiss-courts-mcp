"""
Swiss Courts MCP Server
========================
MCP-Server für Schweizer Gerichtsentscheide via entscheidsuche.ch.
Aggregiert Urteile des Bundesgerichts, Bundesverwaltungsgerichts,
Bundesstrafgerichts und kantonaler Gerichte aller 26 Kantone.

Datenquelle: https://entscheidsuche.ch
Lizenz: Freie Nutzung (kein API-Key nötig)

Synergie mit fedlex-mcp: Gesetze (SR) + Rechtsprechung = vollständige Rechtsrecherche.

Transport: Dual — stdio (lokal, ohne Auth) und streamable-http (Cloud, mit Auth).
MCP-Protokoll: siehe `PROTOCOL_VERSION` (von der FastMCP-SDK-Version bestimmt).
Phase: 1 (read-only) — siehe ROADMAP.md.
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, ConfigDict, Field

from swiss_courts_mcp import api_client
from swiss_courts_mcp.config import Settings
from swiss_courts_mcp.logging_config import configure_logging, get_logger
from swiss_courts_mcp.models import (
    DATA_LICENSE,
    DATA_SOURCE,
    DATA_SOURCE_URL,
    DecisionResult,
    SearchResponse,
)

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

MAX_RESULTS_DEFAULT = 20
MAX_RESULTS_LIMIT = 50

# Bewusst gepinnte, getestete MCP-Protocol-Version (ARCH-012). Kein "latest":
# ein SDK-Bump muss bewusst nachgezogen werden (Wert + CHANGELOG + README).
# tests/test_protocol.py erkennt Drift gegen die installierte SDK-Version.
PROTOCOL_VERSION = "2025-11-25"

# Maschinen-/menschenlesbarer Quellen- + Lizenz-Footer (CH-004).
SOURCE_FOOTER = (
    f"\n---\n*Quelle: {DATA_SOURCE} ({DATA_SOURCE_URL}) · "
    f"Lizenz: {DATA_LICENSE}*"
)

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
        max_length=200,
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
# Context-Helfer (SDK-003)
# ---------------------------------------------------------------------------


def _client(ctx: Context | None) -> httpx.AsyncClient | None:
    """Holt den gepoolten httpx-Client aus dem Lifespan-Kontext (SDK-001)."""
    try:
        return ctx.request_context.lifespan_context.get("client")  # type: ignore[union-attr]
    except Exception:
        return None


async def _progress(ctx: Context | None, current: float, total: float) -> None:
    """Best-effort Progress-Report; bricht den Tool-Call nie ab."""
    if ctx is None:
        return
    try:
        await ctx.report_progress(progress=current, total=total)
    except Exception:
        pass


async def _info(ctx: Context | None, message: str, **kw) -> None:
    if ctx is None:
        return
    try:
        await ctx.info(message)
    except Exception:
        pass
    log.info(message, **kw)


def _match_type(total: int) -> str:
    """ARCH-003: maschinenlesbarer Treffer-Typ."""
    return "exact" if total > 0 else "none"


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
        f"| **Quelle / Lizenz** | {DATA_SOURCE} — {DATA_LICENSE} |",
    ]
    if hit["title"]:
        lines.extend(["", "### Titel", hit["title"]])
    if hit["abstract"]:
        lines.extend(["", "### Zusammenfassung", hit["abstract"]])
    return "\n".join(lines)


def result_header(count: int, total: int, desc: str, match_type: str | None = None) -> str:
    """Standardisierter Ergebnisheader (inkl. optionalem Treffer-Typ, ARCH-003)."""
    mt = f"\n**Treffer-Typ:** {match_type}" if match_type else ""
    if total > count:
        return f"## {desc}\n**Treffer:** {count} von {total} angezeigt{mt}\n"
    return f"## {desc}\n**Treffer:** {total}{mt}\n"


def _build_response(query: str, total: int, hits: list[dict]) -> SearchResponse:
    """Baut den strukturierten Such-Envelope (SDK-002)."""
    return SearchResponse(
        query=query,
        match_type=_match_type(total),  # type: ignore[arg-type]
        count=len(hits),
        total=total,
        results=[DecisionResult(**h) for h in hits],
    )


def _result(markdown: str, structured: BaseModel | dict) -> CallToolResult:
    """Liefert kuratiertes Markdown (content) UND maschinenlesbares
    structuredContent in einem Tool-Result (SDK-002).

    Die Tools werden mit ``structured_output=False`` registriert, damit FastMCP
    dieses ``CallToolResult`` unverändert durchreicht.
    """
    sc = structured.model_dump(mode="json") if isinstance(structured, BaseModel) else structured
    return CallToolResult(content=[TextContent(type="text", text=markdown)], structuredContent=sc)


# ---------------------------------------------------------------------------
# Tool-Implementierungen (registriert via register_tools)
# ---------------------------------------------------------------------------


async def search_court_decisions(params: SearchDecisionsInput, ctx: Context) -> CallToolResult:
    """Volltextsuche in Schweizer Gerichtsentscheiden.

    Use-Case: juristische Recherche über alle Schweizer Gerichte (Bund + Kantone)
    via entscheidsuche.ch. Unterstützt Filter nach Kanton, Gerichtsebene und
    Datumsbereich. Liefert abgeschlossene Treffer inkl. Titel, Abstract und
    Volltext-Link, kuratiertes Markdown sowie einen maschinenlesbaren
    Response-Envelope (source, license, match_type, count, total, results).
    """
    await _progress(ctx, 0, 1)
    try:
        body = api_client.build_search_body(
            query=params.query,
            canton=params.canton.value if params.canton else None,
            court_level=params.court_level.value if params.court_level else None,
            date_from=params.date_from,
            date_to=params.date_to,
            size=params.limit,
        )
        result = await api_client.search_decisions(body, client=_client(ctx))
        total = api_client.extract_total(result)
        await _progress(ctx, 1, 1)

        if total == 0:
            await _info(ctx, "search_empty", tool="search_court_decisions")
            md = (
                f"Keine Entscheide gefunden für: **{params.query}** "
                "(Treffer-Typ: none)\n\nTipps:\n"
                "- Andere Suchbegriffe versuchen\n- Filter entfernen (Kanton, Datum)"
            ) + SOURCE_FOOTER
            return _result(md, _build_response(params.query, 0, []))

        hits = [
            api_client.extract_hit(h, params.language.value)
            for h in result.get("hits", {}).get("hits", [])
        ]
        envelope = _build_response(params.query, total, hits)
        parts = [result_header(
            envelope.count, total, f"Gerichtsentscheide: «{params.query}»",
            match_type=envelope.match_type,
        )]
        for i, hit in enumerate(hits, 1):
            parts.append(format_hit(hit, i))
        return _result("\n\n".join(parts) + SOURCE_FOOTER, envelope)

    except Exception as e:  # noqa: BLE001 — wird maskiert + als isError gemeldet
        raise ToolError(api_client.handle_error(e)) from None


async def get_court_decision(params: GetDecisionInput, ctx: Context) -> CallToolResult:
    """Ruft einen einzelnen Gerichtsentscheid anhand seiner Signatur ab.

    Use-Case: Detail-Ansicht eines konkreten Urteils (Signatur aus
    search_court_decisions). Exakter Lookup ohne Fuzzy-Fallback.
    """
    try:
        hit_raw = await api_client.get_decision_by_id(params.signature, client=_client(ctx))
        if not hit_raw:
            md = (
                f"Entscheid nicht gefunden: `{params.signature}` (Treffer-Typ: none)\n\n"
                "Bitte Signatur prüfen."
            ) + SOURCE_FOOTER
            return _result(md, {
                "source": DATA_SOURCE, "license": DATA_LICENSE,
                "match_type": "none", "decision": None,
            })

        hit = api_client.extract_hit(hit_raw, params.language.value)
        decision = DecisionResult(**hit)
        return _result(format_decision_detail(hit) + SOURCE_FOOTER, {
            "source": DATA_SOURCE, "license": DATA_LICENSE,
            "match_type": "exact", "decision": decision.model_dump(mode="json"),
        })

    except Exception as e:  # noqa: BLE001
        raise ToolError(api_client.handle_error(e)) from None


async def search_bger_decisions(params: SearchBGerInput, ctx: Context) -> CallToolResult:
    """Sucht gezielt in Bundesgerichtsentscheiden (BGer/BGE).

    Use-Case: höchstrichterliche Rechtsprechung mit optionalem Abteilungsfilter.
    """
    await _progress(ctx, 0, 1)
    try:
        prefixes = ["CH_BGer", "CH_BGE"]
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
        result = await api_client.search_decisions(body, client=_client(ctx))
        total = api_client.extract_total(result)
        await _progress(ctx, 1, 1)

        if total == 0:
            md = (
                f"Keine Bundesgerichtsentscheide gefunden für: **{params.query}** "
                "(Treffer-Typ: none)"
            ) + SOURCE_FOOTER
            return _result(md, _build_response(params.query, 0, []))

        hits = [
            api_client.extract_hit(h, params.language.value)
            for h in result.get("hits", {}).get("hits", [])
        ]
        envelope = _build_response(params.query, total, hits)
        parts = [result_header(
            envelope.count, total, f"Bundesgericht: «{params.query}»",
            match_type=envelope.match_type,
        )]
        for i, hit in enumerate(hits, 1):
            parts.append(format_hit(hit, i))
        return _result("\n\n".join(parts) + SOURCE_FOOTER, envelope)

    except Exception as e:  # noqa: BLE001
        raise ToolError(api_client.handle_error(e)) from None


async def search_by_law_reference(params: SearchByLawInput, ctx: Context) -> CallToolResult:
    """Sucht Gerichtsentscheide die einen bestimmten Gesetzesartikel zitieren.

    Use-Case: Praxis zu einer Norm finden. Mehrstufige Suche: exakte Phrase
    (höchste Relevanz) + Artikelnummer/Kürzel (breitere Abdeckung). Synergie mit
    fedlex-mcp: zuerst Gesetz nachschlagen, dann Praxis dazu finden.
    Beispiele: 'Art. 8 BV', 'Art. 328 OR', 'Art. 25 DSG'.
    """
    await _progress(ctx, 0, 1)
    try:
        body = api_client.build_law_reference_body(
            law_reference=params.law_reference,
            date_from=params.date_from,
            date_to=params.date_to,
            size=params.limit,
        )
        result = await api_client.search_decisions(body, client=_client(ctx))
        total = api_client.extract_total(result)
        await _progress(ctx, 1, 1)

        if total == 0:
            md = (
                f"Keine Entscheide gefunden zu: **{params.law_reference}** "
                "(Treffer-Typ: none)\n\n"
                "Tipps:\n"
                "- Schreibweise prüfen (z.B. 'Art. 8 BV' statt 'Art.8BV')\n"
                "- Andere Formulierung versuchen (z.B. '8 BV' statt 'Art. 8 BV')\n"
                "- Mit fedlex-mcp die korrekte Gesetzesbezeichnung nachschlagen"
            ) + SOURCE_FOOTER
            return _result(md, _build_response(params.law_reference, 0, []))

        hits = [
            api_client.extract_hit(h, params.language.value)
            for h in result.get("hits", {}).get("hits", [])
        ]
        envelope = _build_response(params.law_reference, total, hits)
        parts = [result_header(
            envelope.count, total, f"Rechtsprechung zu {params.law_reference}",
            match_type=envelope.match_type,
        )]
        for i, hit in enumerate(hits, 1):
            parts.append(format_hit(hit, i))
        return _result("\n\n".join(parts) + SOURCE_FOOTER, envelope)

    except Exception as e:  # noqa: BLE001
        raise ToolError(api_client.handle_error(e)) from None


async def list_courts(params: ListCourtsInput, ctx: Context) -> CallToolResult:
    """Listet alle in entscheidsuche.ch indexierten Gerichte auf.

    Use-Case: Überblick über verfügbare Bundes- und Kantonsgerichte,
    optional nach Kanton gefiltert.
    """
    try:
        taxonomy = await api_client.get_court_taxonomy(client=_client(ctx))

        lines = ["## Verfügbare Gerichte\n"]
        court_keys: list[str] = []

        if isinstance(taxonomy, dict):
            filtered = {}
            for key, value in taxonomy.items():
                if params.canton:
                    if key.upper() == params.canton.value or key.startswith(params.canton.value):
                        filtered[key] = value
                else:
                    filtered[key] = value

            if not filtered:
                return _result(
                    f"Keine Gerichte gefunden für Kanton: {params.canton}" + SOURCE_FOOTER,
                    {"source": DATA_SOURCE, "license": DATA_LICENSE,
                     "type": "court_taxonomy", "count": 0, "courts": []},
                )

            court_keys = sorted(filtered.keys())
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
                    court_keys.append(canton_code)
                    lines.append(f"- **{canton_code}**: {name}")

        return _result("\n".join(lines) + SOURCE_FOOTER, {
            "source": DATA_SOURCE, "license": DATA_LICENSE,
            "type": "court_taxonomy", "count": len(court_keys), "courts": court_keys,
        })

    except Exception as e:  # noqa: BLE001
        raise ToolError(api_client.handle_error(e)) from None


async def get_recent_decisions(params: RecentDecisionsInput, ctx: Context) -> CallToolResult:
    """Gibt die neuesten Gerichtsentscheide zurück.

    Use-Case: aktuelle Rechtsprechungsentwicklungen verfolgen. Chronologisch
    sortiert, filterbar nach Kanton und Gerichtsebene.
    """
    try:
        body = api_client.build_search_body(
            canton=params.canton.value if params.canton else None,
            court_level=params.court_level.value if params.court_level else None,
            size=params.limit,
        )
        result = await api_client.search_decisions(body, client=_client(ctx))
        total = api_client.extract_total(result)

        if total == 0:
            return _result(
                "Keine aktuellen Entscheide gefunden. (Treffer-Typ: none)" + SOURCE_FOOTER,
                _build_response("", 0, []),
            )

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

        envelope = _build_response("", total, hits)
        parts = [result_header(envelope.count, total, desc, match_type=envelope.match_type)]
        for i, hit in enumerate(hits, 1):
            parts.append(format_hit(hit, i))
        return _result("\n\n".join(parts) + SOURCE_FOOTER, envelope)

    except Exception as e:  # noqa: BLE001
        raise ToolError(api_client.handle_error(e)) from None


async def get_decision_statistics(params: DecisionStatsInput, ctx: Context) -> CallToolResult:
    """Gibt Statistiken über die Anzahl indexierter Gerichtsentscheide zurück.

    Use-Case: Mengengerüst und Verteilung nach Kanton/Jahr.
    """
    try:
        body: dict = {
            "size": 0,
            "aggs": {
                "by_canton": {"terms": {"field": "hierarchy.keyword", "size": 50}},
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
                "range": {"date": {"gte": f"{params.year}-01-01", "lte": f"{params.year}-12-31"}}
            })

        body["query"] = {"bool": {"filter": filter_clauses}} if filter_clauses else {"match_all": {}}

        result = await api_client.search_decisions(body, client=_client(ctx))
        total = api_client.extract_total(result)

        lines = ["## Entscheid-Statistiken\n", f"**Gesamtzahl:** {total:,} Entscheide"]
        if params.canton:
            lines.append(f"**Filter:** Kanton {params.canton.value}")
        if params.year:
            lines.append(f"**Filter:** Jahr {params.year}")

        aggs = result.get("aggregations", {})
        canton_buckets = aggs.get("by_canton", {}).get("buckets", [])
        by_canton: list[dict] = []
        if canton_buckets:
            lines.extend(["", "### Nach Kanton/Gericht", "", "| Kanton/Gericht | Anzahl |",
                          "|----------------|--------|"])
            for bucket in canton_buckets[:20]:
                key, cnt = bucket.get("key", ""), bucket.get("doc_count", 0)
                by_canton.append({"key": key, "count": cnt})
                lines.append(f"| {key} | {cnt:,} |")

        year_buckets = aggs.get("by_year", {}).get("buckets", [])
        by_year: list[dict] = []
        if year_buckets:
            lines.extend(["", "### Nach Jahr", "", "| Jahr | Anzahl |", "|------|--------|"])
            for bucket in year_buckets[:10]:
                key_str = bucket.get("key_as_string", "")
                year_val = key_str[:4] if key_str else str(bucket.get("key", ""))
                cnt = bucket.get("doc_count", 0)
                by_year.append({"year": year_val, "count": cnt})
                lines.append(f"| {year_val} | {cnt:,} |")

        return _result("\n".join(lines) + SOURCE_FOOTER, {
            "source": DATA_SOURCE, "license": DATA_LICENSE,
            "total": total, "by_canton": by_canton, "by_year": by_year,
        })

    except Exception as e:  # noqa: BLE001
        raise ToolError(api_client.handle_error(e)) from None


# Annotations-Übersicht (ARCH-009) — alle Tools sind read-only, idempotent,
# nicht-destruktiv und erreichen ein externes System (openWorld).
_READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

_TOOLS = [
    (search_court_decisions, "search_court_decisions", "Gerichtsentscheide suchen"),
    (get_court_decision, "get_court_decision", "Gerichtsentscheid abrufen"),
    (search_bger_decisions, "search_bger_decisions", "Bundesgerichtsentscheide suchen"),
    (search_by_law_reference, "search_by_law_reference", "Entscheide zu Gesetzesartikel suchen"),
    (list_courts, "list_courts", "Verfügbare Gerichte auflisten"),
    (get_recent_decisions, "get_recent_decisions", "Neueste Gerichtsentscheide"),
    (get_decision_statistics, "get_decision_statistics", "Entscheid-Statistiken"),
]


def register_tools(mcp: FastMCP) -> None:
    """Registriert alle Tools mit expliziten Annotations (ARCH-009).

    ``structured_output=False``: die Tools liefern ein eigenes ``CallToolResult``
    mit kuratiertem Markdown (content) UND ``structuredContent`` (SDK-002),
    daher kein automatisch generiertes Output-Schema.
    """
    for fn, name, title in _TOOLS:
        mcp.tool(
            name=name,
            annotations={"title": title, **_READ_ONLY},
            structured_output=False,
        )(fn)


def register_prompts(mcp: FastMCP) -> None:
    """Registriert kuratierte Prompts (zweites Primitiv, ARCH-008)."""

    @mcp.prompt(name="rechtsrecherche", title="Schweizer Rechtsrecherche")
    def rechtsrecherche(thema: str, kanton: str = "") -> str:
        """Strukturierte Rechtsrecherche zu einem Thema (mit fedlex-mcp-Synergie)."""
        kanton_hint = f" mit Fokus auf Kanton {kanton}" if kanton else ""
        return (
            f"Führe eine strukturierte Rechtsrecherche zum Thema '{thema}'{kanton_hint} durch:\n"
            "1. Nutze search_by_law_reference für einschlägige Normen.\n"
            "2. Nutze search_court_decisions für die Rechtsprechung.\n"
            "3. Fasse die führenden Entscheide mit Signatur und Datum zusammen.\n"
            "4. Verweise auf den Volltext-Link jeder zitierten Quelle."
        )


# ---------------------------------------------------------------------------
# Lifespan (SDK-001): ein gepoolter httpx-Client für alle Tool-Calls
# ---------------------------------------------------------------------------


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Erzeugt den HTTP-Client beim Start, schliesst ihn beim Shutdown."""
    configure_logging(os.environ.get("MCP_LOG_LEVEL", "INFO"))
    client = api_client.new_client()
    log.info("server_startup")
    try:
        yield {"client": client}
    finally:
        await client.aclose()
        log.info("server_shutdown")


# ---------------------------------------------------------------------------
# Server-Factory
# ---------------------------------------------------------------------------


def _build_auth(settings: Settings):
    """Baut (AuthSettings, TokenVerifier) für den HTTP-Modus (SEC-009)."""
    from mcp.server.auth.settings import AuthSettings

    from swiss_courts_mcp.auth import JWTTokenVerifier

    base = f"http://{settings.host}:{settings.port}"
    auth_settings = AuthSettings(
        issuer_url=settings.oauth_issuer or base,
        resource_server_url=base,
        required_scopes=settings.required_scopes or None,
    )
    return auth_settings, JWTTokenVerifier(settings)


def create_mcp(settings: Settings, *, http: bool = False) -> FastMCP:
    """Baut eine FastMCP-Instanz. Auth wird nur im HTTP-Modus verdrahtet."""
    kwargs: dict = dict(
        instructions=(
            "MCP-Server für Schweizer Gerichtsentscheide via entscheidsuche.ch. "
            "Zugriff auf Urteile des Bundesgerichts (BGer), Bundesverwaltungsgerichts (BVGer), "
            "Bundesstrafgerichts (BStGer) und kantonaler Gerichte aller 26 Kantone. "
            "Ideal in Kombination mit fedlex-mcp für vollständige Rechtsrecherche. "
            "Alle Daten stammen von entscheidsuche.ch (öffentlich, kein API-Key nötig)."
        ),
        lifespan=app_lifespan,
        host=settings.host,
        port=settings.port,
    )
    if http:
        kwargs["stateless_http"] = settings.stateless_http  # SCALE-002: zustandslos skalierbar
        if settings.auth_enabled:
            auth_settings, verifier = _build_auth(settings)
            kwargs["auth"] = auth_settings
            kwargs["token_verifier"] = verifier

    mcp = FastMCP("swiss_courts_mcp", **kwargs)
    register_tools(mcp)
    register_prompts(mcp)
    return mcp


# Modul-Instanz für stdio (Default) und den Script-Entry-Point.
mcp = create_mcp(Settings.from_env(), http=False)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def _run_http(settings: Settings) -> None:
    """Startet den HTTP-Transport mit Auth (SEC-009) und CORS (SDK-004)."""
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware

    if settings.host == "0.0.0.0" and not settings.allow_public_bind:  # noqa: S104
        log.warning(
            "public_bind_without_optin",
            hint="0.0.0.0 nur in Containern/Trusted-Net; setze MCP_ALLOW_PUBLIC_BIND=1",
        )
    if not settings.auth_enabled:
        log.warning(
            "http_without_auth",
            hint="HTTP-Modus ohne Auth — nur hinter authentifizierendem Proxy betreiben",
        )

    server = create_mcp(settings, http=True)
    app = server.streamable_http_app()
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.auth_enabled,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Mcp-Session-Id", "Authorization", "Content-Type"],
            expose_headers=["Mcp-Session-Id"],
        )
    uvicorn.run(app, host=settings.host, port=settings.port)


def main():
    """Startet den MCP-Server (Default stdio, optional streamable-http)."""
    if "--http" in sys.argv:
        settings = Settings.from_env()
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                settings = settings.model_copy(update={"port": int(sys.argv[i + 1])})
        _run_http(settings)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
