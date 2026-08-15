"""
Dokumentierte Gate-Befehle gegen die halten, die die CI wirklich fährt.

`ci.yml` ist die einzige Quelle der Wahrheit. Verglichen wird die Liste der
Gate-Befehle im Job `test` mit dem, was jede Doku-Datei zwischen ihren
Gate-Markern nennt:

  - `CLAUDE.md`, `README.md`, `README.de.md`
  - `CONTRIBUTING.md`, `CONTRIBUTING.de.md`

Hintergrund: Genau diese Liste ist schon zweimal auseinandergelaufen. Die CI
lintete `src/ tests/ scripts/`, während vier Dateien `src/ tests/` nannten,
und `ruff format --check` wie der Versions-Sync fehlten ganz. Wer die Doku
kopierte, fuhr das Gate unvollständig und sah die Differenz erst rot in der
CI — an Code, den er nicht angefasst hatte. Eine Doku, die niemand erzwingt,
beschreibt irgendwann einen Zustand von früher.

Die Marker stehen als HTML-Kommentare in den Dateien und sind im gerenderten
Markdown unsichtbar:

    <!-- gates:start -->
    ```bash
    …
    ```
    <!-- gates:end -->

Verglichen wird nicht buchstäblich, sondern nach einer kleinen, bewussten
Normalisierung — sonst erzwingt der Check Kosmetik statt Inhalt:

  - führende Env-Zuweisungen (`PYTHONPATH=src …`) fallen weg. Nach
    `pip install -e ".[dev]"` ist das Paket importierbar, die Doku darf den
    Präfix also weglassen.
  - `-v` / `--verbose` fällt weg. Ausführlichkeit ist keine Zusicherung.
  - Anführungszeichen werden vereinheitlicht (`-m "not live"` und
    `-m 'not live'` sind derselbe Befehl).

Alles andere zählt: ein fehlendes `scripts/` ist eine Abweichung, ein
fehlendes Gate erst recht.

Verwendung:
    python scripts/check_gate_docs.py     # exit 1 bei Abweichung

Bewusst nur Standardbibliothek und ein Minimal-Parser für den einen Job in
`ci.yml` — für einen Doku-Check lohnt keine YAML-Abhängigkeit.
"""

import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CI = ROOT / ".github" / "workflows" / "ci.yml"

# Nur dieser Job. `live.yml` läuft nach Plan gegen die echte Quelle und ist
# kein Gate, das man vor einem Commit fährt.
JOB = "test"

DOCS = (
    "CLAUDE.md",
    "README.md",
    "README.de.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.de.md",
)

START = "<!-- gates:start -->"
END = "<!-- gates:end -->"

# Aufbau, kein Gate. Was hier nicht steht, gilt als Gate — ein neuer
# Prüfschritt in der CI wird also automatisch einforderbar, statt still
# undokumentiert zu bleiben. Ein neuer *Aufbau*-Schritt schlägt dafür hier
# auf und will ergänzt werden; laut scheitern ist besser als still nichts
# prüfen.
SETUP_PREFIXES = ("pip install", "pip3 install", "python -m pip", "uv pip install")

_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_NOISE = {"-v", "--verbose"}

# `run: <Befehl>` — auch als erste Zeile eines Listeneintrags (`- run: …`).
_RUN = re.compile(r"^\s*(?:-\s+)?run:\s*(?P<value>.*)$")
_BLOCK_SCALAR = {"|", "|-", "|+", ">", ">-", ">+"}


def normalise(command: str) -> str:
    """Auf die Form bringen, in der zwei Schreibweisen desselben Befehls gleich sind."""
    tokens = shlex.split(command)
    while tokens and _ENV_ASSIGN.match(tokens[0]):
        tokens.pop(0)
    tokens = [t for t in tokens if t not in _NOISE]
    return " ".join(shlex.quote(t) for t in tokens)


def job_body(text: str, job: str) -> list[str]:
    """Die Zeilen eines Jobs aus `jobs:` — alles unterhalb, tiefer eingerückt."""
    lines = text.splitlines()
    body: list[str] = []
    inside = False
    for line in lines:
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
        sys.exit(f"FEHLER: Job {job!r} steht nicht in {CI.relative_to(ROOT)}.")
    return body


def ci_gates() -> list[str]:
    gates: list[str] = []
    for line in job_body(CI.read_text(encoding="utf-8"), JOB):
        match = _RUN.match(line)
        if not match:
            continue
        value = match.group("value").strip()
        if value in _BLOCK_SCALAR:
            # Ein mehrzeiliges `run:` liesse sich nur raten — welche Zeile ist
            # das Gate, welche Beiwerk? Lieber hier laut scheitern als der
            # Doku eine Zusicherung geben, die niemand geprüft hat.
            sys.exit(
                f"FEHLER: Job {JOB!r} in {CI.relative_to(ROOT)} enthält ein mehrzeiliges "
                f"`run:`. Gate-Schritte einzeilig halten, sonst kann dieser Check sie "
                f"nicht gegen die Doku halten."
            )
        if value.startswith(SETUP_PREFIXES):
            continue
        gates.append(value)
    if not gates:
        sys.exit(f"FEHLER: In Job {JOB!r} steht kein einziger Gate-Befehl. Parser kaputt?")
    return gates


def doc_gates(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        sys.exit(
            f"FEHLER: {path.relative_to(ROOT)} braucht genau ein Markerpaar "
            f"{START} … {END} um den Block mit den Gate-Befehlen."
        )
    region = text.split(START, 1)[1].split(END, 1)[0]
    commands = []
    for raw in region.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        commands.append(line)
    return commands


def main() -> int:
    expected = ci_gates()
    wanted = {normalise(c) for c in expected}

    problems: list[str] = []
    for name in DOCS:
        path = ROOT / name
        if not path.exists():
            problems.append(f"{name}: Datei fehlt.")
            continue
        found = {normalise(c) for c in doc_gates(path)}
        for missing in sorted(wanted - found):
            problems.append(f"{name}: nennt das Gate nicht — {missing}")
        for extra in sorted(found - wanted):
            problems.append(f"{name}: nennt einen Befehl, den die CI nicht fährt — {extra}")

    if problems:
        print(
            f"DRIFT: Die dokumentierten Gates weichen von {CI.relative_to(ROOT)} ab.",
            file=sys.stderr,
        )
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Die CI fährt im Job {JOB!r}:", file=sys.stderr)
        for command in expected:
            print(f"  {command}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Verglichen wird ohne führende Env-Zuweisungen und ohne `-v`; alles andere zählt.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Gate-Doku OK ({len(expected)} Gates aus {CI.relative_to(ROOT)}; "
        f"geprüft: {', '.join(DOCS)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
