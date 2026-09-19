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
  als Entwarnung für die gesperrte nehmen. Das ist dieselbe Asymmetrie wie
  bei der verschwundenen Codex-Meldung weiter unten.

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

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

## Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Zwischen erster und letzter Limit-Meldung liegen **25 h 15 min**. Das ist der
Abstand zweier Fehlschläge, nicht die Dauer einer Sperre. Wer ihn Untergrenze
nennt, hat die durchgehende Erschöpfung schon vorausgesetzt, die er belegen
soll: Öffnete sich das Fenster zwischendurch und schloss es sich durch neue
Auslöser wieder, waren es zwei kurze Sperren und nie eine von 25 Stunden.
Untergrenze einer *einzelnen* Sperre sind die 25 h 15 min nur unter genau dieser
Annahme — und die ist unbelegt.

Nach oben trägt die Rechnung dagegen. Die längste mit den Beobachtungen
verträgliche Sperre reicht vom letzten Erfolg um 08:41 bis zur abweichenden
Meldung um 08:22, also **47 h 41 min**; länger kann keine einzelne gewesen sein.
Wer stattdessen ab der ersten Limit-Meldung rechnet, unterschlägt die 67
Minuten, in denen das Kontingent schon weg gewesen sein kann, und nennt die
Spanne zwischen zwei Beobachtungen eine Obergrenze.

Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor der abweichenden
Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Vier** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann schreibt er einen gewöhnlichen Issue-Kommentar:

  ```
  Codex Review: Didn't find any major issues. Swish!
  ```

  Der Schlusssatz wechselt bei jedem Lauf («Delightful!», «Keep it up!»,
  «More of your lovely PRs please.»); stabil ist nur der Satz davor. Der
  Infokasten, den Codex unter jeden Review setzt, behauptet weiterhin eine
  Reaktion («otherwise it will react with 👍») — am 23.8. kam in sechs Repos
  die Meldung und in keinem die Reaktion. Der Kasten ist keine Quelle.
