## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Leere Suchergebnisse liefern actionable Hinweise statt nur 'nicht gefunden' (server.py:341, 487-493)

### Expected Behavior

Antwort-Feld match_type (exact/fuzzy/none); bei none ein actionable Hinweis bzw. Fuzzy-/Suggestion-Fallback.

### Evidence / Gaps

- Kein match_type-Feld (exact/fuzzy/none) in der Antwort
- Kein Fuzzy-Match/Suggestion-Mechanismus bei 0 Treffern

### Risk Description

Bei 0 Treffern erhält das LLM keine maschinenlesbare Information über die Match-Qualität (kein match_type), nur Prosa-Tipps. Erschwert automatisches Reagieren (Reformulieren, Fallback-Tool).

### Remediation

Antwort-Feld match_type (exact/fuzzy/none); bei none ein actionable Hinweis bzw. Fuzzy-/Suggestion-Fallback.

### Effort Estimate

M
