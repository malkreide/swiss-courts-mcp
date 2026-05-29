## Finding: SDK-002 — Strukturierte Tool-Returns (Response-Envelope)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SDK-002` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Pydantic v2; `SearchResponse`-Envelope (`models.py`) mit `source`, `license`,
  `match_type`, `count`, `total`, `results` wird intern gebaut.
- `count`/`total`/`source`/`license`/`match_type` sind im Markdown-Output sichtbar.
- Literal-Types/Enums für enumerable Werte vorhanden.

### Expected Behavior

Konsistenter Response-Envelope zusätzlich als maschinenlesbarer
`structuredContent` (nicht nur Markdown), damit nachgelagerte Agents die
Resultate ohne Parsing weiterverarbeiten können.

### Risk Description

Kein Sicherheitsrisiko. Markdown-Returns sind für die LLM-Anzeige optimal,
erschweren aber die programmatische Komposition durch andere Agents.

### Remediation

Tools optional `SearchResponse` als strukturierten Return (FastMCP
`structuredContent`) ausliefern, parallel zum Markdown-Text. Eingeplant für
Phase 1 (siehe ROADMAP.md).

### Effort Estimate

M
