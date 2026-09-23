# CLAUDE.md

## Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

**Nach einem Merge den Branch-Ref wegräumen — sonst meldet git fremde Commits
als eigene, ungesicherte Arbeit.** GitHub löscht den Feature-Branch beim Merge;
der lokale Tracking-Ref `origin/claude/<name>` überlebt das und zeigt weiter auf
den Stand *vor* dem Merge. Setzt man den gleichnamigen lokalen Branch danach auf
den frischen Default-Branch, liest git die Differenz als «N unpushed commits».

Am 19.9.2026 dreimal aufgetreten, und der mittlere Fall zeigt, warum es
gefährlich ist: gemeldet waren drei Commits, und **zwei davon gehörten nicht
mir** — `21ca5c4` (Merge eines Dependabot-PR) und `b456439`
(`build(deps): bump actions/github-script from 7 to 9`). Alle drei standen
längst auf `origin/master`:

```bash
git ls-remote --heads origin claude/<name> | wc -l   # 0 — remote gelöscht
git branch -r --contains HEAD                        # origin/master
```

Wer die Meldung durch einen Push beruhigt, legt einen erledigten Branch neu an
und veröffentlicht fremde, längst gemergte Commits unter dem eigenen Namen. Der
richtige Griff ist lokal:

```bash
git fetch --prune origin        # OHNE Refspec
```

**Das `--prune` verliert seine Wirkung, sobald ein Refspec dahintersteht.**
`git fetch --prune origin master` räumt nur innerhalb von `master` auf; der
tote Branch-Ref bleibt stehen. Genau so entstand der dritte Fehlalarm desselben
Tages — der Befehl war getippt, sah nach Erledigung aus und hatte die eine
Referenz nicht angefasst, um die es ging. Der Frische-Check ganz
oben benutzt aus demselben Grund einen Refspec und ersetzt dieses `--prune`
deshalb **nicht**.

Der Fehlalarm ist dabei nicht bloss lästig. Im selben mittleren Fall verdeckte
er eine echte Veralterung: das Aufräumen brachte ein `[behind 2]` zum Vorschein
— `master` war inzwischen um zwei Dependabot-Merges weitergelaufen, während der
Blick auf einem Ref lag, der rückwärts zeigte. Also genau der Zustand, vor dem
der Absatz darüber warnt, getarnt als sein Gegenteil: die Meldung sprach von
Arbeit, die zu sichern sei, und der Klon hinkte in Wahrheit hinterher.

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

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**Dieselbe Falle bei einer Konfigurationsoption: die Vorgabe lesen, bevor man
einen Schlüssel für wirkungslos hält.** Am 29.8.2026 fielen die
`labels:`-Zeilen aus den `dependabot.yml` des Portfolios, begründet mit
«Dependabot legt Labels nicht an». Eine Messung danach zeigte, dass
`dependencies` in 36 von 42 Repos sehr wohl existiert, 35 davon mit GitHubs
Standardbeschreibung. Das las sich zuerst wie ein Beleg, dass die Aktion
falsch war.

Die Optionsreferenz kehrt es um:

```
Dependabot creates these default labels automatically, as necessary in
your repository.

If you define more than one package manager, an additional label for the
ecosystem or language is added to each pull request.

The labels specified are used instead of the default labels.
```

Ohne `labels:` vergibt Dependabot also `dependencies` — und, sobald mehr als
ein Paketmanager deklariert ist, zusätzlich ein Ökosystem-Label — und legt sie
selbst an; eine eigene Liste **ersetzt** diesen Satz, und «if any of these
labels is not defined in the repository, it is ignored». Die Zeile war nicht
wirkungslos — sie tauschte einen sich selbst pflegenden Vorgabesatz gegen eine
starre Liste.

**Die Bedingung nicht weglassen.** Bei nur einem Paketmanager steht das
Ökosystem-Label gar nicht zu; wer es dort trotzdem erwartet, schreibt genau
den Fehlbefund auf, gegen den dieser Abschnitt geschrieben ist — der Abschnitt
liefe an sich selbst vorbei. Im Portfolio deklariert jede `dependabot.yml`
zwei (`pip` und `github-actions`), die Bedingung ist hier also überall
erfüllt; anderswo nicht unbedingt. Aufgefallen ist die fehlende Bedingung
nicht beim Schreiben, sondern durch einen Codex-Review auf
`swiss-environment-mcp` PR #113 — vierzehn Sekunden vor dem Merge desselben
PR.

