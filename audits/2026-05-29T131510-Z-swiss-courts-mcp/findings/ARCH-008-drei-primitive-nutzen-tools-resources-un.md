## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Sec 2 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Server nutzt ausschliesslich das Tools-Primitiv (7 @mcp.tool)

### Expected Behavior

Mindestens zwei Primitive (z.B. list_courts/Statistik als Resources) ODER README-Begründung, warum nur Tools.

### Evidence / Gaps

- Keine Resources und keine Prompts implementiert
- Keine Begründung im README, warum nur Tools verwendet werden
- Read-only Tools (list_courts, get_decision_statistics) sind Resource-Migrations-Kandidaten

### Risk Description

Rein Tools-basiert; read-only Lookups, die sich als Resources eigneten, sind nicht als solche exponiert. Kein funktionaler Schaden, aber suboptimale Primitive-Nutzung.

### Remediation

Mindestens zwei Primitive (z.B. list_courts/Statistik als Resources) ODER README-Begründung, warum nur Tools.

### Effort Estimate

M
