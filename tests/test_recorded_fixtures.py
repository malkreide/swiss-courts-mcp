"""Jedes Werkzeug, gefahren aus einer aufgezeichneten Antwort.

Die handgeschriebenen Stubs im Rest der Suite pruefen die *Fehler*-Pfade — ein
Timeout, ein 5xx, eine leere Trefferliste, den Offline-Fallback —, die sich
nicht auf Zuruf aufzeichnen lassen und als Erfindung in Ordnung sind. Was sie
nicht koennen: die Form einer Erfolgs-Antwort belegen. Sie stimmen mit dem
ueberein, was ihr Autor annahm.

Ein Suchendpunkt, aber ein halbes Dutzend Abfrageformen: Volltext,
Signatur-Lookup, Gesetzesreferenz, Taxonomie-Aggregation, Datums-Sortierung,
Jahres-Statistik. Aufgezeichnet ist deshalb eine Antwort je **Abfrage**, und
der Elasticsearch-Rumpf gehoert in den Schluessel — ohne ihn waeren alle
Anfragen ununterscheidbar, sie gehen an dieselbe Adresse.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei stehen in
`tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`PYTHONPATH=src python scripts/record_fixtures.py`.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from typing import Any

import httpx
import pytest
import respx
from mcp.server.mcpserver.exceptions import ToolError

from swiss_courts_mcp import api_client, server
from tests.fixture_data import (
    fixture_json,
    fixture_text,
    provenance,
    recorded_names,
    recorder,
    schluesselverzeichnis,
)

ZEITRAUM = {"date_from": "2025-01-01", "date_to": "2025-06-30"}

# Werkzeug → (Eingabeklasse, Eingabe). Bewusst noch einmal hingeschrieben und
# nicht aus dem Recorder-Plan abgeleitet: die Tests sollen eine eigene Aussage
# machen. Dass beide dieselben Aufrufe fahren, prueft
# `test_der_recorder_faehrt_dieselben_aufrufe`.
WERKZEUGE: dict[str, tuple[str, str, dict[str, Any]]] = {
    "search": (
        "search_court_decisions",
        "SearchDecisionsInput",
        {"query": "Datenschutz", "limit": 5, **ZEITRAUM},
    ),
    "search_bger": (
        "search_bger_decisions",
        "SearchBGerInput",
        {"query": "Persönlichkeitsschutz", "limit": 5, **ZEITRAUM},
    ),
    "search_law": (
        "search_by_law_reference",
        "SearchByLawInput",
        {"law_reference": "Art. 28 ZGB", "limit": 5, **ZEITRAUM},
    ),
    "search_canton": (
        "search_court_decisions",
        "SearchDecisionsInput",
        {"query": "Datenschutz", "canton": "ZH", "limit": 5, **ZEITRAUM},
    ),
    "recent": ("get_recent_decisions", "RecentDecisionsInput", {"limit": 5}),
    "courts": ("list_courts", "ListCourtsInput", {}),
    "statistics": ("get_decision_statistics", "DecisionStatsInput", {"year": 2025}),
}


def _signatur() -> str:
    """Die aufgezeichnete Signatur des Detail-Abrufs, aus dem Entscheid selbst."""
    return str(fixture_json("decision_1.json")["hits"]["hits"][0]["_id"])


@pytest.fixture
def quelle():
    """Beantwortet jede Anfrage aus ihrer eigenen Aufzeichnung und protokolliert mit.

    Nach der *Anfrage* zugeordnet, nicht nach der Reihenfolge — und der Rumpf
    gehoert dazu: alle Suchen gehen an dieselbe URL. Eine Anfrage ohne
    Aufzeichnung faellt hier laut auf, statt still eine fremde Datei zu
    bekommen.
    """
    protokoll: list[httpx.Request] = []
    verzeichnis = schluesselverzeichnis()

    def antwort(request: httpx.Request) -> httpx.Response:
        protokoll.append(request)
        rumpf = request.content.decode("utf-8", "replace") if request.content else ""
        schluessel = str(request.url)
        if rumpf:
            schluessel += f"#{hashlib.sha256(rumpf.encode()).hexdigest()[:12]}"
        name = verzeichnis.get(schluessel)
        if name is None:
            raise AssertionError(
                f"keine Aufzeichnung fuer diese Anfrage:\n  {schluessel}\n  Rumpf: {rumpf[:300]}\n"
                "Neu aufzeichnen mit `PYTHONPATH=src python scripts/record_fixtures.py`."
            )
        return httpx.Response(200, text=fixture_text(name))

    with respx.mock:
        respx.route().mock(side_effect=antwort)
        yield protokoll


async def _fahre(name: str, ctx):
    """Ruft ein Werkzeug mit der Eingabe aus der Tabelle."""
    if name == "decision":
        werkzeug, klasse, eingabe = (
            "get_court_decision",
            "GetDecisionInput",
            {"signature": _signatur()},
        )
    else:
        werkzeug, klasse, eingabe = WERKZEUGE[name]
    return await getattr(server, werkzeug)(getattr(server, klasse)(**eingabe), ctx)


def _strukturiert(ergebnis) -> dict:
    """Der `structuredContent`-Teil der Antwort."""
    return ergebnis.structured_content or {}


def _markdown(ergebnis) -> str:
    return "\n".join(getattr(b, "text", "") for b in (ergebnis.content or []))


# --------------------------------------------------------------------------
# Herkunft
# --------------------------------------------------------------------------
def test_provenance_nennt_ein_brauchbares_aufnahmedatum():
    """Eine Aufzeichnung ohne Datum ist eine undatierte Behauptung ueber die Quelle."""
    treffer = re.search(r"Aufgezeichnet am \*\*(\d{4}-\d{2}-\d{2})\*\*", provenance())
    assert treffer, "PROVENANCE.md nennt kein Aufnahmedatum im erwarteten Format"
    wann = dt.date.fromisoformat(treffer.group(1))
    assert wann <= dt.datetime.now(dt.UTC).date(), "Aufnahmedatum liegt in der Zukunft"


def test_jede_fixture_steht_in_der_provenance():
    """Sonst waechst der Ordner und der Nachweis bleibt zurueck."""
    text = provenance()
    fehlend = [n for n in recorded_names() if f"## `{n}`" not in text]
    assert not fehlend, f"ohne Eintrag in PROVENANCE.md: {fehlend}"


def test_jeder_schluessel_zeigt_auf_eine_vorhandene_datei():
    """Der Nachweis traegt hier den Abspielbetrieb — er darf nicht ins Leere zeigen."""
    fehlend = sorted(set(schluesselverzeichnis().values()) - set(recorded_names()))
    assert not fehlend, f"im Nachweis genannt, aber nicht vorhanden: {fehlend}"


def test_keine_aufzeichnung_liegt_unbenutzt_herum():
    """Die Gegenrichtung — eine Datei, die kein Schluessel erreicht, belegt nichts."""
    ueberzaehlig = sorted(set(recorded_names()) - set(schluesselverzeichnis().values()))
    assert not ueberzaehlig, f"von keinem Schluessel erreicht: {ueberzaehlig}"


def test_der_recorder_faehrt_dieselben_aufrufe():
    """Recorder und Tests duerfen nicht auseinanderlaufen.

    Laedt `scripts/record_fixtures.py` als Modul — `main()` wird nicht gerufen,
    es geht keine Anfrage raus. Der Detail-Abruf steht in beiden ausserhalb der
    Tabelle, weil seine Signatur zur Laufzeit gesucht wird.
    """
    im_plan = {a.name for a in recorder().PLAN}
    assert im_plan == set(WERKZEUGE), "Recorder und Testtabelle nennen verschiedene Aufrufe"


@pytest.mark.parametrize("name", sorted(recorded_names()))
def test_keine_aufzeichnung_ist_leer(name):
    """Eine leere Antwort sieht aus wie eine gueltige und prueft nichts.

    Drei Formen kommen von diesem Endpunkt: eine Trefferliste, eine
    Aggregation (Statistik) und die Gerichtstaxonomie, die gar keine
    ES-Antwort ist, sondern ein nach Kanton geschachteltes Verzeichnis.
    """
    daten = fixture_json(name)
    if "hits" in daten:
        assert (daten["hits"].get("hits") or []) or (daten.get("aggregations") or {}), (
            f"{name} traegt weder Treffer noch Aggregation — neu aufzeichnen"
        )
        return
    assert daten, f"{name} ist leer"
    assert len(daten) > 5, f"{name} traegt nur {len(daten)} Eintraege — gekuerzt?"


# --------------------------------------------------------------------------
# Personendaten
# --------------------------------------------------------------------------
def test_der_entscheid_ist_anonymisiert():
    """Gerichte publizieren anonymisiert; die Aufzeichnung belegt, dass sie es taten.

    Parteien erscheinen als `A._`, `B._` und so fort. Eine Aufzeichnung ist
    eine Datei im Repository, kein fluechtiger Abruf — hier steht deshalb, was
    beim Aufnehmen tatsaechlich drin war, statt darauf zu vertrauen.
    """
    text = fixture_text("decision_1.json")
    marker = re.findall(r"\b[A-Z]\._", text)
    assert len(marker) > 20, (
        f"nur {len(marker)} Anonymisierungsmarker — die Aufzeichnung vor dem "
        "Einchecken von Hand ansehen"
    )


# --------------------------------------------------------------------------
# Die Werkzeuge, jedes an seiner eigenen Antwort
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted([*WERKZEUGE, "decision"]))
async def test_jedes_werkzeug_liest_seine_aufgezeichnete_antwort(ctx, quelle, name):
    """Der eigentliche Punkt: jede Abfrage bekommt *ihre* Antwort.

    Alle mit derselben zu bedienen hiesse, die Aufzeichnung gegen eine Abfrage
    zu halten, die sie nicht beantwortet. Der Dispatcher faellt laut, wenn eine
    Anfrage keine Aufzeichnung hat.
    """
    ergebnis = await _fahre(name, ctx)
    assert not ergebnis.is_error, _markdown(ergebnis)[:400]
    assert _markdown(ergebnis).strip(), f"{name} liefert kein Markdown"
    assert quelle, f"{name} hat gar keine Anfrage abgeschickt"


async def test_die_suche_meldet_die_treffer_des_index_nicht_die_der_seite(ctx, quelle):
    """Der Grund, warum `hits.total` beim Kuerzen stehen bleibt.

    Wer `total` auf die Zeilen der Seite kuerzt, macht aus «1234 Entscheide,
    davon 3 gezeigt» ein «3 Entscheide» — und die Antwort behauptet dann etwas
    ueber die Rechtsprechung.
    """
    daten = fixture_json("search_1.json")
    gesamt = daten["hits"]["total"]["value"]
    gezeigt = len(daten["hits"]["hits"])
    assert gesamt > gezeigt, "total wurde mitgekuerzt — dann behauptet die Antwort weniger"

    ergebnis = await _fahre("search", ctx)
    assert str(gesamt) in _markdown(ergebnis), f"die Gesamtzahl {gesamt} steht nicht in der Antwort"


async def test_der_titel_kommt_als_sprach_dict(ctx, quelle):
    """`_source.title` ist ein Sprach-Dict, keine Zeichenkette.

    Ein Stub mit `"title": "…"` sieht einfacher aus und ist falsch; wer darauf
    `.get("de")` ruft, bekaeme im Betrieb einen Fehler statt eines Titels.
    """
    quelle_hit = fixture_json("search_1.json")["hits"]["hits"][0]["_source"]
    assert isinstance(quelle_hit["title"], dict), "der Titel ist kein Sprach-Dict mehr"
    ergebnis = await _fahre("search", ctx)
    text = _markdown(ergebnis)
    assert "{" not in text.split("\n")[0], f"ein rohes Dict im Titel: {text[:200]}"


async def test_die_gerichtsliste_liest_das_ganze_verzeichnis(ctx, quelle):
    """Die Taxonomie ist ein Verzeichnis, keine Trefferliste.

    Deshalb bleibt sie ungekuerzt: der Server filtert und zaehlt *in* ihr, und
    auf die ersten Eintraege geschnitten faende ein Kantonsfilter nichts.
    """
    daten = fixture_json("courts_1.json")
    # Die Taxonomie ist keine ES-Antwort: ein nach Kanton geschachteltes
    # Verzeichnis, in dem der Server nach Kanton filtert und Kammern zaehlt.
    assert "hits" not in daten, "die Taxonomie ist plötzlich eine Trefferliste"
    assert {"CH", "ZH", "BE"} <= set(daten), f"Kantone fehlen: {sorted(daten)[:10]}"
    ergebnis = await _fahre("courts", ctx)
    assert not ergebnis.is_error, _markdown(ergebnis)[:300]
    assert _strukturiert(ergebnis), "die Gerichtsliste kommt ohne strukturierte Daten"


async def test_der_entscheid_wird_ueber_seine_signatur_gefunden(ctx, quelle):
    """Der Detail-Abruf schickt eine andere Abfrageform als die Suche.

    Ein Test, der beide mit derselben Datei bedient, merkte eine Vertauschung
    nicht — die Antworten sind gleich gebaut.
    """
    ergebnis = await _fahre("decision", ctx)
    assert not ergebnis.is_error, _markdown(ergebnis)[:300]
    assert _signatur() in _markdown(ergebnis) or _signatur() in json.dumps(
        _strukturiert(ergebnis), ensure_ascii=False
    ), "die Antwort nennt die angefragte Signatur nicht"


# --------------------------------------------------------------------------
# Die Funde: zwei Filter, die auf Felder zeigten, die es so nicht gibt
# --------------------------------------------------------------------------
async def test_die_gerichtsebene_filtert_ueber_hierarchy_nicht_ueber_id(ctx, quelle):
    """Elasticsearch lehnt Prefix-Abfragen auf `_id` ab.

    «Can only use prefix queries on keyword, text and wildcard fields — not on
    [_id] which is of type [_id]». Die Antwort kam trotzdem mit HTTP 200,
    `hits.total = 0` und `_shards.failed = 47` von 53. `search_bger_decisions`
    hat damit nie einen Entscheid gefunden — als sauberer Negativbefund
    verkleidet.

    Diese Zusicherung liest die tatsaechlich gestellte Abfrage. Im Ergebnis
    waere der Unterschied unsichtbar gewesen.
    """
    await _fahre("search_bger", ctx)
    rumpf = json.loads(quelle[-1].content)
    text = json.dumps(rumpf, ensure_ascii=False)
    assert '"_id"' not in text, f"die Abfrage filtert wieder ueber `_id`: {text[:300]}"
    assert '"hierarchy"' in text, text[:300]


async def test_der_kantonsfilter_nennt_ein_feld_das_es_gibt(ctx, quelle):
    """`hierarchy.keyword` gibt es im Index nicht.

    Ein `term` auf ein unbekanntes Feld beantwortet Elasticsearch mit HTTP 200
    und null Treffern — kein Fehler, keine Warnung, kein Shard-Fehler. Der
    Kantonsfilter lieferte deshalb *immer* nichts. Gemessen am 15.08.2026 fuer
    «Datenschutz» + ZH: `hierarchy.keyword` → 0, `hierarchy` → 460.
    """
    await _fahre("search_canton", ctx)
    text = json.dumps(json.loads(quelle[-1].content), ensure_ascii=False)
    assert "hierarchy.keyword" not in text, f"das Feld gibt es nicht: {text[:300]}"
    assert '"hierarchy"' in text, text[:300]


@pytest.mark.parametrize("name", ["search_bger", "search_canton"])
async def test_die_gefilterte_suche_findet_etwas(ctx, quelle, name):
    """Und das ist die Zusicherung, die beide Funde festhaelt.

    Vorher lieferten beide Wege `match_type: none` mit hilfreichen Suchtipps —
    die glaubwuerdigste Form eines Ausfalls.
    """
    ergebnis = await _fahre(name, ctx)
    daten = _strukturiert(ergebnis)
    assert daten["match_type"] != "none", _markdown(ergebnis)[:300]
    assert daten["count"] > 0
    assert daten["total"] > 0


@respx.mock
async def test_gescheiterte_shards_sind_kein_leeres_ergebnis(ctx):
    """Der Waechter gegen die naechste stille Variante davon.

    Elasticsearch beantwortet eine Abfrage, die auf einzelnen Shards scheitert,
    mit HTTP 200 und der Trefferzahl der *uebrigen* Shards. Genau so blieb der
    `_id`-Fehler unbemerkt. Ein Modell kann «dazu gibt es keine Rechtsprechung»
    nicht von «die Abfrage wurde nicht ausgefuehrt» unterscheiden — der Server
    muss es koennen.
    """
    kaputt = json.dumps(
        {
            "_shards": {
                "total": 53,
                "successful": 6,
                "failed": 47,
                "failures": [
                    {"reason": {"type": "query_shard_exception", "reason": "Can only use..."}}
                ],
            },
            "hits": {"total": {"value": 0}, "hits": []},
        }
    )
    respx.post(api_client.SEARCH_URL).mock(return_value=httpx.Response(200, text=kaputt))
    with pytest.raises(ToolError) as fehler:
        await _fahre("search", ctx)
    text = str(fehler.value)
    assert "47" in text and "teilweise" in text, text
    assert "Keine Entscheide gefunden" not in text, (
        "ein Totalausfall wird als sauberer Negativbefund gemeldet"
    )
    assert "Interner Fehler" not in text, "die Ursache wird maskiert — dann liest sie niemand"


def test_die_abfragen_unterscheiden_sich_im_rumpf():
    """Der Grund, warum der Rumpf in den Schluessel gehoert.

    Waeren die Rumpfe gleich, genuegte eine Datei. Sie sind es nicht — und ein
    Dispatcher, der nur die URL liest, gaebe allen dieselbe Antwort.
    """
    rumpfe = re.findall(r"- \*\*Rumpf:\*\* `(.+)`$", provenance(), re.MULTILINE)
    assert len(rumpfe) >= 5, f"nur {len(rumpfe)} Rumpfe im Nachweis"
    assert len(set(rumpfe)) == len(rumpfe), "zwei Aufzeichnungen tragen denselben Rumpf"


# --------------------------------------------------------------------------
# Die Gegenrichtung
# --------------------------------------------------------------------------
@respx.mock
async def test_eine_leere_trefferliste_bleibt_eine_leere_trefferliste(ctx):
    """`hits: []` ist eine Aussage der Quelle: dazu gibt es nichts.

    Das darf nicht als Fehler herauskommen — sonst kann das Modell einen echten
    Negativtreffer nicht von einem Ausfall unterscheiden.
    """
    leer = json.dumps({"hits": {"total": {"value": 0}, "hits": []}})
    respx.post(api_client.SEARCH_URL).mock(return_value=httpx.Response(200, text=leer))
    ergebnis = await _fahre("search", ctx)
    assert not ergebnis.is_error, "eine leere Suche ist kein Fehler"
    assert "Keine Entscheide" in _markdown(ergebnis)
    assert _strukturiert(ergebnis)["match_type"] == "none"
