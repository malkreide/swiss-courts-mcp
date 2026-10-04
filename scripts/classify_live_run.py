#!/usr/bin/env python3
"""Was hat der geplante Live-Lauf festgestellt — clear, finding oder unknown?

WARUM DAS EIN SKRIPT IST UND KEIN YAML-BLOCK
--------------------------------------------
`if: failure()` kennt zwei Antworten: rot und nicht rot. Ein Live-Lauf hat
drei, und die dritte ist die, die zaehlt:

  clear    Die Suite ist gelaufen und war gruen.
  finding  Die Suite ist gelaufen und etwas ist gefallen.
  unknown  Die Suite ist NICHT gelaufen — und niemand weiss, ob der Vertrag
           mit der Quelle noch haelt.

Ein gescheitertes `pip install`, ein Timeout, eine umbenannte Marke: alles
`unknown`, alles sieht unter `if: failure()` aus wie ein gebrochener Vertrag.
Und ein Lauf, in dem jeder Test uebersprungen wurde, sieht unter jedem
Exit-Code-Check aus wie Erfolg.

Diese Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Sie in einen
`run:`-Block zu schreiben hiesse, den einzigen Teil des Workflows, der etwas
behauptet, an die einzige Stelle zu legen, an der ihn niemand testen kann.
Deshalb steht sie hier, neben ihrem Test.

DER UEBERSPRUNGENE LAUF
-----------------------
Gemessen am 7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY`
ueberspringt die Live-Suite alle sechs Tests, und pytest endet mit 0. Ein
woechentlicher Job haette gemeldet: gruen. Geprueft haette er nichts — und ein
offenes Issue haette er zugemacht, mit einem Vergleich, den es nie gab.

`tests - skipped == 0` ist deshalb `unknown` und nicht `clear`. Ein Secret, das
niemand gesetzt hat, ist kein gruener Vertrag mit der Quelle; es ist gar keiner.

DIE QUELLE IST DAS JUNIT-XML, NICHT DER EXIT-CODE
-------------------------------------------------
Der Exit-Code von pytest sagt 0 fuer «alles gruen» und fuer «alles
uebersprungen» dasselbe. Das XML zaehlt Tests, Fehler, Fehlschlaege und
Uebersprungene getrennt, also wird es gelesen. Fehlt es, ist pytest gar nicht
bis zum Schreiben gekommen — auch das ist `unknown`, und zwar mit Grund.

HAT DIE QUELLE UEBERHAUPT GEANTWORTET?
-------------------------------------
`finding` umfasst zweierlei: einen geaenderten Vertrag mit der Quelle und eine
Quelle, die gerade aus ist. Beides gehoert gesehen, nur das Erste gehoert
gefixt — und der Zaehler `2 Fehlschlaege` sagt nicht, welches. Am 19.9.2026
(Zenodo, `httpx.ReadTimeout`) und am 2.10.2026 (entscheidsuche.ch,
`httpx.ConnectTimeout`) ging je ein Issue auf, und beide Male zeigte erst das
Nachpruefen, dass die Quelle schlicht nicht geantwortet hatte; am Folgetag war
der Lauf von selbst gruen.

Der Grund nennt deshalb, wie viele der Fehlschlaege Transportfehler sind. Am
Zustand aendert das nichts: auch ein reiner Ausfall bleibt `finding`, macht
den Job rot und oeffnet das Issue. Ein laengerer Ausfall soll nicht leiser
werden, nur seine Diagnose soll im Issue stehen statt im Log.

Aufruf:
    python scripts/classify_live_run.py live-report.xml
    python scripts/classify_live_run.py live-report.xml --pytest-exit 1

Gibt `state=...` und `reason=...` auf stdout aus und haengt beides an
`$GITHUB_OUTPUT` an, wenn die Variable gesetzt ist. Der Exit-Code ist immer 0:
Ueber rot oder gruen entscheidet der Workflow, nicht dieser Reporter.
"""

from __future__ import annotations

import argparse
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

CLEAR = "clear"
FINDING = "finding"
UNKNOWN = "unknown"

# Ausnahmen, bei denen die Quelle nicht oder nicht rechtzeitig geantwortet hat.
# Bewusst eng: `RemoteProtocolError` oder `ReadError` heissen, dass eine
# Verbindung stand und etwas zurueckkam — darueber laesst sich nicht sagen, die
# Quelle habe geschwiegen. Ein HTTP-Status ist ohnehin eine Antwort. Und nur,
# was aufgezeichnet ist: `WriteTimeout` oder `PoolTimeout` gehoerten dem Sinn
# nach dazu, sind aber nie beobachtet worden; ein Eintrag ohne Aufzeichnung
# liesse sich entfernen, ohne dass ein Test es merkt.
TRANSPORTFEHLER = frozenset({"httpx.ConnectError", "httpx.ConnectTimeout", "httpx.ReadTimeout"})

