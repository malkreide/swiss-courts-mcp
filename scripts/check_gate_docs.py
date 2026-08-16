"""
Dokumentierte Befehle gegen die halten, die die Workflows wirklich fahren.

Zwei Regionen, zwei Verträge — weil `ci.yml` und `live.yml` nicht dasselbe
versprechen.

**Region `gates`** — Quelle ist der Job `test` in `ci.yml`. Ein Schritt ist
ein Gate, wenn seine `run:`-Zeile die Marke `# gate` trägt; dann muss er in
jeder Doku-Datei stehen. Gate-Schritte bleiben dafür einzeilig; ein
mehrzeiliges `run:` bricht den Check ab, statt zu raten, welche Zeile das
Gate ist.

Die Marke ist eine Positivliste, und das hat einen Preis: Ein neues Gate,
das niemand markiert, wird nicht eingefordert. Zwei Dinge federn das ab —
die übersprungenen Schritte stehen in der Ausgabe (auch wenn alles grün
ist), und wer die Marke von einem *bestehenden* Gate entfernt, macht den
Check trotzdem rot: Der Befehl steht dann in der Doku, aber nicht mehr in
der Gate-Liste, und der Abgleich läuft in beide Richtungen.

**Region `live`** — Quelle ist der Job `live` in `live.yml`. Hier ist fast
alles CI-Maschinerie: `set +e`, `--junitxml`, `tee`, die Einordnung des
Ergebnisses, das Issue-Skript. Nichts davon fährt ein Mensch von Hand, und
nichts davon gehört in eine Doku. Was zählt, ist die eine Frage, die eine
Doku beantworten muss: *wie rufe ich die Live-Suite lokal auf?* Also wird
genau der pytest-Aufruf verglichen, und die Plumbing-Teile fallen weg
(alles ab der ersten Pipe, `--junitxml=…`, `2>&1`).

Verglichen wird in beiden Regionen nach einer kleinen, bewussten
Normalisierung — sonst erzwingt der Check Kosmetik statt Inhalt:

  - führende Env-Zuweisungen (`PYTHONPATH=src …`) fallen weg. Nach
    `pip install -e ".[dev]"` ist das Paket importierbar, die Doku darf den
    Präfix also weglassen.
  - `-v` / `--verbose` fällt weg. Ausführlichkeit ist keine Zusicherung.
  - Anführungszeichen werden vereinheitlicht (`-m "not live"` und
    `-m 'not live'` sind derselbe Befehl).

Alles andere zählt: ein fehlendes `scripts/` ist eine Abweichung, ein
fehlendes Gate erst recht, und `-m live` gegen `-m "live and not slow"` auch.

Die Marker stehen als HTML-Kommentare in den Dateien und sind im gerenderten
Markdown unsichtbar:

    <!-- gates:start -->
    ```bash
    …
    ```
    <!-- gates:end -->

Welche Datei welche Region führen muss, steht unten in `REGIONS`. Zurzeit
führen alle fünf Dateien beide Regionen. Dass die Live-Suite kein PR-Gate
ist, macht sie nicht unwichtig — sie ist das Einzige, was einen geänderten
Vertrag mit der Quelle überhaupt bemerkt, und wer den Client anfasst, sollte
sie von Hand kennen. Der Unterschied steht in der Prosa neben dem Block,
nicht in seiner Abwesenheit.

Hintergrund: Die Gate-Liste ist zweimal auseinandergelaufen. Die CI lintete
`src/ tests/ scripts/`, während vier Dateien `src/ tests/` nannten, und
`ruff format --check` wie der Versions-Sync fehlten ganz. Wer die Doku
kopierte, fuhr das Gate unvollständig und sah die Differenz erst rot in der
CI — an Code, den er nicht angefasst hatte. Eine Doku, die niemand erzwingt,
beschreibt irgendwann einen Zustand von früher.

Verwendung:
    python scripts/check_gate_docs.py     # exit 1 bei Abweichung

Bewusst nur Standardbibliothek und ein Minimal-Parser für die zwei Jobs —
für einen Doku-Check lohnt keine YAML-Abhängigkeit.
"""

import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

ALL_DOCS = (
    "CLAUDE.md",
    "README.md",
    "README.de.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.de.md",
)

# Positivliste statt Ausschlussliste: Ein Schritt ist ein Gate, wenn seine
# `run:`-Zeile die Marke trägt — als YAML-Kommentar direkt am Befehl:
#
#     - name: Lint
#       run: ruff check src/ tests/ scripts/  # gate
#
# Die Marke steht an der Zeile, um die es geht, nicht in einer Liste hier;
# YAML wirft sie beim Parsen weg, GitHub sieht sie nie. Alles ohne Marke
# gilt als Beiwerk und wird übersprungen — aber nicht stillschweigend: Die
# übersprungenen Schritte stehen in der Ausgabe, auch im Erfolgsfall.
GATE_TAG = "gate"
_TRAILING_COMMENT = re.compile(r"\s+#\s*(?P<tag>.*?)\s*$")

