## Finding: CH-004 — OGD-CH Lizenz-Compliance: Attribution

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `CH-004` |
| **PDF-Reference** | Custom CH |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Jede Tool-Antwort enthält Quellen-Footer 'Quelle: entscheidsuche.ch' (SOURCE_FOOTER, server.py:33)
- README dokumentiert Datenquelle und Lizenz (BGG Art. 27, public domain — README.md:173)

### Expected Behavior

Lizenz im maschinenlesbaren source-Feld jeder Antwort; Provenienz pro Datensatz (nicht nur globaler Footer).

### Evidence / Gaps

- Lizenz fehlt im maschinenlesbaren source-Feld der Antwort (nur im Fliesstext-Footer)
- Keine Provenienz pro Datensatz (nur globaler Footer)

### Risk Description

Lizenz-/Provenienz-Information ist nur als Prosa-Footer vorhanden, nicht maschinenlesbar pro Datensatz — erschwert lizenzkonforme Weiterverwendung.

### Remediation

Lizenz im maschinenlesbaren source-Feld jeder Antwort; Provenienz pro Datensatz (nicht nur globaler Footer).

### Effort Estimate

S
