"""
Strukturierte Tool-Return-Modelle (SDK-002, CH-004, ARCH-003).
==============================================================
Konsistenter Response-Envelope mit ``source`` (Abruf-Pfad: live | dump),
``dataset``/``license``/``attribution`` (variiert je nach Quelle),
``results``, ``count`` und ``match_type``. Die Tools liefern weiterhin Markdown
für die LLM-Anzeige, betten dieses strukturierte Objekt aber zur maschinellen
Weiterverarbeitung ein.

Provenance-Modell (Governance):
  * ``source`` deklariert, OB die Antwort aus der Live-Quelle (entscheidsuche.ch)
    oder aus dem Offline-Dump (SCD/Zenodo) stammt. Der Dump deckt NUR das
    Bundesgericht (2007–2024) ab — deshalb trägt jede Dump-Antwort zusätzlich
    ein ``coverage_note``. Ein Server, der im Fallback still nur BGer liefert und
    so tut als sei nichts, wäre ein Governance-Defekt (nicht ein Feature).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Live-Quelle: entscheidsuche.ch (CH-004: OGD-CH Attribution) ---
DATA_SOURCE = "entscheidsuche.ch"
DATA_SOURCE_URL = "https://entscheidsuche.ch"
DATA_LICENSE = "Public Domain (BGG Art. 27) — Schweizer Gerichtsentscheide"
DATA_ATTRIBUTION = "Quelle: entscheidsuche.ch (öffentlich, kein API-Key)"

# --- Offline-Dump: Swiss Federal Supreme Court Dataset (SCD), Zenodo (CC BY 4.0) ---
# Attribution ist Pflicht (CC BY) und wird im Tool-Output mitgeliefert, nicht nur
# im README (Anti-Pattern: "Attribution kommt ins README" — README wird nicht
# weitergereicht).
DUMP_DATASET = "Swiss Federal Supreme Court Dataset (SCD), Version 2024-3"
DUMP_DATASET_URL = "https://doi.org/10.5281/zenodo.14867950"
DUMP_LICENSE = "CC BY 4.0"
DUMP_ATTRIBUTION = (
    "Geering, F. & Merane, J. (2025). Swiss Federal Supreme Court Dataset (SCD), "
    "Version 2024-3. Zenodo. https://doi.org/10.5281/zenodo.14867950 (CC BY 4.0)"
)

# Abruf-Pfad einer Antwort. "live" = direkt von entscheidsuche.ch;
# "dump" = aus dem gecachten SCD-Offline-Dump (nur Bundesgericht, partiell).
RetrievalSource = Literal["live", "dump"]

MatchType = Literal["exact", "partial", "none"]


class Provenance(BaseModel):
    """Herkunfts-Information pro Datensatz (CH-004).

    ``source`` deklariert den Abruf-Pfad (live | dump); die übrigen Felder
    beschreiben den konkreten Datensatz und seine Lizenz/Attribution.
    """

    source: RetrievalSource = "live"
    dataset: str = DATA_SOURCE
    dataset_url: str = DATA_SOURCE_URL
    license: str = DATA_LICENSE
    attribution: str = DATA_ATTRIBUTION


# Wiederverwendbare Singletons (Default = live).
LIVE_PROVENANCE = Provenance()
DUMP_PROVENANCE = Provenance(
    source="dump",
    dataset=DUMP_DATASET,
    dataset_url=DUMP_DATASET_URL,
    license=DUMP_LICENSE,
    attribution=DUMP_ATTRIBUTION,
)


class DecisionResult(BaseModel):
    """Ein einzelner Gerichtsentscheid (strukturiert)."""

    signature: str
    date: str = ""
    court: str = ""
    canton: str = ""
    references: list[str] = Field(default_factory=list)
    title: str = ""
    abstract: str = ""
    language: str = ""
    url: str = ""
    provenance: Provenance = Field(default_factory=Provenance)


class SearchResponse(BaseModel):
    """Standardisierter Such-Envelope (SDK-002).

    ``source`` (live | dump) macht die Herkunft für jede Antwort maschinenlesbar;
    ``coverage_note`` ist gesetzt, sobald ``source == "dump"`` und benennt die
    partielle Abdeckung (nur Bundesgericht, 2007–2024, kein Volltext).
    """

    source: RetrievalSource = "live"
    dataset: str = DATA_SOURCE
    license: str = DATA_LICENSE
    attribution: str = DATA_ATTRIBUTION
    coverage_note: str | None = None
    query: str = ""
    match_type: MatchType = "none"
    count: int = 0
    total: int = 0
    results: list[DecisionResult] = Field(default_factory=list)
