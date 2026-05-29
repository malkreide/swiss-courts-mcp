## Finding: SDK-003 — Context Injection für Progress/Logging

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SDK-003` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Tools sind async (server.py:322 ff.)

### Expected Behavior

ctx: Context-Parameter, ctx.report_progress() bei langlaufenden Suchen, ctx.warning/ctx.error für nicht-fatale Fehler.

### Evidence / Gaps

- Such-Tools machen Netzwerk-Calls mit bis zu 30s Timeout (api_client.py:27), aber kein ctx: Context-Parameter
- Kein ctx.report_progress() für potentiell langlaufende Suchen
- Fehler werden nicht über ctx.warning()/ctx.error() geloggt

### Risk Description

Langlaufende Suchen (bis 30s Timeout) geben keinen Progress; der Client kann nicht zwischen 'hängt' und 'arbeitet' unterscheiden.

### Remediation

ctx: Context-Parameter, ctx.report_progress() bei langlaufenden Suchen, ctx.warning/ctx.error für nicht-fatale Fehler.

### Effort Estimate

M
