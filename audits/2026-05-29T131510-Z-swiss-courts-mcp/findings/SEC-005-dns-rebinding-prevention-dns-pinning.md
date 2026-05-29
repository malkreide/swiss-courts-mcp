## Finding: SEC-005 — DNS-Rebinding-Prevention (DNS-Pinning)

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SEC-005` |
| **PDF-Reference** | Sec 4 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Nur ein fester, vertrauenswürdiger Host (entscheidsuche.ch) wird kontaktiert — DNS-Rebinding-Impact stark begrenzt

### Expected Behavior

Einmalige DNS-Resolution + gepinnte IP für die TCP-Connection, Host-Header/SNI für TLS; Test auf genau 1 DNS-Call.

### Evidence / Gaps

- Kein DNS-Pinning/Custom-Resolver; httpx löst pro Request neu auf (api_client.py:237-253)
- Kein Test, der genau 1 DNS-Call pro Request verifiziert

### Risk Description

DNS-Rebinding ist theoretisch möglich, da pro Request neu aufgelöst wird. Praktisch stark begrenzt, da nur ein fester, vertrauenswürdiger Host kontaktiert wird.

### Remediation

Einmalige DNS-Resolution + gepinnte IP für die TCP-Connection, Host-Header/SNI für TLS; Test auf genau 1 DNS-Call.

### Effort Estimate

M
