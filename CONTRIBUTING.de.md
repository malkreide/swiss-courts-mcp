# Mitwirken an swiss-courts-mcp

[:gb: English Version](CONTRIBUTING.md)

Vielen Dank für Ihr Interesse an einem Beitrag! Dieser Server ist Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide). Das Projekt folgt dem **No-Auth-First**-Prinzip — alle Datenquellen müssen ohne API-Key öffentlich zugänglich sein.

---

## Probleme melden

Nutzen Sie [GitHub Issues](https://github.com/malkreide/swiss-courts-mcp/issues), um Fehler zu melden oder Funktionen vorzuschlagen.

Bitte geben Sie an:
- Python-Version und Betriebssystem
- Vollständige Fehlermeldung oder Beschreibung des unerwarteten Verhaltens
- Schritte zur Reproduktion
- Bei API-Problemen: ob entscheidsuche.ch selbst erreichbar ist

---

## Pull Requests

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feat/ihr-feature`
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"`
4. Nehmen Sie Ihre Änderungen vor und ergänzen Sie Tests
5. Stellen Sie sicher, dass Tests und Linting bestehen:
   <!-- gates:start -->
   ```bash
   pytest tests/ -m "not live"
   ruff check src/ tests/ scripts/
   ruff format --check src/ tests/ scripts/
   python scripts/check_version_sync.py
   python scripts/check_gate_docs.py
   ```
   <!-- gates:end -->
   Das sind exakt die fünf Gates der CI — `scripts/` ist ein Lint-Ziel,
   und Format-Check, Versions-Sync und Gate-Doku-Check sind je ein eigenes
   Gate. Der Versions-Sync greift nur, wenn Sie die Version anfassen: Er
   hält `pyproject.toml` gegen `server.json` und die README-Badges und
   scheitert an einer in `src/` hartkodierten Version. Der Gate-Doku-Check
   hält die Liste oben gegen `ci.yml` — ein neues Gate in der CI ohne
   Eintrag in der Doku macht den Build rot.
6. Optional — die Live-Suite gegen die echte Quelle fahren:
   <!-- live:start -->
   ```bash
   PYTHONPATH=src pytest tests/ -m live
   ```
   <!-- live:end -->
   Kein Gate: Sie fragt `entscheidsuche.ch` wirklich ab, ist deshalb aus der
   PR-CI ausgeschlossen und läuft stattdessen nach Plan (`live.yml`). Von
   Hand lohnt sie, wenn Sie den Client, das Parsing oder sonst etwas
   anfassen, das von der Form der Antworten abhängt — genau das sehen die
   gemockten Unit-Tests nicht. Rot heisst hier nicht automatisch «unser
   Fehler»: erst die Quelle abfragen, dann einordnen.
7. Committen Sie nach [Conventional Commits](https://www.conventionalcommits.org/): `feat: neues Tool hinzufügen`
8. Pushen Sie und öffnen Sie einen Pull Request

---

## Code-Stil

- Python 3.11+, durchgängig async/await
- [Ruff](https://github.com/astral-sh/ruff) für Linting und Formatierung (Konfiguration in `pyproject.toml`)
- Type Hints für alle öffentlichen Funktionen erforderlich
- Pydantic-Modelle für alle Tool-Inputs mit `extra="forbid"`
- Deutschsprachige User-Strings (Fehlermeldungen, Tool-Beschreibungen); englische Code-Identifier
- Tests für neue Tools erforderlich; den bestehenden FastMCP-/Pydantic-v2-Mustern in `server.py` folgen

---

## Datenquelle

Dieser Server nutzt den öffentlichen entscheidsuche.ch-Endpoint — keine Authentifizierung erforderlich.

| Quelle | URL | Auth |
|--------|-----|------|
| entscheidsuche.ch | https://entscheidsuche.ch | Keine |

Wenn Sie neue Abfragen hinzufügen, prüfen Sie diese zuerst manuell gegen den Endpoint und behandeln Sie Randfälle (fehlende optionale Felder, Timeout bei breiten Abfragen).

---

## Projekt-Phase

Der Server ist in **Phase 1 (read-only)** — siehe [ROADMAP.md](ROADMAP.md). Schreibende Tools werden erst nach Phase-2-Freigabe akzeptiert.

---

## Die Live-Suite: wann sie läuft, und wer ein rotes Ergebnis sieht

**Kadenz:** täglich um 04:00 UTC, dazu jederzeit von Hand über *Actions → Live API Tests → Run
workflow*. Siehe [`.github/workflows/live.yml`](.github/workflows/live.yml).

**Wer es sieht:** Ein roter Lauf öffnet ein Issue mit dem Label `upstream` und dem stabilen Titel «Live-Tests gegen entscheidsuche.ch rot (<Datum>)». Ein zweiter roter Lauf erkennt das offene Issue am Titelanfang und hängt sich an denselben Thread, statt ein zweites aufzumachen. Wird die Suite wieder grün, schliesst sich das Issue selbst.

**Drei Antworten, nicht zwei.** `scripts/classify_live_run.py` liest das JUnit-XML statt des
Exit-Codes und unterscheidet: `clear` (gelaufen, grün), `finding` (gelaufen,
etwas gefallen) und `unknown` (nicht gelaufen — Installation gescheitert, null
Tests eingesammelt, alle übersprungen). Ein `unknown` schliesst nie ein Issue:
Zuzumachen hiesse zu behaupten, der Vergleich sei gelaufen.

**Ein roter Live-Lauf heisst nicht zwingend «unser Fehler».** Er heisst: Der
Vertrag mit der Quelle hat sich geändert, oder die Quelle ist gerade aus. Beides
gehört gesehen, nur das Erste gehört gefixt. Bitte den Lauf lesen, bevor der Job
deaktiviert wird — so stirbt dieser Check, und er ist der einzige im Repo, der
einer falschen Grundannahme über entscheidsuche.ch widersprechen kann. Jeder andere Test
prüft gegen eine Fixture, und die Fixture ist aus derselben Annahme geschrieben
wie der Code.

## Lizenz

Mit Ihrem Beitrag erklären Sie sich damit einverstanden, dass Ihre Beiträge unter der [MIT-Lizenz](LICENSE) lizenziert werden.
