## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SDK-004` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | fail |

### Observed Behavior

- (keine — Pass-Criteria nicht erfüllt)

### Expected Behavior

CORSMiddleware mit expose_headers=['Mcp-Session-Id'], allow_headers inkl. Mcp-Session-Id, explizite allow_origins (keine Wildcard in Prod).

### Evidence / Gaps

- Transport ist dual (HTTP aktivierbar), aber keine CORS-Middleware konfiguriert (grep: keine CORSMiddleware/expose_headers)
- Mcp-Session-Id wird nicht via expose_headers/allow_headers freigegeben — Browser-Clients können Session nicht lesen
- allow_origins nicht explizit gesetzt

### Risk Description

Wird der HTTP-Transport genutzt, fehlt jegliche CORS-Konfiguration. Browser-basierte MCP-Clients können den Mcp-Session-Id-Header nicht lesen und damit keine Folge-Requests korrelieren; der HTTP-Modus ist für Web-Clients praktisch unbrauchbar.

### Remediation

CORSMiddleware mit expose_headers=['Mcp-Session-Id'], allow_headers inkl. Mcp-Session-Id, explizite allow_origins (keine Wildcard in Prod).

### Effort Estimate

S
