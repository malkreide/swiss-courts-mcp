#!/usr/bin/env bash
#
# SessionStart-Hook: meldet, wie viele Commits der ausgecheckte Stand hinter
# origin/<default-branch> liegt. Bei 0 schweigt er, und in jedem Fehlerfall
# ebenfalls.
#
# WARUM (ausführlich in .claude/hooks/README.md):
# Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
# Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
# die das Gate einführten, an dem der Branch scheiterte. Die Prüfung kostet
# eine Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.
#
# ABSOLUTER VORRANG: Dieser Hook blockiert die Session nie. Kein Netz, kein
# Remote, detached HEAD, flatterndes DNS — jeder dieser Fälle geht still durch
# (exit 0). Ein Hook, der bei Netzproblemen die Arbeit anhält, wird nach dem
# zweiten Mal abgeschaltet und schützt danach gar nichts.
#
# Daraus folgen drei Entscheidungen, die absichtlich so aussehen:
#   - kein `set -e` / `set -u`: ein Abbruch mitten im Skript endet non-zero,
#     und ein non-zero Hook meldet sich beim Nutzer. Stattdessen ist jeder
#     Schritt einzeln abgesichert und jeder Ausgang ein explizites `exit 0`.
#   - jeder Netzaufruf hart gedeckelt (siehe run_capped).
#   - keine interaktiven Git-Prompts: ein Credential-Prompt ohne Terminal
#     wartet ewig, und das wäre exakt das Blockieren, das hier ausgeschlossen
#     ist.
# Es wird auch kein stdin gelesen: der Hook bekommt sein JSON über stdin, aber
# ein Lesen daran ist eine weitere Hänge-Möglichkeit für null Gewinn. Die
# Auswahl der Auslöser (`startup`, `resume`) macht der Matcher in settings.json.

# Sekunden, die ein EINZELNER Netzaufruf höchstens dauern darf. Im schlimmsten
# Fall fallen zwei an (ls-remote und fetch), der Hook ist also auf das Doppelte
# gedeckelt — 10s bei Standardwert. `settings.json` deckelt den Hook zusätzlich
# auf 15s; zwei unabhängige Grenzen, damit ein Ausfall der einen den
# Sessionstart nicht kostet.
FETCH_TIMEOUT="${CLAUDE_FRESHNESS_TIMEOUT:-5}"

# Git darf unter keinen Umständen nach Zugangsdaten fragen — ohne Terminal
# wartet es sonst unbegrenzt. `true` als Askpass liefert leere Eingaben, git
# scheitert dadurch sofort statt zu warten.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=true
export SSH_ASKPASS=true
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes}"

# Netzaufruf mit hartem Deckel. `timeout` fehlt auf macOS ohne coreutils;
# dann übernimmt ein portabler Watchdog, damit die Deckelung nicht davon
# abhängt, was zufällig installiert ist.
run_capped() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "$FETCH_TIMEOUT" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$FETCH_TIMEOUT" "$@"
  else
    "$@" &
    _pid=$!
    ( sleep "$FETCH_TIMEOUT"; kill -9 "$_pid" ) >/dev/null 2>&1 &
    _watchdog=$!
    wait "$_pid"
    _rc=$?
    kill "$_watchdog" >/dev/null 2>&1
    return "$_rc"
  fi
}

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# Kein Repo, kein Remote, nichts ausgecheckt: still raus. Ein frischer Klon
# ohne Commits hat kein auflösbares HEAD.
git rev-parse --git-dir            >/dev/null 2>&1 || exit 0
git remote get-url origin          >/dev/null 2>&1 || exit 0
git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || exit 0

# Default-Branch und Remote-Stand ermitteln — beides aus EINEM Aufruf.
#
# Der Default-Branch wird gefragt, nicht geraten. Die naheliegende Abkürzung,
# den lokal gecachten `refs/remotes/origin/HEAD` zu nehmen, ist gemessen
# unzuverlässig: in einem Klon, der von einem anderen Klon stammt, zeigte er
# auf den dort ausgecheckten Feature-Branch statt auf den Default-Branch. Der
# Hook hätte dann still den falschen Branch verglichen — eine falsche Antwort
# ist schlimmer als keine. Der Cache dient deshalb nur noch als Rückfallebene,
# wenn der Remote nicht antwortet.
#
# `ls-remote --symref origin HEAD` liefert zwei Zeilen:
#     ref: refs/heads/master<TAB>HEAD
#     <sha><TAB>HEAD
# also Branch-Name UND Spitze des Default-Branches in einem gedeckelten Aufruf.
ls_out=$(run_capped git ls-remote --symref origin HEAD 2>/dev/null)

default_branch=$(printf '%s\n' "$ls_out" |
  sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' | head -n 1)
remote_head=$(printf '%s\n' "$ls_out" |
  sed -n 's|^\([0-9a-f]\{7,\}\)[[:space:]]\{1,\}HEAD$|\1|p' | head -n 1)

# Rückfallebene: Remote stumm (kein Netz, alter Server ohne --symref). Dann
# der lokale Cache — mit dem Vorbehalt von oben.
if [ -z "$default_branch" ]; then
  ref=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)
  [ -n "$ref" ] && default_branch="${ref#origin/}"
fi

# Nicht ermittelbar heisst schweigen, nicht `main` annehmen.
[ -n "$default_branch" ] || exit 0

# Die Spitze schon lokal? Dann ist gar kein fetch nötig — das ist der
# Normalfall (frischer Klon) und macht die Prüfung zu einem einzigen
# Netzaufruf. Nur wenn die Objekte fehlen, wird wirklich geholt.
if [ -z "$remote_head" ] ||
   ! git rev-parse --verify --quiet "${remote_head}^{commit}" >/dev/null 2>&1; then
  # Ab hier liegen die Netzfälle: kein Netz, DNS weg, Remote verschwunden,
  # Auth abgelaufen. Jeder davon ist ein stiller Ausgang.
  run_capped git fetch --quiet origin "$default_branch" >/dev/null 2>&1 || exit 0

  # FETCH_HEAD nur nach erfolgreichem fetch lesen — sonst stünde dort der
  # Stand eines früheren Laufs und die Meldung wäre schlicht falsch.
  remote_head=$(git rev-parse --verify --quiet FETCH_HEAD 2>/dev/null)
  [ -n "$remote_head" ] || exit 0
fi

behind=$(git rev-list --count "HEAD..$remote_head" 2>/dev/null)

# Nur melden, wenn wirklich Commits fehlen. Alles andere — 0, leer, kaputt —
# schweigt.
case "$behind" in
  '' | *[!0-9]*) exit 0 ;;
  0)             exit 0 ;;
esac

# Detached HEAD ist kein Fehlerfall: der Abstand ist dort genauso messbar und
# genauso relevant, nur hat der Stand keinen Branch-Namen.
current=$(git symbolic-ref --quiet --short HEAD 2>/dev/null)
if [ -z "$current" ]; then
  current="detached HEAD ($(git rev-parse --short HEAD 2>/dev/null))"
fi

commit_word="Commits"
[ "$behind" = "1" ] && commit_word="Commit"

printf '%s\n' \
  "⚠️  Klon veraltet: $current liegt $behind $commit_word hinter origin/$default_branch." \
  "" \
  "    Auffrischen:  git fetch origin $default_branch && git merge origin/$default_branch" \
  "" \
  "    Warum das gemeldet wird: ein veralteter Klon erzeugt eine rote CI, deren" \
  "    Ursache nicht im Diff steht — die fehlenden Commits sind typischerweise" \
  "    genau die, die das Gate einführen, an dem der Branch scheitert."

exit 0
