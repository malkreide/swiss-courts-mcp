## Finding: OBS-002 — Mask Error Details: keine internen Exception-Repr ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- handle_error liefert überwiegend generische, benutzerfreundliche Meldungen (HTTP 400/429/503, Timeout, ConnectError — api_client.py:340-355)
- Keine traceback.format_exc()-Ausgaben in Tool-Returns

### Expected Behavior

FastMCP(mask_error_details=True); generischer Fallback ohne Exception-Repr; Originalfehler nur ins Server-Log.

### Evidence / Gaps

- FastMCP ohne mask_error_details=True (server.py:89)
- Fallback leakt interne Exception-Details an den Client: f'Fehler: {type(e).__name__}: {e}' (api_client.py:356)

### Risk Description

Der Fallback in handle_error gibt type(e).__name__ und die Exception-Message direkt an den Client/das LLM zurück. Unerwartete Fehler können so interne Details (Bibliotheks-Interna, Pfade, Payload-Fragmente) leaken.

### Remediation

FastMCP(mask_error_details=True); generischer Fallback ohne Exception-Repr; Originalfehler nur ins Server-Log.

### Effort Estimate

S
