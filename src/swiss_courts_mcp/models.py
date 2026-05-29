"""
Strukturierte Tool-Return-Modelle (SDK-002, CH-004, ARCH-003).
==============================================================
Konsistenter Response-Envelope mit ``source``, ``provenance``, ``results``,
``count`` und ``match_type``. Die Tools liefern weiterhin Markdown für die
LLM-Anzeige, betten dieses strukturierte Objekt aber zur maschinellen
Weiterverarbeitung ein.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Quelle + Lizenz maschinenlesbar (CH-004: OGD-CH Attribution).
DATA_SOURCE = "entscheidsuche.ch"
DATA_SOURCE_URL = "https://entscheidsuche.ch"
DATA_LICENSE = "Public Domain (BGG Art. 27) — Schweizer Gerichtsentscheide"

MatchType = Literal["exact", "partial", "none"]


class Provenance(BaseModel):
    """Herkunfts-Information pro Datensatz (CH-004)."""

    source: str = DATA_SOURCE
    source_url: str = DATA_SOURCE_URL
    license: str = DATA_LICENSE


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
    """Standardisierter Such-Envelope (SDK-002)."""

    source: str = DATA_SOURCE
    license: str = DATA_LICENSE
    query: str = ""
    match_type: MatchType = "none"
    count: int = 0
    total: int = 0
    results: list[DecisionResult] = Field(default_factory=list)
