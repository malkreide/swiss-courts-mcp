## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OBS-001` |
| **PDF-Reference** | Sec 6 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Tool-Handler fangen Exceptions ab und mappen sie auf handlungsweisende Meldungen (server.py:354, api_client.handle_error api_client.py:338-356)
- Error-Pfad teilweise getestet (handle_error-Tests test_api_client.py:271-277)

### Expected Behavior

Anwendungsfehler als Tool-Result mit isError:true; Protocol-Fehler über standardisierte JSON-RPC-Codes; Tests für beide Pfade.

### Evidence / Gaps

- Anwendungsfehler werden als normaler Text-Result zurückgegeben, NICHT mit isError:true markiert
- Keine standardisierten Protocol-Level-Fehlercodes; kein Test, der den isError-Pfad abdeckt

### Risk Description

Anwendungsfehler werden als normaler Text-Result zurückgegeben statt mit isError:true. Der Client kann Erfolg nicht von Fehler unterscheiden; LLMs interpretieren Fehlertext ggf. als gültiges Ergebnis.

### Remediation

Anwendungsfehler als Tool-Result mit isError:true; Protocol-Fehler über standardisierte JSON-RPC-Codes; Tests für beide Pfade.

### Effort Estimate

M
