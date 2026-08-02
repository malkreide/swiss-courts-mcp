"""
Offline-Fallback über den SCD-Dump (Zenodo 14867950)
====================================================
Klar getrennt vom Live-Client (``api_client.py``). Dieser Layer greift NUR, wenn
entscheidsuche.ch nicht erreichbar ist (Bot-Block, 5xx, Timeout, Connect-Error)
oder der Fallback per ``SWISS_COURTS_FORCE_DUMP=1`` erzwungen wird.

Architektur-Entscheid (Phase 2, verifiziert live am 2026-07-19):
  * Quelle: **Swiss Federal Supreme Court Dataset (SCD)**, Zenodo 14867950,
    Version 2024-3, CC BY 4.0. N = 127'477 BGer-Fälle 2007–2024.
  * Genutzt wird der **CSV-Export (~120 MB, nur Metadaten/Regesten, KEIN
    Volltext)** — bewusst nicht der 375-MB-Parquet mit Volltext. Ein partieller
    Notnagel rechtfertigt weder den Footprint noch die schwere ``pyarrow``-
    Dependency. Volltext wäre zudem eine Äquivalenz-Illusion (nur BGer!).
  * Der zweite Kandidat (Zenodo 5529712, "SwissJudgmentPrediction") wurde wegen
    CC BY-NC-SA 4.0 (NonCommercial + ShareAlike) verworfen — unvereinbar mit dem
    MIT-Portfolio.

Abdeckung (KRITISCH — nicht äquivalent zur Live-Quelle):
  Nur Bundesgericht (BGer/BGE), 2007–2024, nur Metadaten. Bundesverwaltungs-,
  Bundesstrafgericht und alle 26 Kantone sind NICHT abgedeckt. Jede Dump-Antwort
  deklariert das über ``source == "dump"`` + ``coverage_note``.

Lieferung: Lazy-Download beim ersten Fallback-Bedarf in ein ``platformdirs``-
Cache-Verzeichnis, dann lokal via SQLite durchsucht (stdlib, keine Runtime-
Dependency ausser ``platformdirs``). Update-Erkennung über die Zenodo-Versions-
API (``conceptrecid`` 7793043).
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx

from swiss_courts_mcp.logging_config import get_logger
from swiss_courts_mcp.models import (
    DUMP_ATTRIBUTION,
    DUMP_DATASET,
    DUMP_LICENSE,
)

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

# Konkrete Version (Default) und das übergeordnete Konzept für Update-Erkennung.
DEFAULT_RECORD_ID = "14867950"
CONCEPT_RECID = "7793043"

ZENODO_HOST = "zenodo.org"
ZENODO_API = "https://zenodo.org/api/records"
# Eigene Egress-Allow-List (SEC-021) für den Fallback-Layer. Der Live-Client hat
# seine eigene (entscheidsuche.ch); hier ist ausschliesslich Zenodo erlaubt.
ALLOWED_HOSTS: frozenset[str] = frozenset({ZENODO_HOST})

# Grosszügiger Timeout für den (einmaligen) ~120-MB-Download.
DOWNLOAD_TIMEOUT = 600.0

# Abdeckungshinweis — landet in jeder Dump-Antwort (coverage_note).
COVERAGE_NOTE = (
    "Offline-Fallback aus dem SCD-Dump: ausschliesslich Bundesgericht (BGer/BGE), "
    "2007–2024, nur Metadaten/Regesten (kein Volltext). Bundesverwaltungsgericht, "
    "Bundesstrafgericht und alle 26 Kantone sind NICHT abgedeckt. Die Live-Quelle "
    "entscheidsuche.ch war nicht erreichbar."
)

# SCD-CSV-Spalten, die wir in SQLite übernehmen (Auswahl aus 31; kein Volltext).
_COLUMNS = [
    "docref",
    "date",
    "year",
    "language",
    "url",
    "topic",
    "issue",
    "area_general",
    "area_intermediate",
    "area_detailed",
    "division",
    "outcome",
    "leading_case",
    "source_canton",
]


class FallbackUnavailableError(RuntimeError):
    """Weder Live noch Dump verfügbar — handlungsleitende Meldung für den Client."""


# ---------------------------------------------------------------------------
# Konfiguration (ENV)
# ---------------------------------------------------------------------------


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def force_dump() -> bool:
    """Erzwingt den Dump-Pfad (für Tests/Pre-Warming)."""
    return _env_flag("SWISS_COURTS_FORCE_DUMP")


def fallback_enabled() -> bool:
    """Ob der Fallback bei Live-Ausfall überhaupt greifen darf (Default: ja)."""
    return _env_flag("SWISS_COURTS_FALLBACK_ENABLED", default=True)


def _record_id() -> str:
    return (
        os.environ.get("SWISS_COURTS_DUMP_RECORD", DEFAULT_RECORD_ID).strip() or DEFAULT_RECORD_ID
    )


def cache_dir() -> Path:
    """Cache-Verzeichnis (``platformdirs``, mit ENV-Override und Fallback)."""
    override = os.environ.get("SWISS_COURTS_CACHE_DIR")
    if override:
        return Path(override)
    try:
        from platformdirs import user_cache_dir

        return Path(user_cache_dir("swiss-courts-mcp", "swiss-public-data"))
    except Exception:  # pragma: no cover - platformdirs ist eine harte Dependency
        return Path.home() / ".cache" / "swiss-courts-mcp"


def _assert_zenodo(url: str) -> None:
    """Egress-Guard: nur HTTPS zu zenodo.org (SEC-004/021)."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise FallbackUnavailableError("Dump-Download nur über HTTPS erlaubt.")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise FallbackUnavailableError(f"Host {host!r} nicht auf der Dump-Egress-Allow-List.")


