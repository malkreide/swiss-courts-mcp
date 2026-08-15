#!/usr/bin/env python3
"""Zeichnet je eine echte Antwort pro Abfrage auf.

Warum nicht von Hand geschrieben: eine handgeschriebene Erfolgs-Antwort stimmt
mit dem ueberein, was ihr Autor annahm, und kann die Quelle deshalb nicht
widerlegen. Aufgezeichnet wird darum an demselben Ort, an dem der Server die
Antwort entgegennimmt — ueber einen httpx-Response-Hook auf dem Client aus
`api_client.new_client()`. Damit tragen Aufzeichnung und Betrieb denselben
User-Agent, dasselbe Timeout und dieselbe Host-Pruefung.

Ein Endpunkt, aber viele Abfrageformen: `_searchV2.php` bekommt je nach Werkzeug
einen anderen Elasticsearch-Rumpf — Volltext, Signatur-Lookup,
Gesetzesreferenz, Taxonomie-Aggregation, Datums-Sortierung, Jahres-Statistik.
Die Portfolio-Regel «eine Antwort je externem Endpunkt» waere mit einer Datei
erfuellt und truege fast nichts. Der Rumpf gehoert deshalb in den Schluessel,
sonst waeren alle Anfragen ununterscheidbar.

## Personendaten

Gerichtsentscheide werden von den Gerichten anonymisiert publiziert;
entscheidsuche.ch spiegelt diese Publikationen. Aufgezeichnet sind hier
Trefferlisten und ein Entscheid — also genau das, was die Gerichte selbst
veroeffentlichen. Parteien erscheinen als `A._`, `B._` und so fort; die
Aufnahme vom 15.08.2026 traegt 146 solcher Marker und keinen Klarnamen.
`test_der_entscheid_ist_anonymisiert` haelt das fest.

## Aufruf

    PYTHONPATH=src python scripts/record_fixtures.py

Schreibt nach `tests/fixtures/` und erzeugt `tests/fixtures/PROVENANCE.md` neu.
Dateien, die kein Plan-Eintrag mehr erzeugt, werden geloescht — sonst waechst
der Ordner und der Nachweis bleibt zurueck. `scd_sample.csv` bleibt: das ist
der Offline-Dump-Auszug fuer den Fallback, kein aufgezeichneter Abruf.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import types
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))

from swiss_courts_mcp import api_client, server  # noqa: E402

FIXTURES = WURZEL / "tests" / "fixtures"

# Der Offline-Dump-Auszug ist keine Aufzeichnung und wird nicht aufgeraeumt.
FREMDE_DATEIEN = {"scd_sample.csv"}

VERSUCHE = 4

# Wie viele Treffer je Antwort bleiben. Die Form eines Treffers belegen drei
# genauso gut wie fuenfzig; die Zahl steht je Datei im Nachweis.
ZEILEN = 3

# Fester Zeitraum. Die Quelle liefert je nach Tag andere Entscheide — ohne
# Fenster waere jede Neuaufnahme ein anderer Datensatz und der Diff unlesbar.
ZEITRAUM = {"date_from": "2025-01-01", "date_to": "2025-06-30"}


@dataclass(frozen=True)
class Aufruf:
    """Ein Werkzeugaufruf, der Anfragen ausloesen soll."""

    name: str
    werkzeug: str
    klasse: str
    eingabe: dict[str, Any]
    # Kuerzen ist nur dort harmlos, wo der Server die Liste ganz liest. Filtert
    # oder zaehlt er *in* ihr, schneidet ein Schnitt auf die ersten Zeilen
    # womoeglich genau die Zeile weg, die er sucht.
    kuerzen: bool = True
    notiz: str = ""


PLAN: list[Aufruf] = [
    Aufruf(
        "search",
        "search_court_decisions",
        "SearchDecisionsInput",
        {"query": "Datenschutz", "limit": 5, **ZEITRAUM},
    ),
    Aufruf(
        "search_bger",
        "search_bger_decisions",
        "SearchBGerInput",
        {"query": "Persönlichkeitsschutz", "limit": 5, **ZEITRAUM},
    ),
    Aufruf(
        "search_law",
        "search_by_law_reference",
        "SearchByLawInput",
        {"law_reference": "Art. 28 ZGB", "limit": 5, **ZEITRAUM},
    ),
    Aufruf(
        "search_canton",
        "search_court_decisions",
        "SearchDecisionsInput",
        {"query": "Datenschutz", "canton": "ZH", "limit": 5, **ZEITRAUM},
        notiz="Eigene Aufzeichnung fuer den Kantonsfilter: er lief ueber ein "
        "Feld, das der Index nicht kennt, und lieferte immer null Treffer.",
    ),
    Aufruf(
        "recent",
        "get_recent_decisions",
        "RecentDecisionsInput",
        {"limit": 5},
    ),
    Aufruf(
        "courts",
        "list_courts",
        "ListCourtsInput",
        {},
        kuerzen=False,
        notiz="Ungekuerzt: das Werkzeug liest die Aggregation ueber die "
        "Gerichtshierarchie. Auf die ersten Eintraege geschnitten faende ein "
        "Kantonsfilter nichts — ein Negativbefund, den die Quelle nie gab.",
    ),
    Aufruf(
        "statistics",
        "get_decision_statistics",
        "DecisionStatsInput",
        {"year": 2025},
        kuerzen=False,
        notiz="Ungekuerzt: die Antwort ist eine Aggregation, deren Zahlen der "
        "Server summiert. Gekuerzt summierte er etwas anderes.",
    ),
]

# `get_court_decision` steht ausserhalb des Plans: seine Signatur wird zur
# Laufzeit aus der ersten Suche genommen. Eine fest verdrahtete Signatur waere
# beim naechsten Aufzeichnen womoeglich nicht mehr im Index.
DETAIL = ("get_court_decision", "GetDecisionInput")


@dataclass
class Antwort:
    """Eine gesehene Antwort samt der Anfrage, die sie ausgeloest hat."""

    url: str
    rumpf: str
    text: str
    werkzeuge: list[str] = field(default_factory=list)
    darf_kuerzen: bool = True
    dateiname: str = ""
    original_bytes: int = 0
    gekuerzt_von: int = 0
    behalten: int = 0
    sha256: str = ""
    bytes: int = 0

    @property
    def schluessel(self) -> str:
        """Woran eine Anfrage beim Abspielen wiedererkannt wird.

        Die URL allein genuegt hier nicht: alle Suchen gehen an dieselbe
        Adresse und unterscheiden sich nur im Rumpf.
        """
        if not self.rumpf:
            return self.url
        return f"{self.url}#{hashlib.sha256(self.rumpf.encode()).hexdigest()[:12]}"


def _hook_fuer(gesehen: list[Antwort]) -> Callable[[httpx.Response], Awaitable[None]]:
    """Baut den Response-Hook fuer einen Versuch.

    Eigene Funktion, damit die Liste als Argument gebunden ist und nicht als
    Schleifenvariable aus dem umgebenden Namensraum (ruff B023).
    """

    async def hook(response: httpx.Response) -> None:
        await response.aread()
        gesehen.append(
            Antwort(
                url=str(response.request.url),
                rumpf=response.request.content.decode("utf-8", "replace"),
                text=response.text,
            )
        )

    return hook


class _Kontext:
    """Der Context, den MCPServer sonst reicht — mit dem echten Client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.request_context = types.SimpleNamespace(lifespan_context={"client": client})

    async def report_progress(self, *a: object, **kw: object) -> None: ...

    async def info(self, *a: object, **kw: object) -> None: ...

    async def warning(self, *a: object, **kw: object) -> None: ...

    async def error(self, *a: object, **kw: object) -> None: ...


