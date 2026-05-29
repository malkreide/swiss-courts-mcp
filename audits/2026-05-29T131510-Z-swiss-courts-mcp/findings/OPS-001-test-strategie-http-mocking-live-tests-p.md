## Finding: OPS-001 — Test-Strategie: HTTP-Mocking + Live-Tests pro Tool

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Anhang C |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Unit-Tests vorhanden (test_server.py 19, test_api_client.py 36 Test-Funktionen)
- Live-Tests mit @pytest.mark.live markiert (test_api_client.py:286-299)
- live-Marker in pyproject.toml registriert; CI läuft pytest -m 'not live' (.github/workflows/ci.yml)

### Expected Behavior

respx-gemockte Unit-Tests für jeden Tool-Handler (>=5/Tool), >=1 Live-Test/Tool, separater Live-Workflow.

### Evidence / Gaps

- respx ist in dev-deps deklariert, wird aber NICHT verwendet — Tool-Handler mit gemocktem HTTP sind ungetestet
- Nur 2 Live-Tests gesamt statt >=1 pro Tool; kein separater nightly/manueller Live-Workflow
- Tests decken Query-Builder/Formatter ab, aber nicht die async Tool-Handler-Pfade

### Risk Description

Die async Tool-Handler-Pfade (HTTP-Aufruf, Parsing, Formatierung) sind nicht durch gemockte Tests abgedeckt. Regressionen in der Kernfunktionalität würden in CI nicht auffallen; respx ist deklariert, aber ungenutzt.

### Remediation

respx-gemockte Unit-Tests für jeden Tool-Handler (>=5/Tool), >=1 Live-Test/Tool, separater Live-Workflow.

### Effort Estimate

M