# pytest schreibt den Ausnahmetyp an den Anfang von `message`: `httpx.ReadTimeout:
# timed out` bei einem Fehlschlag, `failed on setup with "httpx.ConnectError:
# ..."` bei einem Fehler in einer Fixture. Beides aufgezeichnet, siehe
# tests/fixtures/junit/gemischt.xml.
_AUSNAHMETYP = re.compile(r'^(?:failed on \w+ with ")?([A-Za-z_][\w.]*)')


def _ausnahmetyp(element: ET.Element) -> str:
    treffer = _AUSNAHMETYP.match(element.get("message") or "")
    return treffer.group(1) if treffer else ""


def _transport_anteil(suites: list[ET.Element]) -> str:
    """Zusatz zum Grund: wie viele Fehlschlaege die Quelle gar nicht erreicht haben."""
    befunde = [el for s in suites for el in s.iter() if el.tag in ("failure", "error")]
    arten = Counter(t for t in map(_ausnahmetyp, befunde) if t in TRANSPORTFEHLER)
    n = sum(arten.values())
    if not n:
        return ""
    liste = ", ".join(f"{k} x{v}" for k, v in sorted(arten.items()))
    if n == len(befunde):
        return (
            f" — alle {n} durch Transportfehler ({liste}): Die Quelle hat nicht "
            "geantwortet. Ein geaenderter Vertrag ist damit weder belegt noch "
            "ausgeschlossen"
        )
    return (
        f" — davon {n} durch Transportfehler ({liste}); die uebrigen "
        f"{len(befunde) - n} sind inhaltlich und zuerst anzusehen"
    )


def classify(report: Path, pytest_exit: int | None = None) -> tuple[str, str]:
    """(state, reason) aus einem JUnit-XML und optional dem pytest-Exit-Code."""
    if not report.is_file():
        return (
            UNKNOWN,
            f"kein Report unter {report} — pytest ist nicht bis zum Schreiben "
            "gekommen" + (f" (Exit {pytest_exit})" if pytest_exit is not None else ""),
        )
    try:
        root = ET.parse(report).getroot()
    except (ET.ParseError, OSError) as exc:
        return UNKNOWN, f"{report} ist nicht lesbar: {exc}"

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return UNKNOWN, f"{report} enthaelt keine testsuite"

    def total(attr: str) -> int:
        return sum(int(s.get(attr) or 0) for s in suites)

    tests, failures, errors, skipped = (
        total("tests"),
        total("failures"),
        total("errors"),
        total("skipped"),
    )

    if failures or errors:
        return (
            FINDING,
            f"{failures} Fehlschlag/Fehlschlaege und {errors} Fehler von {tests} Test(s)"
            + _transport_anteil(suites),
        )
    if tests == 0:
        return (
            UNKNOWN,
            "null Tests eingesammelt — die Marke oder die Dateien haben sich "
            "bewegt, und ein Erfolg ohne Test ist kein Erfolg",
        )
    if tests - skipped == 0:
        return (
            UNKNOWN,
            f"alle {tests} Test(s) uebersprungen — meist ein fehlendes Secret oder "
            "eine nicht erfuellte Vorbedingung. Geprueft wurde nichts",
        )
    return CLEAR, f"{tests - skipped} von {tests} Test(s) ausgefuehrt, alle gruen"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="classify_live_run")
    ap.add_argument("report", type=Path, help="Pfad zum JUnit-XML von pytest")
    ap.add_argument("--pytest-exit", type=int, default=None)
    args = ap.parse_args(argv)

    state, reason = classify(args.report, args.pytest_exit)
    print(f"state={state}")
    print(f"reason={reason}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # Zeilenumbruch raus, bevor der Grund in `$GITHUB_OUTPUT` geht: Die
        # `key=value`-Form endet an der ersten neuen Zeile, und was danach
        # steht, liest der Runner als naechstes Output. Ein Grund koennte so
        # ein `state=clear` nachschieben und den roten Lauf gruen faerben.
        flat = " ".join(reason.split())
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={state}\n")
            fh.write(f"reason={flat}\n")
    # Immer 0: Ueber rot oder gruen entscheidet der Workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