# ---------------------------------------------------------------------------
# Coverage-Helfer
# ---------------------------------------------------------------------------


def out_of_coverage_note(canton: str | None, court_level: str | None) -> str | None:
    """Gibt eine ehrliche 'nicht abgedeckt'-Erklärung zurück (oder None)."""
    if canton:
        return (
            f"Kanton {canton} ist im Offline-Fallback nicht abgedeckt — der SCD-Dump "
            "enthält ausschliesslich Bundesgerichtsentscheide (kein kantonales Recht)."
        )
    if court_level and court_level != "bundesgericht":
        return (
            f"Gerichtsebene '{court_level}' ist im Offline-Fallback nicht abgedeckt — "
            "der SCD-Dump enthält nur Bundesgericht (BGer/BGE)."
        )
    return None


@dataclass
class DumpResult:
    """Ergebnis einer Dump-Abfrage in Live-kompatibler Form.

    ``hits`` sind ``extract_hit``-kompatible Dicts. ``out_of_coverage`` markiert
    Anfragen, die der Dump prinzipiell nicht bedienen kann (Kanton/Nicht-BGer) —
    dann ist ``hits`` leer und ``note`` erklärt warum (kein leeres Resultat ohne
    Erklärung).
    """

    hits: list[dict] = field(default_factory=list)
    total: int = 0
    out_of_coverage: bool = False
    note: str = COVERAGE_NOTE


# ---------------------------------------------------------------------------
# Dump-Store (Download + SQLite)
# ---------------------------------------------------------------------------


def _norm(value: str | None) -> str:
    """Normalisiert SCD-Werte: 'NA'/leer → ''."""
    if value is None:
        return ""
    v = value.strip()
    return "" if v.upper() == "NA" else v


