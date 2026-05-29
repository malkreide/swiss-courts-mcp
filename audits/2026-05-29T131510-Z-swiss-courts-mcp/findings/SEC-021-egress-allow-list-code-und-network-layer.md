## Finding: SEC-021 — Egress-Allow-List (Code- und Network-Layer)

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Sec 4 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Ziel-Hosts faktisch über Modul-Konstanten gepinnt (SEARCH_URL/DOCS_BASE/FACETS_URL, api_client.py:23-25)

### Expected Behavior

frozenset-Allow-List + assert_host_allowed-Pre-Request-Check; docs/network-egress.md; Network-Layer-Egress-Control im Deployment.

### Evidence / Gaps

- Keine frozenset-Egress-Allow-List und kein assert_host_allowed-Pre-Request-Check
- Keine docs/network-egress.md; keine Network-Layer-Egress-Control dokumentiert

### Risk Description

Es gibt keinen erzwungenen Egress-Allow-List-Check. Bei künftiger Einführung dynamischer URLs (oder einer kompromittierten Dependency) gäbe es keine Code-Layer-Schranke gegen ungewollte Ziele.

### Remediation

frozenset-Allow-List + assert_host_allowed-Pre-Request-Check; docs/network-egress.md; Network-Layer-Egress-Control im Deployment.

### Effort Estimate

M