- **Der PR ist ein Draft** — darauf läuft *kein Review* an. Dass ein Draft
  deshalb **gar keinen** Kommentar bekommt, stand hier bis zum 19.9.2026 und ist
  widerlegt: PR #83 in `swiss-courts-mcp` wurde um 09:23:50 als Draft angelegt
  und bekam um **09:24:00** — zehn Sekunden später, `draft: true` — die
  Environment-Meldung von unten. Ein Draft ist also nicht stumm. Was dort
  ausbleibt, ist der Review, nicht die Reaktion.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

  **Diesen Text nicht als Auskunft über das Repo lesen.** Am 19.9.2026 kam er
  in `swiss-courts-mcp` auf dem Draft #83 um 09:24:00 — und um **09:10:47**,
  dreizehn Minuten davor, hatte im *selben Repo* der Review auf #82 mit
  `✅ Completed` geschlossen. Eine fehlende Environment kann das nicht erklären;
  ohne sie wäre #82 nicht gelaufen.

  **Und derselbe PR entschied es dann selbst.** Um 10:11:23 wurde #83 auf
  «ready for review» geschaltet, und um 10:11:28 stand die Summary-Tabelle auf
  `🔄 Running` — ein echter Lauf auf demselben Commit, in demselben Repo,
  47 Minuten nach der Meldung, die angeblich sagte, hier sei Codex nicht
  benutzbar. Er lief auch durch: `✅ Completed 10:12:27`, 64 s von «ready», und
  damit ganz normal innerhalb der gemessenen Spanne. Die Meldung **verhindert
  also keinen Review**; sie stand nur da, solange der PR ein Draft war.

  Sie erschien also auf einem Draft und blockierte den späteren Lauf nicht.
  **Mehr trägt die Messung nicht, und «an einen Draft gebunden» stand hier
  eine Fassung lang zu Unrecht.** Drei Drafts im selben Repo, derselbe
  Vormittag:

  | PR | angelegt | Environment-Meldung |
  |---|---|---|
  | #83 | 09:23:50 | **ja**, 09:24:00 (10 s) |
  | #84 | 10:14:09 | **nein** — 3 min 36 s Draft, nichts |
  | #85 | 10:31:55 | **ja**, 10:32:07 (12 s) |

  Zwei von drei. Sie kommt also **nicht auf jedem** Draft und ist ebenso wenig
  eine Aussage über das Repo. Wovon sie abhängt, was sie fachlich meint und ob
  ein Repo ohne Environment sie auch nach «ready» zeigt, bleibt
  **ungemessen** — auch der Abstand zum vorigen abgeschlossenen Lauf, der bei
  #84 mit 1 min 42 s deutlich kürzer war als bei #83 und #85 (je rund 13 min).
  Das ist eine Auffälligkeit in drei Datenpunkten und keine Ursache; wer sie
  zur Erklärung macht, hat dieselbe Verallgemeinerung noch einmal gebaut.

  Denn genau die stand hier: der Satz war aus #83 allein gebildet, bevor #84
  vorlag. Die Sorte Verallgemeinerung, gegen die diese Datei geschrieben ist,
  diesmal von ihr selbst — und #85 hätte sie wieder bestätigt, wenn #84 nicht
  dazwischen gelegen hätte. Zwei Beobachtungen, die in dieselbe Richtung
  zeigen, sind keine Regel.

  Nebenbefund zur Form: die Tabelle kam als **neuer** Kommentar
  (`5740959405`), die Environment-Meldung (`5740744996`) blieb unverändert
  daneben stehen. Das in-place-Überschreiben von unten gilt innerhalb der
  Summary-Tabelle, nicht zwischen den Formen — auf einem PR können also zwei
  Codex-Kommentare mit gegensätzlicher Aussage liegen, und der ältere ist nicht
  der gültige. Wer den ersten liest und aufhört, liest den falschen.

  Dieselbe Klasse wie der 403 weiter oben: dort war eine Sperre als Fund-
  Fehlschlag verpackt, hier ist eine unbekannte Ursache als
  Konfigurationsdiagnose verpackt. Die Lehre ist beide Male die gleiche — den
  Satz zitieren, nicht seine Selbstauskunft übernehmen, und eine
  Positivkontrolle im selben Repo dagegenhalten.

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt, eine Befundlos-Meldung **oder** die Summary-Tabelle mit
`✅ Completed` (die fünfte Form, gleich unten). Wer nur das Objekt gelten lässt,
zählt jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm
ein, den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe); ein Review **ohne** Befund und die
beiden Ausfallmeldungen — Kontingent wie Environment — sind gewöhnliche
Issue-Kommentare und trennen sich nur im Text. Beim Draft bleibt der Review aus
— ein kommentarloser Draft ist deshalb kein Beleg, sondern ein nicht
durchgeführter Test. Dass dort *nichts* kommt, stimmt allerdings nicht: die
Environment-Meldung erschien am 19.9. auf einem Draft (siehe oben). Ein
Kommentar auf einem Draft ist also kein Hinweis darauf, dass doch geprüft wurde.

Das sind verschiedene Abfragen — `get_reviews` fürs Objekt, `get_comments` für
alles andere; wer nur eine nimmt, übersieht den Rest. Genau so ist die
Limit-Meldung zuerst durchgerutscht.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Befundlos-, die Kontingent- **oder** die Environment-Meldung sein — drei
gegensätzliche Bedeutungen unter derselben Zahl. Den Text lesen, nicht die Zahl.
Und einen unbekannten vierten Text wörtlich zitieren, statt ihn in eine der
bekannten Schubladen zu zwingen: Dieser Abschnitt musste schon einmal von drei
auf vier Gründe wachsen, und die 👍-Reaktion stand hier zwei Fassungen lang als
Tatsache.

### Die fünfte Form: eine Summary-Tabelle, die sich selbst überschreibt

Genau das ist am 19.9.2026 eingetreten. In `swiss-courts-mcp` schrieb Codex auf
PR #73 und #74 einen Issue-Kommentar, den die vier Schubladen oben nicht
kennen — weder Befundlos-Meldung noch Ausfallmeldung, sondern eine Tabelle:

```
## Codex Review Summary

| Review | Status | Commit | Review trigger |
| --- | --- | --- | --- |
| 📝 **Code Review** | ✅ **Completed** <relative-time …> | `bc05ec7` | Draft marked ready |
```