async def _fahre(a: Aufruf, client: httpx.AsyncClient) -> list[Antwort]:
    """Ruft ein Werkzeug und gibt die dabei gesehenen Antworten zurueck."""
    fn = getattr(server, a.werkzeug)
    modell = getattr(server, a.klasse)(**a.eingabe)
    letzter: Exception | None = None

    for versuch in range(VERSUCHE):
        if versuch:
            await asyncio.sleep(2**versuch)
        gesehen: list[Antwort] = []
        hook = _hook_fuer(gesehen)
        client.event_hooks.setdefault("response", []).append(hook)
        try:
            ergebnis = await fn(modell, _Kontext(client))
        except Exception as e:  # noqa: BLE001 — jeder Fehler ist hier ein Retry-Grund
            letzter = e
            continue
        finally:
            client.event_hooks["response"].remove(hook)

        if getattr(ergebnis, "isError", False):
            letzter = RuntimeError(f"{a.werkzeug} meldet einen Fehler")
            continue
        if not gesehen:
            letzter = RuntimeError(f"{a.werkzeug} hat keine Anfrage abgeschickt")
            continue
        for antwort in gesehen:
            antwort.werkzeuge.append(a.werkzeug)
            antwort.darf_kuerzen = a.kuerzen
        return gesehen

    raise RuntimeError(f"{a.name} nach {VERSUCHE} Versuchen nicht aufgezeichnet: {letzter}")