class DumpStore:
    """Verwaltet den lokalen SCD-Cache (Download → SQLite) und die Abfragen."""

    def __init__(self, base_dir: Path | None = None, record_id: str | None = None) -> None:
        self.record_id = record_id or _record_id()
        self.base_dir = base_dir or cache_dir()
        self.db_path = self.base_dir / f"scd-{self.record_id}.sqlite"
        self.meta_path = self.base_dir / f"scd-{self.record_id}.meta.json"

    # -- Zustand -----------------------------------------------------------

    def ready(self) -> bool:
        return self.db_path.exists() and self.db_path.stat().st_size > 0

    def _meta(self) -> dict:
        try:
            return json.loads(self.meta_path.read_text("utf-8"))
        except Exception:
            return {}

    def row_count(self) -> int:
        if not self.ready():
            return 0
        try:
            with sqlite3.connect(self.db_path) as con:
                return int(con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0])
        except Exception:
            return 0

    def status(self) -> dict:
        meta = self._meta()
        return {
            "ready": self.ready(),
            "record_id": self.record_id,
            "version": meta.get("version", ""),
            "rows": self.row_count() if self.ready() else 0,
            "cache_dir": str(self.base_dir),
            "db_path": str(self.db_path),
            "built_at": meta.get("built_at", ""),
            "dataset": DUMP_DATASET,
            "license": DUMP_LICENSE,
            "attribution": DUMP_ATTRIBUTION,
            "coverage": COVERAGE_NOTE,
            "force_dump": force_dump(),
            "fallback_enabled": fallback_enabled(),
        }

    # -- Aufbau ------------------------------------------------------------

    async def ensure_ready(self, client: httpx.AsyncClient | None = None) -> None:
        """Stellt sicher, dass die lokale DB existiert; lädt sie sonst herunter.

        Wirft ``FallbackUnavailableError`` mit handlungsleitender Meldung, wenn
        der Download/Aufbau scheitert (Graceful Degradation).
        """
        if self.ready():
            return
        self.base_dir.mkdir(parents=True, exist_ok=True)
        try:
            csv_url = await self._resolve_csv_url(client)
            version = await self._resolve_version(client)
            await self._download_and_build(csv_url, client, version)
        except FallbackUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — Graceful Degradation: nie crashen
            # Jeder Download-/Build-Fehler wird zu einer handlungsleitenden
            # FallbackUnavailableError — der Fallback-Layer darf den Tool-Call
            # niemals mit einem internen Fehler abbrechen.
            log.warning("dump_build_failed", error=str(exc))
            raise FallbackUnavailableError(
                "Der Offline-Dump (SCD/Zenodo) konnte nicht geladen werden: "
                f"{type(exc).__name__}. Bitte später erneut versuchen."
            ) from None

    async def _fetch_record(self, client: httpx.AsyncClient | None) -> dict:
        url = f"{ZENODO_API}/{self.record_id}"
        _assert_zenodo(url)
        data = await _get_json(url, client)
        if not isinstance(data, dict) or "files" not in data:
            raise FallbackUnavailableError("Unerwartete Zenodo-Antwort (keine Dateiliste).")
        return data

    async def _resolve_csv_url(self, client: httpx.AsyncClient | None) -> str:
        data = await self._fetch_record(client)
        for f in data.get("files", []):
            key = str(f.get("key", ""))
            if key.endswith(".csv"):
                link = (f.get("links", {}) or {}).get("self") or (
                    f"{ZENODO_API}/{self.record_id}/files/{key}/content"
                )
                _assert_zenodo(link)
                return link
        raise FallbackUnavailableError("SCD-Record enthält keine CSV-Datei.")

    async def _resolve_version(self, client: httpx.AsyncClient | None) -> str:
        try:
            data = await self._fetch_record(client)
            return str((data.get("metadata", {}) or {}).get("version", ""))
        except Exception:
            return ""

    async def _download_and_build(
        self, csv_url: str, client: httpx.AsyncClient | None, version: str
    ) -> None:
        tmp_db = self.db_path.with_suffix(".sqlite.tmp")
        if tmp_db.exists():
            tmp_db.unlink()
        rows = 0
        owns_client = client is None
        http = client or httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT)
        try:
            async with http.stream(
                "GET", csv_url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True
            ) as resp:
                resp.raise_for_status()
                # Zeilenweises Streaming: kein Vollpuffer der 120 MB im RAM.
                buffer = ""
                header: list[str] | None = None
                con = sqlite3.connect(tmp_db)
                self._init_schema(con)
                batch: list[tuple] = []
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        header, added = self._consume_line(con, line, header, batch)
                        rows += added
                        if len(batch) >= 2000:
                            self._flush(con, batch)
                if buffer.strip():
                    header, added = self._consume_line(con, buffer, header, batch)
                    rows += added
                self._flush(con, batch)
                con.commit()
                con.close()
        finally:
            if owns_client:
                await http.aclose()
        if rows == 0:
            tmp_db.unlink(missing_ok=True)
            raise FallbackUnavailableError("SCD-CSV war leer oder nicht parsbar.")
        tmp_db.replace(self.db_path)
        self.meta_path.write_text(
            json.dumps(
                {
                    "record_id": self.record_id,
                    "version": version,
                    "rows": rows,
                    "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                ensure_ascii=False,
            ),
            "utf-8",
        )
        log.info("dump_built", record_id=self.record_id, version=version, rows=rows)

    def build_from_csv(self, csv_path: str | Path, version: str = "local") -> int:
        """Baut die SQLite-DB aus einer bereits lokal vorliegenden SCD-CSV.

        Für Offline-Provisioning (manuell heruntergeladener Dump) und Tests —
        ohne Netzwerk. Gibt die Zeilenzahl zurück.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        self._init_schema(con)
        rows = 0
        header: list[str] | None = None
        batch: list[tuple] = []
        with open(csv_path, encoding="utf-8") as fh:
            for line in fh:
                header, added = self._consume_line(con, line, header, batch)
                rows += added
                if len(batch) >= 2000:
                    self._flush(con, batch)
        self._flush(con, batch)
        con.commit()
        con.close()
        self.meta_path.write_text(
            json.dumps(
                {
                    "record_id": self.record_id,
                    "version": version,
                    "rows": rows,
                    "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                ensure_ascii=False,
            ),
            "utf-8",
        )
        return rows

    @staticmethod
    def _init_schema(con: sqlite3.Connection) -> None:
        con.execute(
            "CREATE TABLE decisions ("
            "docref TEXT, date TEXT, year INTEGER, language TEXT, url TEXT, "
            "topic TEXT, issue TEXT, area_general TEXT, area_intermediate TEXT, "
            "area_detailed TEXT, division TEXT, outcome TEXT, leading_case TEXT, "
            "source_canton TEXT, blob TEXT)"
        )

    _reader_dialect = None

    def _consume_line(
        self,
        con: sqlite3.Connection,
        line: str,
        header: list[str] | None,
        batch: list[tuple],
    ) -> tuple[list[str] | None, int]:
        """Parst eine CSV-Zeile; erste Zeile ist der Header."""
        line = line.rstrip("\r")
        if not line:
            return header, 0
        fields = next(csv.reader(io.StringIO(line)))
        if header is None:
            return fields, 0
        record = dict(zip(header, fields, strict=False))
        docref = _norm(record.get("docref"))
        if not docref:
            return header, 0
        vals = {c: _norm(record.get(c)) for c in _COLUMNS}
        year_raw = vals.get("year", "")
        try:
            year = int(year_raw) if year_raw else None
        except ValueError:
            year = None
        blob = " ".join(
            filter(
                None,
                [
                    vals["docref"],
                    vals["topic"],
                    vals["issue"],
                    vals["area_detailed"],
                    vals["area_intermediate"],
                    vals["area_general"],
                    vals["leading_case"],
                ],
            )
        ).lower()
        batch.append(
            (
                vals["docref"],
                vals["date"],
                year,
                vals["language"],
                vals["url"],
                vals["topic"],
                vals["issue"],
                vals["area_general"],
                vals["area_intermediate"],
                vals["area_detailed"],
                vals["division"],
                vals["outcome"],
                vals["leading_case"],
                vals["source_canton"],
                blob,
            )
        )
        return header, 1

    @staticmethod
    def _flush(con: sqlite3.Connection, batch: list[tuple]) -> None:
        if not batch:
            return
        con.executemany("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        batch.clear()

    # -- Abfragen ----------------------------------------------------------

    def _query(
        self,
        terms: list[str],
        date_from: str | None,
        date_to: str | None,
        limit: int,
        order: str = "date DESC",
    ) -> tuple[int, list[dict]]:
        where = ["1=1"]
        params: list[object] = []
        for t in terms:
            where.append("blob LIKE ?")
            params.append(f"%{t.lower()}%")
        if date_from:
            where.append("date >= ?")
            params.append(date_from)
        if date_to:
            where.append("date <= ?")
            params.append(date_to)
        clause = " AND ".join(where)
        with sqlite3.connect(self.db_path) as con:
            total = int(
                con.execute(f"SELECT COUNT(*) FROM decisions WHERE {clause}", params).fetchone()[0]
            )
            cur = con.execute(
                f"SELECT docref,date,year,language,url,topic,issue,area_general,"
                f"area_intermediate,area_detailed,division,outcome,leading_case,"
                f"source_canton FROM decisions WHERE {clause} ORDER BY {order} LIMIT ?",
                [*params, limit],
            )
            hits = [_row_to_hit(row) for row in cur.fetchall()]
        return total, hits

    def search(
        self,
        query: str | None,
        date_from: str | None,
        date_to: str | None,
        limit: int,
    ) -> tuple[int, list[dict]]:
        return self._query(_terms(query), date_from, date_to, limit)

    def recent(
        self, date_from: str | None, date_to: str | None, limit: int
    ) -> tuple[int, list[dict]]:
        return self._query([], date_from, date_to, limit)

    def get_by_docref(self, candidates: list[str]) -> dict | None:
        if not candidates:
            return None
        placeholders = ",".join("?" for _ in candidates)
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute(
                f"SELECT docref,date,year,language,url,topic,issue,area_general,"
                f"area_intermediate,area_detailed,division,outcome,leading_case,"
                f"source_canton FROM decisions WHERE docref IN ({placeholders}) LIMIT 1",
                candidates,
            )
            row = cur.fetchone()
        return _row_to_hit(row) if row else None

    def statistics(self, year: int | None) -> dict:
        where = ["1=1"]
        params: list[object] = []
        if year:
            where.append("year = ?")
            params.append(year)
        clause = " AND ".join(where)
        with sqlite3.connect(self.db_path) as con:
            total = int(
                con.execute(f"SELECT COUNT(*) FROM decisions WHERE {clause}", params).fetchone()[0]
            )
            by_year = [
                {"year": str(y), "count": c}
                for (y, c) in con.execute(
                    f"SELECT year, COUNT(*) FROM decisions WHERE {clause} AND year IS NOT NULL "
                    f"GROUP BY year ORDER BY year DESC",
                    params,
                ).fetchall()
            ]
            by_area = [
                {"key": a, "count": c}
                for (a, c) in con.execute(
                    f"SELECT area_general, COUNT(*) FROM decisions WHERE {clause} "
                    f"AND area_general != '' GROUP BY area_general ORDER BY COUNT(*) DESC",
                    params,
                ).fetchall()
            ]
        return {"total": total, "by_year": by_year, "by_area": by_area}


# ---------------------------------------------------------------------------
# Zeilen-Mapping (SCD → extract_hit-kompatibles Dict)
# ---------------------------------------------------------------------------


def _row_to_hit(row: tuple) -> dict:
    (
        docref,
        date,
        year,
        language,
        url,
        topic,
        issue,
        area_general,
        area_intermediate,
        area_detailed,
        division,
        outcome,
        leading_case,
        source_canton,
    ) = row

    references: list[str] = []
    if leading_case:
        references.append(f"BGE {leading_case}")
    if docref:
        references.append(docref)

    court = "Bundesgericht"
    if division:
        court = f"Bundesgericht ({division} Abteilung)"

    abstract_parts: list[str] = []
    if area_general:
        abstract_parts.append(f"Rechtsgebiet: {area_general}")
    detail = issue or topic
    if detail:
        abstract_parts.append(detail)
    if outcome:
        abstract_parts.append(f"Ausgang: {outcome}")
    if source_canton:
        abstract_parts.append(f"Vorinstanz-Herkunft: {source_canton}")

    return {
        "signature": docref,
        "date": date or "",
        "court": court,
        "canton": "CH",
        "references": references,
        "title": topic or "",
        "abstract": " · ".join(abstract_parts),
        "language": language or "",
        "url": url or "",
    }


def _terms(query: str | None) -> list[str]:
    if not query:
        return []
    cleaned = query.replace('"', " ")
    return [t for t in cleaned.split() if len(t) >= 2]


# ---------------------------------------------------------------------------
# HTTP-Helfer
# ---------------------------------------------------------------------------


async def _get_json(url: str, client: httpx.AsyncClient | None) -> dict:
    _assert_zenodo(url)
    owns = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    try:
        # Zenodo nutzt 301-Redirects (z.B. versions/latest → konkreter Record);
        # der gepoolte Live-Client folgt standardmässig nicht.
        resp = await http.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()
    finally:
        if owns:
            await http.aclose()


# ---------------------------------------------------------------------------
# Modul-Singleton + öffentliche Dump-Abfragen (vom Server aufgerufen)
# ---------------------------------------------------------------------------

_STORE: DumpStore | None = None


def get_store() -> DumpStore:
    """Liefert den Prozess-weiten Store (lazy). Für Tests via ``set_store`` ersetzbar."""
    global _STORE
    if _STORE is None:
        _STORE = DumpStore()
    return _STORE


def set_store(store: DumpStore | None) -> None:
    """Nur für Tests: den Store austauschen (oder mit None zurücksetzen)."""
    global _STORE
    _STORE = store


async def _ready_store(client: httpx.AsyncClient | None) -> DumpStore:
    store = get_store()
    await store.ensure_ready(client)
    return store


async def search_dump(
    *,
    query: str | None,
    canton: str | None,
    court_level: str | None,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    client: httpx.AsyncClient | None = None,
) -> DumpResult:
    """Volltext-nahe Suche im Dump (topic/issue/Rechtsgebiet)."""
    oob = out_of_coverage_note(canton, court_level)
    if oob:
        return DumpResult(hits=[], total=0, out_of_coverage=True, note=oob)
    store = await _ready_store(client)
    total, hits = store.search(query, date_from, date_to, limit)
    return DumpResult(hits=hits, total=total, note=COVERAGE_NOTE)


async def search_bger_dump(
    *,
    query: str,
    chamber: str | None,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    client: httpx.AsyncClient | None = None,
) -> DumpResult:
    """BGer-Suche im Dump (der Dump ist ohnehin BGer-only)."""
    combined = f"{query} {chamber}" if chamber else query
    store = await _ready_store(client)
    total, hits = store.search(combined, date_from, date_to, limit)
    return DumpResult(hits=hits, total=total, note=COVERAGE_NOTE)


async def search_by_law_dump(
    *,
    law_reference: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    client: httpx.AsyncClient | None = None,
) -> DumpResult:
    """Gesetzesreferenz im Dump — nur soweit in topic/issue erwähnt (eingeschränkt)."""
    store = await _ready_store(client)
    total, hits = store.search(law_reference, date_from, date_to, limit)
    note = (
        COVERAGE_NOTE + " Zusatz: Gesetzesreferenzen werden offline nur erkannt, "
        "soweit sie im Betreff/Regest (topic/issue) genannt sind."
    )
    return DumpResult(hits=hits, total=total, note=note)


async def recent_dump(
    *,
    canton: str | None,
    court_level: str | None,
    limit: int,
    client: httpx.AsyncClient | None = None,
) -> DumpResult:
    """Neueste Entscheide aus dem Dump (chronologisch)."""
    oob = out_of_coverage_note(canton, court_level)
    if oob:
        return DumpResult(hits=[], total=0, out_of_coverage=True, note=oob)
    store = await _ready_store(client)
    total, hits = store.recent(None, None, limit)
    return DumpResult(hits=hits, total=total, note=COVERAGE_NOTE)


_DOCREF_RE = re.compile(r"(\d+[A-Za-z]{1,3})[_-](\d+)[/-](\d{4})")


def _docref_candidates(signature: str) -> list[str]:
    """Best-effort: aus einer entscheidsuche-Signatur einen SCD-docref ableiten."""
    cands = [signature.strip()]
    m = _DOCREF_RE.search(signature)
    if m:
        cands.append(f"{m.group(1)}_{m.group(2)}/{m.group(3)}")
    # dedupe, Reihenfolge erhalten
    seen: set[str] = set()
    out = []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


async def get_decision_dump(
    *,
    signature: str,
    client: httpx.AsyncClient | None = None,
) -> dict | None:
    """Einzel-Lookup im Dump per docref. Gibt None zurück, wenn nicht auflösbar."""
    store = await _ready_store(client)
    return store.get_by_docref(_docref_candidates(signature))


async def statistics_dump(
    *,
    canton: str | None,
    year: int | None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Statistik aus dem Dump. Bei Kantonsfilter: out_of_coverage."""
    oob = out_of_coverage_note(canton, None)
    if oob:
        return {"out_of_coverage": True, "note": oob, "total": 0, "by_year": [], "by_area": []}
    store = await _ready_store(client)
    data = store.statistics(year)
    data["out_of_coverage"] = False
    data["note"] = COVERAGE_NOTE
    return data


def status(client: httpx.AsyncClient | None = None) -> dict:
    """Cache-/Abdeckungs-Status (ohne Netzwerk, ohne Download)."""
    return get_store().status()


async def latest_version(client: httpx.AsyncClient | None = None) -> dict:
    """Fragt die Zenodo-Versions-API: liegt eine neuere SCD-Version vor?

    Ein einzelner Metadaten-Request (kein Download). Update-Erkennung über das
    ``conceptrecid`` — ``versions/latest`` liefert stets die aktuellste Edition.
    """
    url = f"{ZENODO_API}/{CONCEPT_RECID}/versions/latest"
    data = await _get_json(url, client)
    latest_id = str(data.get("id", ""))
    latest_ver = str((data.get("metadata", {}) or {}).get("version", ""))
    store = get_store()
    return {
        "latest_record": latest_id,
        "latest_version": latest_ver,
        "current_record": store.record_id,
        "update_available": bool(latest_id and latest_id != store.record_id),
    }


__all__ = [
    "COVERAGE_NOTE",
    "DumpResult",
    "DumpStore",
    "FallbackUnavailableError",
    "fallback_enabled",
    "force_dump",
    "get_decision_dump",
    "get_store",
    "latest_version",
    "recent_dump",
    "search_by_law_dump",
    "search_bger_dump",
    "search_dump",
    "set_store",
    "statistics_dump",
    "status",
]