_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_NOISE = {"-v", "--verbose"}

# CI-Maschinerie rund um den Live-Aufruf. Ein Report-Pfad und eine
# Umleitung sind kein Teil dessen, was ein Mensch tippt.
_CI_PLUMBING = re.compile(r"^(--junitxml=|--junit-xml=|\d?>&?\d?$|>>?$)")

_RUN = re.compile(r"^(?P<indent>\s*)(?:-\s+)?run:\s*(?P<value>.*)$")
_BLOCK_SCALAR = {"|", "|-", "|+", ">", ">-", ">+"}


@dataclass(frozen=True)
class Region:
    name: str
    workflow: str
    job: str
    docs: tuple[str, ...]
    # "marked": nur Schritte mit der Gate-Marke, dafür einzeilig erzwungen.
    # "pytest": nur die pytest-Aufrufe, mehrzeilige Blöcke sind erlaubt.
    select: str

    @property
    def marked(self) -> bool:
        return self.select == "marked"

    @property
    def start(self) -> str:
        return f"<!-- {self.name}:start -->"

    @property
    def end(self) -> str:
        return f"<!-- {self.name}:end -->"

    @property
    def path(self) -> Path:
        return WORKFLOWS / self.workflow


REGIONS = (
    Region(name="gates", workflow="ci.yml", job="test", docs=ALL_DOCS, select="marked"),
    Region(name="live", workflow="live.yml", job="live", docs=ALL_DOCS, select="pytest"),
)


def join_continuations(lines: list[str]) -> list[str]:
    """Zeilen, die auf `\\` enden, mit der nächsten zusammenziehen."""
    joined: list[str] = []
    buffer = ""
    for line in lines:
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            buffer += stripped[:-1].rstrip() + " "
            continue
        joined.append(buffer + stripped.strip() if buffer else line)
        buffer = ""
    if buffer:
        joined.append(buffer.strip())
    return joined


def normalise(command: str) -> str:
    """Auf die Form bringen, in der zwei Schreibweisen desselben Befehls gleich sind."""
    tokens = shlex.split(command)
    while tokens and _ENV_ASSIGN.match(tokens[0]):
        tokens.pop(0)
    # Alles ab der ersten Pipe ist Weiterverarbeitung, nicht der Befehl.
    if "|" in tokens:
        tokens = tokens[: tokens.index("|")]
    tokens = [t for t in tokens if t not in _NOISE and not _CI_PLUMBING.match(t)]
    return " ".join(shlex.quote(t) for t in tokens)


def job_body(path: Path, job: str) -> list[str]:
    """Die Zeilen eines Jobs aus `jobs:` — alles unterhalb, tiefer eingerückt."""
    body: list[str] = []
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(rf"^  {re.escape(job)}:\s*$", line):
            inside = True
            continue
        if not inside:
            continue
        # Leerzeilen gehören dazu; ein nicht-leerer Eintrag auf Job-Ebene
        # oder darüber beendet den Block.
        if line.strip() and not line.startswith("    "):
            break
        body.append(line)
    if not inside:
        sys.exit(f"FEHLER: Job {job!r} steht nicht in {path.relative_to(ROOT)}.")
    return body


def split_tag(value: str) -> tuple[str, str | None]:
    """Befehl und YAML-Kommentar am Zeilenende trennen.

    `ruff check src/  # gate` → `("ruff check src/", "gate")`. Ein `#` in
    Anführungszeichen ist kein Kommentar — deshalb erst zerlegen, dann
    entscheiden.
    """
    try:
        tokens = shlex.split(value, comments=True)
    except ValueError:
        return value, None
    command = " ".join(tokens) if tokens else ""
    match = _TRAILING_COMMENT.search(value)
    if match and command and not value.startswith("#"):
        # Nur wenn der Kommentar wirklich abgetrennt wurde — sonst stand das
        # `#` in Anführungszeichen und gehört zum Befehl.
        if len(shlex.split(value)) != len(tokens):
            return value[: match.start()].strip(), match.group("tag")
    return value, None