Das ist keine fünfte Ursache fürs Schweigen, sondern eine fünfte **Belegform**,
und eine bessere als die Befundlos-Meldung: sie nennt den geprüften Commit und
den Abschlusszeitpunkt. Deshalb steht sie jetzt oben in der Belegliste.

**Der Kommentar wird an derselben Stelle überschrieben, nicht ergänzt.** Das ist
die Falle, und sie zeigt sich nur im Vergleich beider PRs — an einem allein wäre
sie unsichtbar geblieben:

| | #73 | #74 |
|---|---|---|
| ready for review | 06:36:16 | 06:56:15 |
| Merge | 06:36:19 | 06:56:19 |
| Kommentar `created_at` | 06:36:29 | 06:57:20 |
| Status zu diesem Zeitpunkt | 🔄 Running since 06:36:24 | ✅ Completed 06:57:18 |
| `updated_at` | 06:37:29 | 06:57:20 |
| Status zu *diesem* Zeitpunkt | ✅ Completed 06:37:28 | unverändert |

Auf #73 entstand der Kommentar als «Running» und wurde eine Minute später zu
«Completed» editiert — dieselbe `id` (`5739967817`). Auf #74 stand schon beim
Anlegen «Completed», `created_at` und `updated_at` sind identisch. #82 wiederholt
den #73-Fall am selben Tag und mit derselben Mechanik: `created_at` 09:09:50 mit
`🔄 Running`, `updated_at` 09:10:47 mit `✅ Completed`, `id` `5740680118`
unverändert. **`created_at`
sagt damit nichts über den Zustand des Reviews.** Wer den Kommentar einmal liest
und zwischenspeichert, sieht auf #73 für immer «Running»; wer ihn gar nicht
erneut abruft, hält einen abgeschlossenen Review für laufend. Den Text jedes Mal
frisch lesen, und `updated_at` als Zeitpunkt der letzten Statusänderung nehmen.

Was diese beiden Läufe **nicht** hergeben:

- **Wie ein Befund in dieser Form aussieht.** Beide Läufe endeten ohne Befund:
  `get_reviews` leer, kein «Didn't find any major issues»-Kommentar, nur die
  Tabelle. Ob ein Befund als Review-Objekt, als zusätzliche Tabellenzeile oder
  als beides erscheint, ist **ungemessen**. Der erste Lauf mit Befund unter
  dieser Oberfläche gehört hier nachgetragen.
- **Dass «Completed» ohne Befund-Kommentar «kein Befund» beweist.** Belegt ist
  nur: es wurde auf diesem Commit geprüft, und es wurde in keiner der bekannten
  Formen ein Befund gepostet. Das Fehlen der Befundlos-Meldung, die die erste
  Schublade als Marker führt, bleibt unerklärt.

Zwei Nebenbefunde aus denselben Läufen:

- **Die 👍-Reaktion blieb erneut aus** — `reactions.total_count: 0` auf beiden
  Kommentaren, während der Infokasten sie weiter behauptet. Mit #80 und #82,
  beide am 19.9. ebenfalls auf `total_count: 0` gemessen, steht die Behauptung
  des Kastens gegen zehn Beobachtungen (sechs am 23.8., vier hier). Auf #75 und
  #76 wurde die Reaktion nicht nachgesehen; die zählen also nicht mit.
- **Ein Merge bricht den Lauf nicht ab**, auch nicht mitten im Lauf. Drei PRs
  am 19.9., alle vor dem Ende des Reviews gemergt, alle drei liefen zu Ende:
  #73 (Merge 06:36:19, drei Sekunden nach «ready», fertig 06:37:28), #74 (Merge
  06:56:19, vier Sekunden nach «ready», fertig 06:57:18) und #75 — dort lag der
  Merge um 07:02:55 **46 Sekunden in den laufenden Review hinein** und stoppte
  ihn nicht (fertig 07:05:07). Der Review ist also nicht verloren; er kommt
  bloss zu spät, um noch etwas zu verhindern, und ein Befund stünde dann schon
  in `master`.

  **Und er startet sogar erst nach dem Merge.** Viermal am 19.9. lag der Merge
  *vor* dem `Running since`: #80 (Merge 08:34:10, Start 08:34:12), #82
  («ready» 09:09:41, Merge 09:09:45, Start 09:09:48, Kommentar 09:09:50),
  #83 («ready» 10:11:23, Merge 10:11:27, Start 10:11:28) und #84 («ready»
  10:17:45, Merge 10:17:47, Start 10:17:49). Der
  Auslöser ist das Umschalten von Draft auf ready, und ein bereits geschlossener
  PR hält ihn nicht auf. Das ist stärker als der Satz darüber: nicht bloss ein
  laufender Review übersteht den Merge, sondern ein noch nicht begonnener wird
  von ihm auch nicht verhindert. Wer also mergt, um dem Review zuvorzukommen,
  bekommt ihn trotzdem — nur eben in den Default-Branch hinein.

