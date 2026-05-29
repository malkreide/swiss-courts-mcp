## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Transport dual; HTTP-Modus über FastMCP streamable-http verfügbar (server.py:767)

### Expected Behavior

Sticky-Sessions auf LB-Ebene (Mcp-Session-Id) oder Shared-State-Session-Manager (Redis); explizite Session-TTL; Failover-Nachweis.

### Evidence / Gaps

- Keine Sticky-Sessions / kein Shared-State-Session-Manager (Redis/Durable Objects) für horizontale Skalierung
- Keine explizite Session-TTL; kein Failover-Nachweis — vor Multi-Instance-HTTP-Deployment erforderlich

### Risk Description

Bei horizontaler Skalierung des HTTP-Modus ohne Sticky-Sessions/Shared-State brechen Streamable-HTTP-Sessions zwischen Instanzen ab.

### Remediation

Sticky-Sessions auf LB-Ebene (Mcp-Session-Id) oder Shared-State-Session-Manager (Redis); explizite Session-TTL; Failover-Nachweis.

### Effort Estimate

L