def run_commands(region: Region) -> list[tuple[str, str | None]]:
    """Befehlszeilen der `run:`-Schritte eines Jobs, je mit ihrer Marke.

    Nur `run:` — `with:`/`script:` bleiben aussen vor, sonst liest der Check
    JavaScript-Text als Befehl.
    """
    lines = job_body(region.path, region.job)
    commands: list[tuple[str, str | None]] = []
    index = 0
    while index < len(lines):
        match = _RUN.match(lines[index])
        if not match:
            index += 1
            continue
        value = match.group("value").strip()
        if value not in _BLOCK_SCALAR:
            commands.append(split_tag(value))
            index += 1
            continue
        if region.marked:
            # Ein mehrzeiliges `run:` liesse sich nur raten — welche Zeile ist
            # das Gate, welche Beiwerk? Lieber hier laut scheitern als der
            # Doku eine Zusicherung geben, die niemand geprüft hat.
            sys.exit(
                f"FEHLER: Job {region.job!r} in {region.path.relative_to(ROOT)} enthält ein "
                f"mehrzeiliges `run:`. Gate-Schritte einzeilig halten, sonst kann dieser "
                f"Check sie nicht gegen die Doku halten."
            )
        # Blockinhalt: alles, was tiefer eingerückt ist als der `run:`-Schlüssel.
        depth = len(match.group("indent"))
        block: list[str] = []
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip() and (len(candidate) - len(candidate.lstrip())) <= depth:
                break
            block.append(candidate)
            index += 1
        commands.extend((line, None) for line in join_continuations(block))
    return commands


def invokes_pytest(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    return any(token == "pytest" or token.endswith("/pytest") for token in tokens)


def workflow_commands(region: Region) -> tuple[list[str], list[str]]:
    """(gewählte Befehle, übersprungene Befehle) für eine Region."""
    found: list[str] = []
    skipped: list[str] = []
    for command, tag in run_commands(region):
        text = command.strip()
        if not text or text.startswith("#"):
            continue
        chosen = tag == GATE_TAG if region.marked else invokes_pytest(text)
        (found if chosen else skipped).append(text)
    if not found:
        hint = (
            f"Trägt kein Schritt die Marke `# {GATE_TAG}`?" if region.marked else "Parser kaputt?"
        )
        sys.exit(
            f"FEHLER: In Job {region.job!r} ({region.path.relative_to(ROOT)}) steht kein "
            f"einziger Befehl für die Region {region.name!r}. {hint}"
        )
    return found, skipped


def doc_commands(path: Path, region: Region) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if text.count(region.start) != 1 or text.count(region.end) != 1:
        sys.exit(
            f"FEHLER: {path.relative_to(ROOT)} braucht genau ein Markerpaar "
            f"{region.start} … {region.end} um den Block mit den Befehlen."
        )
    body = text.split(region.start, 1)[1].split(region.end, 1)[0]
    commands = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        commands.append(line)
    return commands


def check(region: Region) -> tuple[list[str], list[str], list[str]]:
    expected, skipped = workflow_commands(region)
    wanted = {normalise(c) for c in expected}

    problems: list[str] = []
    for name in region.docs:
        path = ROOT / name
        if not path.exists():
            problems.append(f"[{region.name}] {name}: Datei fehlt.")
            continue
        found = {normalise(c) for c in doc_commands(path, region)}
        for missing in sorted(wanted - found):
            problems.append(f"[{region.name}] {name}: nennt den Befehl nicht — {missing}")
        for extra in sorted(found - wanted):
            problems.append(
                f"[{region.name}] {name}: nennt einen Befehl, den der Workflow "
                f"nicht fährt — {extra}"
            )
    return expected, skipped, problems


def main() -> int:
    problems: list[str] = []
    summary: list[str] = []
    # Was der Check NICHT geprüft hat, gehört in dieselbe Ausgabe wie das,
    # was er geprüft hat. Eine Auswahl, die man nicht sieht, liest sich wie
    # Vollständigkeit.
    skipped_report: list[str] = []
    for region in REGIONS:
        expected, skipped, found = check(region)
        problems.extend(found)
        summary.append(
            f"{region.name}: {len(expected)} aus {region.path.relative_to(ROOT)} "
            f"in {len(region.docs)} Dateien"
        )
        if found:
            summary[-1] += "  <- Abweichung"
        # Nur für die markierte Region: Dort kann ein übersprungener Schritt
        # ein vergessenes Gate sein. In der Live-Region ist das Übersprungene
        # per Konstruktion Beiwerk (`set +e`, `echo`, die Einordnung) — jede
        # Zeile davon zu melden, verdeckt den einen Fall, der zählt.
        if region.marked:
            skipped_report.extend(skipped)

    if problems:
        print("DRIFT: Die dokumentierten Befehle weichen von den Workflows ab.", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("", file=sys.stderr)
        for region in REGIONS:
            print(f"{region.path.relative_to(ROOT)}, Job {region.job!r}:", file=sys.stderr)
            for command in workflow_commands(region)[0]:
                print(f"  {command}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Verglichen wird ohne führende Env-Zuweisungen, ohne `-v` und ohne "
            "CI-Beiwerk (Pipes, --junitxml, Umleitungen); alles andere zählt.",
            file=sys.stderr,
        )
        return 1

    print(f"Gate-Doku OK ({'; '.join(summary)})")
    for command in skipped_report:
        print(f"  übersprungen, keine Marke `# {GATE_TAG}`: {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