Was das kostet, ist an `openlex-mcp` gemessen: zwei Ökosysteme deklariert,
also stünden `dependencies` **und** ein Ökosystem-Label zu; vorhanden ist nur
das erste, `github-actions` und `github_actions` fehlen beide (Kontrolle `bug`
vorhanden). `register-mcp` ist die Gegenprobe: dort existieren alle vier
deklarierten Namen mit handgeschriebener Beschreibung, die Liste ist gewollt
und vollständig.

**Dreimal falsch eingeordnet, in drei Richtungen.** Erst die Zeile für bloss
wirkungslos gehalten. Dann die gefundenen Labels für einen Widerspruch. Dann,
auf denselben Fund gestützt, einen richtigen PR geschlossen mit dem Argument,
das Label existiere ja — obwohl es existiert, *weil* die Vorgabe es anlegt.
Der dritte Fehler ist der teuerste, weil er wie eine Messung aussah.

Was die Messung **nicht** hergibt: wer die 36 Labels angelegt hat. Die
Referenz sagt, Dependabot tue es; die Objekt-IDs liegen aber so dicht
beieinander, dass sie eher aus einem Stapellauf stammen. Beides passt zum
Befund, keines ist belegt — die Herkunft blieb ungemessen.

Beim Aufräumen gilt deshalb dieselbe Frage wie bei `lotId`: Was ist die
*Vorgabe*, wenn man das Ding weglässt — nicht bloss, ob der aktuelle Wert
etwas bewirkt.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

**Den CI-Stand über `get_check_runs` lesen, nicht über `get_status`.** Die
Status-Abfrage bedient die alte Commit-Status-API, und dieses Repo benutzt
ausschliesslich Check-Runs. Sie antwortet deshalb *immer* mit
`state: "pending"` bei `total_count: 0` — am 19.9.2026 gemessen auf drei PRs,
darunter #80 und #82, die beide mit vier grünen Check-Runs gemergt waren:

```
{"state": "pending", "sha": "…", "total_count": 0, "statuses": []}
```

Die leere Menge trägt hier also das Wort «pending», und wer nur das Feld liest,
hält eine grüne CI für laufend und wartet auf etwas, das schon da ist. Dieselbe
Klasse wie der 403 weiter unten: ein Nichts, verpackt als Auskunft. Das `0`
daneben ist der Hinweis — kein Eintrag heisst keine Messung.

## Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Dieses Repo

Default-Branch ist `master`, nicht `main` — der Frische-Check oben lautet hier
`git fetch origin master && git rev-list --count HEAD..origin/master`.

ruff ist an genau einer Stelle gepinnt: im `dev`-Extra von `pyproject.toml`.
`pip install -e ".[dev]"` liefert damit die CI-Version. **Die Nummer steht
bewusst nicht hier** — sie wird per Dependabot gehoben, und eine zweite Stelle
mit derselben Zahl wäre genau die Drift-Quelle, gegen die der Kommentar am Pin
selbst argumentiert: «Zwei Pins, die übereinstimmen müssen, sind eine
Drift-Quelle und keine Absicherung.»

Hier stand bis zum 19.9.2026 «ruff ist auf `0.16.3` gepinnt, an genau einer
Stelle» — und der Satz widerlegte sich selbst: Er war die zweite Stelle, und
als Dependabot am selben Morgen auf `0.16.5` hob, zeigte er ins Leere. Wer ihm
folgte, installierte 0.16.3 und lief in den Abbruch von
`check_ruff_pin.py`, der die CI-Version aus `pyproject.toml` liest. Die
aktuelle Nummer also dort nachsehen, nicht hier:

```bash
grep 'ruff==' pyproject.toml
```

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet. Genau so ist es am
19.9.2026 passiert — `/root/.local/bin/ruff` lag vor `/usr/local/bin/ruff`,
und der Install hatte nichts gemeldet. `check_ruff_pin.py` prüft deshalb beide
Wege, `ruff …` und `python -m ruff …`.

Gates, wörtlich aus `ci.yml` (Python 3.11 / 3.12 / 3.13):

<!-- gates:start -->
```bash
PYTHONPATH=src pytest tests/ -m "not live"
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py
python scripts/check_gate_docs.py
```
<!-- gates:end -->

**Ein sechstes Gate hängt an jedem PR, ausserhalb von `ci.yml`:**
`security.yml`. Es steht bewusst nicht im Block oben — der wird von
`check_gate_docs.py` gegen den Job `test` in `ci.yml` gehalten, und ein
fremder Eintrag dort machte diesen Gate rot. Lokal lässt es sich nicht
nebenbei nachfahren; ein roter PR bei grünen Tests ist meistens es.

Alle Gates des Blocks laufen auf allen drei Matrix-Feldern, keine
`if:`-Ausnahme; ein `fail-fast: false` steht nicht da.

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
