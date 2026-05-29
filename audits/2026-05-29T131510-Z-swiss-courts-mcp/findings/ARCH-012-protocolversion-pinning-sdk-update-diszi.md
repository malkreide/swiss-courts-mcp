## Finding: ARCH-012 — protocolVersion-Pinning + SDK-Update-Disziplin

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Sec 2 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- CHANGELOG.md im Keep-a-Changelog-Format vorhanden (CHANGELOG.md:1-6)

### Expected Behavior

protocolVersion explizit pinnen, README-Sektion 'MCP Protocol Version' + Update-Policy, Dependabot/Renovate aktivieren.

### Evidence / Gaps

- Kein protocolVersion-Pinning im Server-Code (grep: keine Fundstelle)
- Keine README-Sektion 'MCP Protocol Version' / Update-Policy
- Kein Dependabot/Renovate für SDK-Update-PRs (.github/ enthält nur Workflows)
- mcp-Dependency nur '>=1.3.0' statt gepinnt (pyproject.toml)

### Risk Description

Ohne protocolVersion-Pinning und Dependabot kann ein SDK-/Spec-Update unbemerkt Breaking Changes einführen.

### Remediation

protocolVersion explizit pinnen, README-Sektion 'MCP Protocol Version' + Update-Policy, Dependabot/Renovate aktivieren.

### Effort Estimate

S
