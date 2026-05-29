## Finding: SDK-001 — FastMCP Lifespan + Connection-Reuse

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SDK-001` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | fail |

### Observed Behavior

- (keine — Pass-Criteria nicht erfüllt)

### Expected Behavior

Ein einziger, über @asynccontextmanager-Lifespan verwalteter httpx.AsyncClient, der allen Tool-Calls bereitgestellt wird; Cleanup im finally.

### Evidence / Gaps

- Kein Lifespan: FastMCP(...) ohne lifespan= (server.py:89-99)
- httpx.AsyncClient wird PRO Tool-Call neu erzeugt (api_client._get_client, aufgerufen in search_decisions/get_court_taxonomy — api_client.py:237-269)
- Kein @asynccontextmanager / AsyncExitStack; keine Connection-Wiederverwendung

### Risk Description

Pro Tool-Call wird ein neuer httpx.AsyncClient aufgebaut und sofort wieder verworfen. Das verhindert Connection-Pooling/Keep-Alive, erhöht Latenz und TLS-Handshake-Overhead und kann unter Last zu Socket-Exhaustion führen.

### Remediation

Ein einziger, über @asynccontextmanager-Lifespan verwalteter httpx.AsyncClient, der allen Tool-Calls bereitgestellt wird; Cleanup im finally.

### Effort Estimate

S