def _kuerze(daten: Any) -> tuple[int, int, Any]:
    """Kuerzt die Trefferliste auf `ZEILEN`; gibt (vorher, nachher, Daten).

    Nur `hits.hits` — die Liste der Treffer. `hits.total` bleibt stehen: die
    Quelle meint damit die Treffer im ganzen Index, und genau die liest der
    Server als `total` aus. Aggregationen bleiben unangetastet, sie sind keine
    Trefferliste.
    """
    treffer = daten.get("hits", {}).get("hits") if isinstance(daten, dict) else None
    if not isinstance(treffer, list):
        return 0, 0, daten
    vorher = len(treffer)
    daten["hits"]["hits"] = treffer[:ZEILEN]
    return vorher, len(daten["hits"]["hits"]), daten


async def _erste_signatur(client: httpx.AsyncClient) -> str:
    """Nimmt die Signatur des ersten Treffers einer Bundesgerichts-Suche."""
    body = api_client.build_search_body(query="Datenschutz", size=1)
    daten = await api_client.search_decisions(body, client)
    treffer = daten.get("hits", {}).get("hits") or []
    if not treffer:
        raise RuntimeError("die Suche liefert keinen Treffer fuer den Detail-Abruf")
    return str(treffer[0]["_id"])


async def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    heute = datetime.now(UTC).date().isoformat()
    nach_schluessel: dict[str, Antwort] = {}
    zaehler: dict[str, int] = {}

    client = api_client.new_client()
    try:
        signatur = await _erste_signatur(client)
        print(f"Detail-Signatur: {signatur}", file=sys.stderr)
        aufrufe = [
            *PLAN,
            Aufruf("decision", DETAIL[0], DETAIL[1], {"signature": signatur}),
        ]
        for a in aufrufe:
            print(f"… {a.werkzeug} ({a.name})", file=sys.stderr)
            for antwort in await _fahre(a, client):
                if antwort.schluessel in nach_schluessel:
                    vorhanden = nach_schluessel[antwort.schluessel]
                    if a.werkzeug not in vorhanden.werkzeuge:
                        vorhanden.werkzeuge.append(a.werkzeug)
                    continue
                zaehler[a.name] = zaehler.get(a.name, 0) + 1
                antwort.dateiname = f"{a.name}_{zaehler[a.name]}.json"
                nach_schluessel[antwort.schluessel] = antwort
    finally:
        await client.aclose()

    for antwort in nach_schluessel.values():
        antwort.original_bytes = len(antwort.text.encode("utf-8"))
        daten = json.loads(antwort.text)
        if antwort.darf_kuerzen:
            antwort.gekuerzt_von, antwort.behalten, daten = _kuerze(daten)
        # Neu eingerueckt geschrieben: eine Zeile JSON waere kleiner, aber im
        # Diff nicht lesbar, und ein Fixture will gelesen werden.
        (FIXTURES / antwort.dateiname).write_text(
            json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        roh = (FIXTURES / antwort.dateiname).read_bytes()
        antwort.sha256 = hashlib.sha256(roh).hexdigest()
        antwort.bytes = len(roh)

    antworten = sorted(nach_schluessel.values(), key=lambda x: x.dateiname)
    _schreibe_provenance(antworten, heute)

    # Aufraeumen: was kein Plan-Eintrag mehr erzeugt, hat auch keinen Nachweis.
    geschrieben = {a.dateiname for a in antworten} | {"PROVENANCE.md"} | FREMDE_DATEIEN
    for pfad in sorted(FIXTURES.iterdir()):
        if pfad.name not in geschrieben:
            print(f"– entferne veraltet: {pfad.name}", file=sys.stderr)
            pfad.unlink()

    print(f"{len(antworten)} Aufzeichnungen in {FIXTURES}", file=sys.stderr)
    return 0


def _schreibe_provenance(antworten: list[Antwort], heute: str) -> None:
    zeilen = [
        "# Herkunft der Fixtures",
        "",
        f"Aufgezeichnet am **{heute}** mit `PYTHONPATH=src python scripts/record_fixtures.py`.",
        "",
        "Eine Antwort je **Abfrage**, nicht je Endpunkt: dieser Server spricht mit einem",
        "Suchendpunkt, aber in einem halben Dutzend Abfrageformen — Volltext,",
        "Signatur-Lookup, Gesetzesreferenz, Taxonomie-Aggregation, Datums-Sortierung,",
        "Jahres-Statistik. Eine Datei wuerde die Portfolio-Regel erfuellen und fast",
        "nichts belegen.",
        "",
        "Der **Schluessel** unten ist, woran der Test eine Anfrage wiedererkennt: die",
        "URL plus eine Kurzfassung des Elasticsearch-Rumpfes. Ohne den Rumpf waeren alle",
        "Suchen ununterscheidbar — sie gehen an dieselbe Adresse.",
        "",
        "Die Antworten stammen aus dem Client von `api_client.new_client()` (gleicher",
        "User-Agent, gleiches Timeout, gleiche Host-Pruefung wie im Betrieb),",
        "abgegriffen ueber einen httpx-Response-Hook. Ausgeloest hat sie jeweils das",
        "Werkzeug selbst — so belegt die Aufzeichnung auch, dass das Werkzeug genau",
        "diese Anfrage schickt.",
        "",
        "## Personendaten",
        "",
        "Gerichtsentscheide werden von den Gerichten anonymisiert publiziert;",
        "entscheidsuche.ch spiegelt diese Publikationen. Aufgezeichnet sind",
        "Trefferlisten und ein Entscheid — also genau das, was die Gerichte selbst",
        "veroeffentlichen.",
        "",
        "## Auswahl",
        "",
        "Neu gesetzt ist die Einrueckung; gekuerzt ist allein die **Zahl** der Treffer",
        "in `hits.hits`. Kein Feld eines behaltenen Treffers ist angetastet, und",
        "`hits.total` steht wie geliefert — die Quelle meint damit die Treffer im ganzen",
        "Index, nicht die der Seite. Aggregationen bleiben ungekuerzt: der Server",
        "summiert und filtert *in* ihnen.",
        "",
        "Die Fehlerpfade — Timeout, 5xx, leere Trefferliste, der Offline-Fallback —",
        "bleiben handgeschrieben. Sie lassen sich nicht auf Zuruf aufzeichnen und sind",
        "als Erfindung in Ordnung. `scd_sample.csv` ist der Dump-Auszug fuer den",
        "Fallback und keine Aufzeichnung.",
        "",
    ]
    for a in antworten:
        zeilen += [
            f"## `{a.dateiname}`",
            "",
            f"- **Werkzeuge:** {', '.join(f'`{w}`' for w in sorted(a.werkzeuge))}",
            f"- **Schluessel:** `{a.schluessel}`",
        ]
        if a.rumpf:
            zeilen.append(f"- **Rumpf:** `{' '.join(a.rumpf.split())[:500]}`")
        if a.gekuerzt_von > a.behalten:
            zeilen.append(
                f"- **Auswahl:** die ersten {a.behalten} von {a.gekuerzt_von} Treffern, "
                f"aus {a.original_bytes} Bytes Rohantwort"
            )
        elif not a.darf_kuerzen:
            zeilen.append(
                "- **Auswahl:** ungekuerzt — der Server rechnet *in* dieser Antwort, "
                "ein Schnitt erfaende ein anderes Ergebnis"
            )
        else:
            zeilen.append("- **Auswahl:** ungekuerzt")
        zeilen += [
            f"- **Groesse:** {a.bytes} Bytes",
            f"- **SHA-256:** `{a.sha256}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(zeilen), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
