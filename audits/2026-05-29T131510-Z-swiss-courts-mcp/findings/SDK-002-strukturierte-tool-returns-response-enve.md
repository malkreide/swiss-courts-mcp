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

- Pydantic >=2.0 in dependencies (pyproject.toml)
- Input-Modelle sind Pydantic v2 mit Field-Defaults und StrEnum-Literals (server.py:107-248)
- Tools haben explizite Return-Annotation -> str

### Expected Behavior

Konsistenter Response-Envelope (source, provenance, results, count) als Pydantic/TypedDict zusätzlich/optional zum Markdown.

### Evidence / Gaps

- Tool-Returns sind formatierte Markdown-Strings, kein strukturierter Response-Envelope mit source/provenance/results/count
- Keine BaseModel/TypedDict-Returns für maschinelle Weiterverarbeitung

### Risk Description

Markdown-Strings sind für LLM-Anzeige ok, aber nicht maschinell weiterverarbeitbar; kein konsistenter Envelope mit Provenienz/Count erschwert Komposition durch nachgelagerte Agents.

### Remediation

Konsistenter Response-Envelope (source, provenance, results, count) als Pydantic/TypedDict zusätzlich/optional zum Markdown.

### Effort Estimate

M
