# CLAUDE.md

## Vor der Arbeit

Klon-Aktualität prüfen: `git fetch origin main && git rev-list --count HEAD..origin/main`
Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

## Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

## Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

---

## Dieses Repo

Default-Branch ist `master`, nicht `main` — der Befehl oben lautet hier
`git fetch origin master && git rev-list --count HEAD..origin/master`.

**ruff:** `ruff==0.16.1`, hart gepinnt, und zwar an genau einer Stelle — der
`dev`-Extra in `pyproject.toml`. Eine `.pre-commit-config.yaml` gibt es nicht,
und die CI installiert ruff über dieselbe Extra. `pip install -e ".[dev]"`
liefert also die CI-Version; kein Nachziehen nötig. Beim Anheben (Dependabot)
ändert sich nur diese eine Zeile.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

<!-- gates:start -->
```bash
PYTHONPATH=src pytest tests/ -m "not live"
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py
python scripts/check_gate_docs.py
```
<!-- gates:end -->

`scripts/` gehört zum Lint-Ziel, und `ruff format --check` ist ein eigenes
Gate. Diese Liste wird erzwungen: `check_gate_docs.py` hält sie gegen die
`run:`-Zeilen in `ci.yml`, hier wie in README und CONTRIBUTING. Ein neues Gate
in der CI macht die Doku rot, bis es drinsteht — die Marker drumherum sind
dafür da, nicht dekorativ.

**Live-Tests:** `.github/workflows/live.yml` läuft geplant, `cron: "0 4 * * *"`,
plus `workflow_dispatch`. DRIFT-005 ist damit erfüllt — Live-Tests sind hier
nicht bloss per `-m "not live"` ausgeschlossen. `schedule` greift nur auf dem
Default-Branch: Änderungen an dem Workflow wirken erst nach dem Merge, vorher
von Hand auslösen.
