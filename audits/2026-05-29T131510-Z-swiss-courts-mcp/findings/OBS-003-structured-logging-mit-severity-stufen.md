## Finding: OBS-003 — Structured Logging mit Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | fail |

### Observed Behavior

- (keine — Pass-Criteria nicht erfüllt)

### Expected Behavior

structlog/loguru als Dependency, JSON-Output auf stderr, >=4 Severity-Stufen, bound context pro Tool-Call.

### Evidence / Gaps

- Kein strukturiertes Logging: grep findet keinerlei logging/structlog/loguru in src/
- Kein structlog/loguru in dependencies
- Keine bound context (tool name, session_id, correlation_id) pro Tool-Call

### Risk Description

Ohne strukturiertes Logging gibt es keinerlei Server-seitige Observability: Fehler, Latenzen und Tool-Nutzung sind nicht nachvollziehbar. Incident-Analyse und SIEM-Anbindung sind unmöglich.

### Remediation

structlog/loguru als Dependency, JSON-Output auf stderr, >=4 Severity-Stufen, bound context pro Tool-Call.

### Effort Estimate

M
