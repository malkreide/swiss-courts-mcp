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

Default-Branch ist `master`, nicht `main` — der Frische-Check oben lautet hier
`git fetch origin master && git rev-list --count HEAD..origin/master`.

ruff ist auf `0.16.1` gepinnt, an genau einer Stelle (`dev`-Extra in
`pyproject.toml`); `pip install -e ".[dev]"` liefert damit die CI-Version.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

Gates, wörtlich aus `ci.yml` (Python 3.11 / 3.12 / 3.13):

<!-- gates:start -->
```bash
PYTHONPATH=src pytest tests/ -m "not live"
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py
python scripts/check_gate_docs.py
```
<!-- gates:end -->

Live-Tests laufen geplant (`live.yml`, `cron: "0 4 * * *"`) — DRIFT-005
erfüllt, nicht bloss per `-m "not live"` ausgeschlossen. Kein Gate, von Hand:

<!-- live:start -->
```bash
PYTHONPATH=src pytest tests/ -v -m live
```
<!-- live:end -->

Beide Blöcke sind erzwungen: `check_gate_docs.py` hält sie gegen `ci.yml` und
`live.yml`. Markiert wird mit `# gate` an der Befehlszeile dort; was markiert
ist, macht die Doku rot, bis es hier steht. Das Übrige steht in README und
CONTRIBUTING.
