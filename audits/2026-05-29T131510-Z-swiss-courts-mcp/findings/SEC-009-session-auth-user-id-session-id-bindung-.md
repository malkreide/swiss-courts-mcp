## Finding: SEC-009 — Session-Auth & user_id<->session_id-Bindung (HTTP)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 4 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Session-Handling im HTTP-Modus erfolgt durch das FastMCP-Framework (sichere Session-IDs)

### Expected Behavior

Im HTTP-Modus validierte Auth (OAuth/Token), User-ID aus sub-Claim, kryptografisch an die Session gebundene IDs (secrets.token_urlsafe), TTL + serverseitige Invalidierung. Alternativ HTTP-Modus deaktivieren bzw. auf vertrauenswürdiges Netz beschränken.

### Evidence / Gaps

- Keine Authentifizierung im HTTP-Modus (auth_model: none) — keine User-ID aus validiertem Token, daher keine kryptografische user_id<->session_id-Bindung
- Kombiniert mit dem 0.0.0.0-Default (SEC-016) ist der HTTP-Modus ohne jegliche Zugriffskontrolle exponiert
- Vor jedem Multi-User-/Cloud-Deployment ist Auth + Session-Bindung erforderlich; für rein lokalen stdio-Betrieb nicht relevant

### Risk Description

Der streamable-http-Transport ist ohne jede Authentifizierung erreichbar. Es gibt keine User-Identität und keine kryptografische Bindung von Session-IDs an einen Nutzer. Bei einem Cloud-/Multi-User-Deployment kann jeder Anfragen stellen; Session-Fixation/Hijacking ist nicht abgesichert.

### Remediation

Im HTTP-Modus validierte Auth (OAuth/Token), User-ID aus sub-Claim, kryptografisch an die Session gebundene IDs (secrets.token_urlsafe), TTL + serverseitige Invalidierung. Alternativ HTTP-Modus deaktivieren bzw. auf vertrauenswürdiges Netz beschränken.

### Effort Estimate

L
