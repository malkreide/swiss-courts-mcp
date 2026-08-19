# SessionStart-Hook: Klon-Aktualität

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<default-branch>` liegt. Liegt er nicht
zurück, sagt er nichts.

## Warum

Ein veralteter Klon hat am 3.8.2026 **zweimal** eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Der Diff war in Ordnung;
gesucht wurde trotzdem dort. Die Prüfung kostet eine Sekunde und ersetzt eine
Fehlersuche in den falschen Dateien.

Dieselbe Prüfung steht als Handgriff in `CLAUDE.md` unter «Vor der Arbeit».
Ein Handgriff, an den man denken muss, ist genau dann vergessen, wenn er
gebraucht wird — der Hook macht daraus den Normalfall.

## Was er zusichert

1. **Er blockiert die Session nie.** Kein Netz, kein Remote, kein Git-Repo,
   detached HEAD, flatterndes DNS, abgelaufene Zugangsdaten — jeder dieser
   Fälle geht still durch (`exit 0`, keine Ausgabe). Das ist die erste
   Anforderung, nicht die letzte: ein Hook, der bei Netzproblemen die Arbeit
   anhält, wird nach dem zweiten Mal abgeschaltet und schützt danach gar
   nichts.
2. **Er hängt nicht.** Jeder *einzelne* Netzaufruf ist auf
   `CLAUDE_FRESHNESS_TIMEOUT` Sekunden gedeckelt (Standard: 5). Im schlimmsten
   Fall fallen zwei an (`ls-remote` und `fetch`), der Hook ist also bei 10
   Sekunden hart zu Ende — nachgemessen an einem Remote, der die Verbindung
   annimmt und dann schweigt. Zusätzlich deckelt `settings.json` den ganzen
   Hook auf 15 Sekunden: zwei unabhängige Grenzen, damit ein Ausfall der einen
   nicht den Sessionstart kostet. Interaktive Git-Prompts sind
   abgeschaltet (`GIT_TERMINAL_PROMPT=0`, Askpass auf `true`,
   SSH auf `BatchMode=yes`); ein Credential-Prompt ohne Terminal wartet sonst
   unbegrenzt.
3. **Er schweigt bei 0.** Ausgabe gibt es nur, wenn wirklich Commits fehlen.
4. **Er rät den Default-Branch nicht.** Autoritativ per `git ls-remote
   --symref origin HEAD`. Ist er nicht ermittelbar, schweigt der Hook, statt
   `main` anzunehmen. Dieses Repo nutzt `master`; die Annahme «main» hat schon
   einmal einen Branch 15 Commits alt werden lassen, weil der Abgleich still
   gegen eine nicht existierende Referenz lief.

   Der lokal gecachte `refs/remotes/origin/HEAD` wäre billiger, ist aber
   **gemessen unzuverlässig**: in einem Klon, der von einem anderen Klon
   stammt, zeigte er auf den dort ausgecheckten Feature-Branch. Der Hook hätte
   dann still den falschen Branch verglichen. Er dient deshalb nur noch als
   Rückfallebene, wenn der Remote nicht antwortet.

## Ein Netzaufruf im Normalfall

`ls-remote --symref origin HEAD` liefert Branch-Namen **und** Spitze des
Default-Branches in einem Aufruf. Ist diese Spitze lokal schon bekannt — der
Normalfall bei einem frischen Klon —, entfällt das `fetch` ganz und die
Prüfung kostet genau einen Netzaufruf. Geholt wird nur, wenn die Objekte
tatsächlich fehlen, also genau dann, wenn es etwas zu melden gibt.

## Wann er läuft

Bei `startup` und `resume` (Matcher in `.claude/settings.json`). Bei `clear`
und `compact` nicht: dort ändert sich der Klon nicht, die Meldung wäre
Wiederholung.

Der Hook liest bewusst kein stdin. Das Event-JSON käme zwar dort an, aber ein
Lesen daran ist eine weitere Hänge-Möglichkeit ohne Gegenwert — die Auswahl
der Auslöser macht der Matcher.

## Ausgabe

```
⚠️  Klon veraltet: claude/mein-branch liegt 15 Commits hinter origin/master.

    Auffrischen:  git fetch origin master && git merge origin/master

    Warum das gemeldet wird: ein veralteter Klon erzeugt eine rote CI, deren
    Ursache nicht im Diff steht — die fehlenden Commits sind typischerweise
    genau die, die das Gate einführen, an dem der Branch scheitert.
```

Der Hook frischt **nicht** selbst auf. Ein Merge beim Sessionstart, den
niemand angefordert hat, ändert den Arbeitsstand hinter dem Rücken des
Nutzers; das Kommando steht deshalb in der Meldung.

## Von Hand prüfen

```bash
# Normalfall gegen dieses Repo (schweigt, wenn der Klon aktuell ist):
.claude/hooks/session-start.sh; echo "exit=$?"

# Netzausfall simulieren — muss still und schnell mit exit=0 enden:
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.http://127.0.0.1:1/.insteadOf \
  GIT_CONFIG_VALUE_0=https://github.com/ \
  .claude/hooks/session-start.sh; echo "exit=$?"
```

## Nachgemessen

Ein Hook, der bei kaputtem Netz schweigt, sieht identisch aus wie einer, der
nie etwas findet. Jede Zusicherung ist deshalb einzeln neutralisiert und der
zugehörige Test musste fallen:

| neutralisiert | Testfall | Ergebnis ohne die Zusicherung |
|---|---|---|
| Default-Branch fest `main` statt `ls-remote` | Klon 3 hinter, Repo nutzt `master` | **stumm** — der Rückstand verschwindet spurlos (der Fehler von damals) |
| Schweigen bei 0 entfernt | aktueller Klon | meldet «liegt 0 Commits hinter» |
| `exit 0`-Schutz entfernt | Verzeichnis ohne Git-Repo | `exit 1` statt stumm |
| Deckel auf dem Netzaufruf entfernt | Remote nimmt an und schweigt | hängt unbegrenzt (extern bei 20s abgewürgt; mit Deckel: 6s) |
| `fetch` bei fehlenden Objekten übersprungen | Klon, danach 3 neue Commits im Remote | **stumm** trotz echtem Rückstand |

Kontrollprobe zur ersten Zeile: dieselbe `main`-Mutation meldet im `main`-Repo
weiterhin korrekt. Sie ist also nicht generell kaputt, sondern genau dort
blind, wo der Default-Branch anders heisst.

Nicht falsifizierbar: das `|| exit 0` hinter dem `fetch`. In jedem
konstruierbaren Fehlerfall leert git `FETCH_HEAD` selbst, sodass die
Leerprüfung danach ohnehin greift. Es bleibt als zweite Schicht stehen, weil
diese Aufräumzusage nirgends dokumentiert ist — aber es ist ungetestet, und
das gehört hier hin statt in eine Zusicherung, die niemand belegt hat.

Der Testaufbau (lokale Bare-Remotes mit `master` und `main`, ein Listener, der
Verbindungen annimmt und nie antwortet) lag im Scratchpad und ist bewusst
nicht Teil des Repos: er prüft den Hook, nicht den Server.
