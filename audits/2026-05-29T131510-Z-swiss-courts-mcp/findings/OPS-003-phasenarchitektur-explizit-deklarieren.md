## Finding: OPS-003 — Phasenarchitektur explizit deklarieren

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Tool-Annotations sind durchgehend read-only — konsistent mit einer Phase-1-Architektur (server.py)

### Expected Behavior

Phase im README explizit deklarieren (Phase 1: read-only) + Roadmap-File mit phasenspezifischen Tasks.

### Evidence / Gaps

- Keine explizite Phasen-Deklaration im README (grep: kein 'Phase')
- Kein Roadmap-File mit phasenspezifischen Tasks

### Risk Description

Ohne deklarierte Phase ist unklar, welche Sicherheits-/Prozess-Gates gelten; Phasenübergänge sind nicht nachvollziehbar.

### Remediation

Phase im README explizit deklarieren (Phase 1: read-only) + Roadmap-File mit phasenspezifischen Tasks.

### Effort Estimate

S
