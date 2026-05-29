## Finding: SEC-016 — 0.0.0.0-Binding-Prevention (NeighborJack)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SEC-016` |
| **PDF-Reference** | Anhang B |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | fail |

### Observed Behavior

- (keine — Pass-Criteria nicht erfüllt)

### Expected Behavior

Default-Host 127.0.0.1; 0.0.0.0 nur via expliziter ENV-Var/Container-Setting; Warnung beim Binden auf 0.0.0.0 ohne Container-Detection.

### Evidence / Gaps

- 0.0.0.0 ist als Default hartkodiert: mcp.run(transport='streamable-http', host='0.0.0.0', port=port) (server.py:767)
- Kein 127.0.0.1-Default, keine Host-ENV-Var, keine Container-Detection, keine Warnung beim Binden auf 0.0.0.0
- NeighborJack-Risiko: jeder im selben Netzwerk erreicht den Server

### Risk Description

Im HTTP-Modus bindet der Server per Default an alle Interfaces (0.0.0.0). Jeder Host im selben Netzwerk/Subnetz (Café-WLAN, Container-Netz, Cloud-VPC) kann den MCP-Server ungehindert ansprechen und sämtliche Such-Tools nutzen — klassischer NeighborJack. In Kombination mit fehlender Auth (SEC-009) ist der Dienst vollständig offen.

### Remediation

Default-Host 127.0.0.1; 0.0.0.0 nur via expliziter ENV-Var/Container-Setting; Warnung beim Binden auf 0.0.0.0 ohne Container-Detection.

### Effort Estimate

S