- **Die Dauer streut, und zwar erheblich.** Sieben Läufe am 19.9., Diffs
  ähnlicher Grösse im selben Repo; die ersten vier innerhalb von 34 Minuten,
  die übrigen drei am späteren Vormittag:

  | PR | «ready» | Start | `Completed` | ready → `Completed` |
  |---|---|---|---|---|
  | #73 | 06:36:16 | 06:36:24 | 06:37:28 | **72 s** |
  | #74 | 06:56:15 | — | 06:57:18 | **63 s** |
  | #75 | 07:02:03 | 07:02:09 | 07:05:07 | **184 s** |
  | #76 | 07:09:43 | — | 07:10:45 | **62 s** |
  | #82 | 09:09:41 | 09:09:48 | 09:10:47 | **66 s** |
  | #83 | 10:11:23 | 10:11:28 | 10:12:27 | **64 s** |
  | #84 | 10:17:45 | 10:17:49 | 10:18:50 | **65 s** |

  62 bis 184 Sekunden, Faktor 2,97 — der längste Lauf brauchte fast das
  Dreifache des kürzesten. Die Läufe fünf bis sieben (#82, #83 und #84, gut
  drei Stunden später) fügen mit 66, 64 und 65 s nichts Neues hinzu und
  **verschieben die Spanne nicht**; #82 steht hier, weil er die
  Positivkontrolle für den Befund ganz unten liefert, #83, weil sein Lauf die
  Environment-Meldung von oben entkräftet, #84 als dritte Kontrolle. Eine Wartezeit lässt sich daraus nicht ableiten, und
  ein früherer Stand dieses Abschnitts tat es doch: dort stand «wer eine Minute
  wartet, hat den Prüfer», gestützt auf die ersten zwei Punkte. Der dritte
  widerlegt es, der vierte hätte ihn wieder bestätigt.

  **Die Spalte «Start» ist der Grund, warum die Tabelle hier steht.** Ein
  früherer Stand nannte die Reihe «72, 63 und 178 Sekunden» — und die 178 waren
  vom *Start* gerechnet, die anderen beiden von «ready». Drei Zahlen
  nebeneinander, zwei Nullpunkte, und die Abweichung fiel nicht auf, weil das
  Ergebnis in die erwartete Richtung zeigte. Von «ready» an sind es 184.
  Codex läuft dort an, wo es gemessen ist, 8 bzw. 6 Sekunden nach dem
  Umschalten; auf #74 und #76 stand der Kommentar schon beim Anlegen auf
  `Completed`, ein Start ist dort nicht beobachtet.

  Wer Laufzeiten vergleicht, nennt also den Nullpunkt dazu. Für die
  Entscheidung zählt «ready»: das ist der Moment, den ein Mensch setzt.

  **Also nicht auf eine Zeitspanne warten, sondern auf den Beleg:** die
  Summary-Tabelle auf `✅ Completed`, mit dem Commit des Heads.

- **Und ein «Running», das lange steht, ist kein Abbruch.** Um 07:05:02 stand
  #75 seit 2 min 53 s auf `🔄 Running`, `updated_at` unverändert auf 07:02:10 —
  bei 63 und 72 Sekunden Erfahrung sah das nach «der Merge hat den Lauf
  erledigt» aus, und genau dieser Satz war schon für diese Datei getippt.
  **Fünf Sekunden später** stand `✅ Completed 07:05:07` da, `updated_at`
  07:05:08.

  Der Fehlschluss wäre nicht aus Unachtsamkeit entstanden, sondern aus einer
  Erwartung, die auf zwei Beobachtungen ruhte. Dieselbe Klasse wie die
  25-Stunden-Sperre weiter oben: der Abstand zweier Beobachtungen ist keine
  Eigenschaft der Sache. Wer aus einem stehenden Status eine Ursache macht,
  erfindet sie — nachgemessen wird, bis der Status sich ändert.

