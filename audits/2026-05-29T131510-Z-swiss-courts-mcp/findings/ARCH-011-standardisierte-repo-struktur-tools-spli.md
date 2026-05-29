## Finding: ARCH-011 — Standardisierte Repo-Struktur (tools/-Split bei >5 Tools)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `ARCH-011` |
| **PDF-Reference** | Anhang A |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Pflicht-Files vorhanden: README.md, README.de.md, CHANGELOG.md, LICENSE, pyproject.toml
- src-Layout korrekt (src/swiss_courts_mcp/), tests/, .github/workflows/ vorhanden
- CI: ci.yml (test) + publish.yml vorhanden
- README.de.md parallel zu README.md (gleiche Top-Level-Sektionen)

### Expected Behavior

Bei >5 Tools tools/-Verzeichnis mit Gruppen-Files ODER dokumentierte Begründung der Single-File-Abweichung im README.

### Evidence / Gaps

- 7 Tools (>5) liegen alle in server.py; kein tools/-Verzeichnis mit File-pro-Gruppe und keine README-Begründung der Abweichung

### Risk Description

7 Tools in einer einzigen server.py erschweren Wartung/Review mit wachsender Tool-Zahl. Kein akutes Risiko.

### Remediation

Bei >5 Tools tools/-Verzeichnis mit Gruppen-Files ODER dokumentierte Begründung der Single-File-Abweichung im README.

### Effort Estimate

S
