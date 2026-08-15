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

**ruff:** CI pinnt `ruff==0.16.1` (`.github/workflows/ci.yml`). Eine
`.pre-commit-config.yaml` gibt es nicht; die zweite Quelle ist die
`dev`-Extra in `pyproject.toml`, und die sagt `ruff>=0.15.15` — eine
Untergrenze, kein Pin. `pip install -e ".[dev]"` installiert also *nicht*
die CI-Version. Nach dem Dev-Install explizit `pip install ruff==0.16.1`.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```bash
PYTHONPATH=src pytest tests/ -m "not live"
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py
```

`scripts/` gehört zum Lint-Ziel. README und CONTRIBUTING nennen nur
`src/ tests/` — wer das kopiert, sieht Lint-Fehler erst in der CI.

**Live-Tests:** `.github/workflows/live.yml` läuft geplant, `cron: "0 4 * * *"`,
plus `workflow_dispatch`. DRIFT-005 ist damit erfüllt — Live-Tests sind hier
nicht bloss per `-m "not live"` ausgeschlossen. `schedule` greift nur auf dem
Default-Branch: Änderungen an dem Workflow wirken erst nach dem Merge, vorher
von Hand auslösen.