- **Aber es endet nicht immer, und dann hat die Regel darüber ein Loch.** Auf
  #80 stand die Tabelle am 19.9. um 10:29:53 noch auf `🔄 Running since
  08:34:12`, `updated_at` unverändert auf 08:34:14 — **116 Minuten**, achtmal
  nachgemessen (08:51, 09:08, 09:11, 09:21, 09:51, 10:12, 10:18, 10:29),
  `get_reviews` leer. Gegen 184 s Maximum der Reihe oben ist das der Faktor 38.

  **Die Positivkontrolle steht im selben Repo und am selben Vormittag, und
  inzwischen dreifach:** #82 wurde 35 Minuten *nach* #80 ausgelöst und war nach
  66 s fertig, #83 nach 64 s, #84 nach 65 s. Ein erschöpftes Kontingent, eine
  fehlende Environment oder ein Ausfall des Dienstes erklären #80 damit nicht —
  sonst wären die drei mitgefallen. Genau so wird aus einem «nicht fertig» eine
  Messung: eine gleichzeitige Abfrage findet etwas.

  Was die Beobachtungen **nicht** hergeben: die Ursache. Und ob dieser Lauf je
  endet — die 116 Minuten sind der Abstand zweier Beobachtungen, nicht eine
  Dauer, und der Absatz darüber gilt weiter: ein stehender Status ist kein
  Abbruch.

  **Praktisch heisst das, dass «auf den Beleg warten» eine Abbruchbedingung
  braucht.** Die Regel unten sagt zu Recht, keine Sekunden zu zählen — aber
  wer ohne Frist auf ein `Completed` wartet, das nicht kommt, wartet endlos.
  Steht der Status weit jenseits der gemessenen Spanne, also nach einer
  Positivkontrolle im selben Repo: den Zustand **datiert festhalten** und die
  Ursache offen nennen, statt weiter zu pollen oder ihn zu deuten. Ob ein
  `@codex review` auf einem gemergten PR einen neuen Lauf auslöst, ist
  **ungemessen** — der naheliegende Ausweg ist also keiner, solange es niemand
  geprüft hat.

Und ein befundloser Lauf ist kein Freispruch. Am 23.8. lief derselbe Text durch
42 Reviews: 36 meldeten denselben P2-Befund, 6 die Befundlos-Meldung — gleiche
Eingabe, gegenteiliges Urteil, alles in denselben neun Minuten. Ein sauberer
Lauf sagt damit etwas über den Lauf, nicht über den Text. Wer sein Häkchen
daran hängt, hängt es an einen Münzwurf.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden, am 19.9. in `swiss-courts-mcp` noch fünfmal dasselbe (#73:
drei Sekunden, #74: vier, #82: vier, #83: vier, #84: **zwei**). Codex wird beim
Umschalten von Draft auf ready
ausgelöst und braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und
den Review nicht abgewartet.

**Der lehrreichste Fall ist der dritte, und er sieht gar nicht nach Eile aus.**
PR #75 wurde am 19.9. **52 Sekunden** nach «ready for review» gemergt — mehr als
das Zehnfache der drei bzw. vier Sekunden, eine Pause, die wie bewusstes
Abwarten aussieht. Sie reichte trotzdem nicht: von «ready» bis `Completed`
vergingen dort **184 Sekunden**, und der Merge lag 46 Sekunden nach dem Start
des Reviews.

Wie lange es dauert, steht oben bei der fünften Form, und die Antwort ist
unbrauchbar als Frist: **72, 63, 184, 62, 66, 64 und 65 Sekunden** bei sieben
ähnlichen Diffs desselben Repos an einem Vormittag; die ersten vier lagen in
34 Minuten. Der längste Lauf war fast dreimal so lang wie der kürzeste, und der
kürzeste kam unmittelbar nach ihm — eine Wartemarke aus den ersten beiden Läufen
hätte den dritten verfehlt und wäre von den vier folgenden wieder bestätigt
worden. Sechs von sieben liegen zwischen 62 und 72 Sekunden, und genau das macht
die Marke verführerisch. Genau so entsteht eine Regel, die meistens stimmt und im
entscheidenden Fall nicht. Der Lauf wird dabei
nicht abgebrochen; er endet nur, wenn niemand mehr etwas davon hat, und ein
Befund stünde dann schon im Default-Branch.

Deshalb ist die Regel nicht «kurz warten», sondern **auf den Beleg warten**: die
Summary-Tabelle auf `✅ Completed` mit dem Commit des Heads. Wer Sekunden zählt,
wettet gegen eine Streuung, die niemand gemessen hat — und hat am Ende wieder
ein Häkchen und keinen Review.

### Vor dem Merge auf den Beleg warten

Entschieden am 19.9.2026, nachdem an diesem einen Vormittag **sechs** PRs
zwischen zwei und vier Sekunden nach «ready for review» gemergt worden waren
und der Review jedes Mal erst danach anlief. Verbindlich, nicht als Rat:

1. Draft auf **ready** schalten. Noch nicht mergen.
2. Den Beleg **messen**, nicht abwarten: `get_comments` **und** `get_reviews`,
   jedes Mal frisch gelesen (`created_at` sagt nichts über den Zustand, und
   auf einem PR können zwei Kommentare mit gegensätzlicher Aussage liegen —
   der ältere ist nicht der gültige).
3. Der Beleg ist die Summary-Tabelle auf `✅ Completed` **mit dem Commit des
   Heads**, oder eine der anderen Belegformen oben. Erst dann mergen.
4. Steht ein Befund da, wird er behoben oder begründet beantwortet — vor dem
   Merge, und das ist der ganze Zweck der Regel.

**Die Regel braucht eine Abbruchbedingung, sonst wartet sie endlos.** #80 belegt
es: seit 08:34:12 auf `🔄 Running`, nach 116 Minuten und acht Messpunkten
unverändert, während drei spätere Läufe im selben Repo nach 64 bis 66 Sekunden
durchliefen. Bleibt der Status weit jenseits der gemessenen Spanne von 62 bis
184 Sekunden und zeigt eine Positivkontrolle im selben Repo, dass Codex läuft:
den Zustand **datiert festhalten**, den Fall zur Entscheidung vorlegen und die
Ursache offen nennen — nicht weiter pollen, nicht deuten, und nicht stillschweigend
doch mergen. Ob ein `@codex review` einen neuen Lauf auslöst, ist **ungemessen**
und deshalb kein Ausweg.

Ein Merge ohne Beleg ist damit eine bewusste Entscheidung des Menschen, keine
Panne — aber sie wird benannt, und der Review landet dann im Default-Branch,
wo ein Befund einen Folge-PR braucht.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die Lücke oben
schliesst das Fünf-Stunden-Fenster nicht aus: Es kann sich zwischendurch
geöffnet und durch neue Auslöser wieder erschöpft haben. Das auszuschliessen
bräuchte den Nachweis, dass in der ganzen Spanne kein einziger Review durchlief
— den gibt es nicht, weil nur Fehlschläge beobachtet wurden. Eine lange Reihe
von Fehlschlägen belegt eine lange Reihe von Fehlschlägen, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

**Umgekehrt gilt das nicht:** die Meldung belegt nicht, dass für dieses Repo
keine Environment existiert. Am 19.9.2026 kam sie in `swiss-courts-mcp`
dreizehn Minuten nach einem abgeschlossenen Review desselben Repos — und auf
demselben PR lief 47 Minuten später, nach dem Umschalten auf «ready», ein
echter Review an. Bevor also jemand eine Environment anlegt, weil die Meldung
es verlangt: nachsehen, ob im selben Repo kurz zuvor ein Review durchlief, und
ob der PR ein Draft war. Trifft eines zu, ist die Meldung unerklärt und die
Environment nicht die Ursache. Umgekehrt ist ihr **Ausbleiben** auf einem Draft
ebenfalls nichts — von drei Drafts desselben Vormittags bekamen sie zwei, #84
nicht.

---

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
