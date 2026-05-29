# MCP-Server Audit-Report — `swiss-courts-mcp`

**Audit-Datum:** 2026-05-29
**Skill-Version:** v1.0.0
**Catalog-Version:** 2026-05 (catalog_hash 091f446b…)

---

## 1. Executive Summary

Server `swiss-courts-mcp` wurde gegen 36 anwendbare Best-Practice-Checks geprüft. 16 bestanden, 20 Findings dokumentiert (2 critical, 10 high, 8 medium, 0 low). Production-Readiness: NICHT erreicht — blockierend: SDK-001, SDK-004, SEC-016.

**Production-Readiness:** NO

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `swiss-courts-mcp` |
| Audit-Datum | 2026-05-29 |
| Skill-Version | v1.0.0 |
| Catalog-Version | 2026-05 (catalog_hash 091f446b…) |
| transport | `dual` |
| auth_model | `none` |
| data_class | `Public Open Data` |
| write_capable | `False` |
| deployment | `['local-stdio']` |
| uses_sampling | `False` |
| tools_make_external_requests | `True` |
| stadt_zuerich_context | `False` |
| schulamt_context | `False` |
| data_source.is_swiss_open_data | `True` |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 7 | 0 | 4 | 0 | 0 |
| CH | 0 | 0 | 1 | 0 | 0 |
| OBS | 1 | 1 | 2 | 0 | 0 |
| OPS | 1 | 0 | 2 | 0 | 0 |
| SCALE | 0 | 0 | 1 | 0 | 0 |
| SDK | 0 | 2 | 2 | 0 | 0 |
| SEC | 7 | 1 | 4 | 0 | 0 |
| **Total** | **16** | **4** | **16** | **0** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| SEC-009 | SEC | critical | partial |
| SEC-016 | SEC | critical | fail |
| OBS-001 | OBS | high | partial |
| OBS-002 | OBS | high | partial |
| OPS-001 | OPS | high | partial |
| OPS-003 | OPS | high | partial |
| SCALE-002 | SCALE | high | partial |
| SDK-001 | SDK | high | fail |
| SDK-004 | SDK | high | fail |
| SEC-005 | SEC | high | partial |
| SEC-007 | SEC | high | partial |
| SEC-021 | SEC | high | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-008 | ARCH | medium | partial |
| ARCH-011 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |
| CH-004 | CH | medium | partial |
| OBS-003 | OBS | medium | fail |
| SDK-002 | SDK | medium | partial |
| SDK-003 | SDK | medium | partial |

**Gesamt:** 20 Findings

---

## 5. Detail-Findings

### ARCH-003

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


### ARCH-008

## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Sec 2 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Server nutzt ausschliesslich das Tools-Primitiv (7 @mcp.tool)

### Expected Behavior

Mindestens zwei Primitive (z.B. list_courts/Statistik als Resources) ODER README-Begründung, warum nur Tools.

### Evidence / Gaps

- Keine Resources und keine Prompts implementiert
- Keine Begründung im README, warum nur Tools verwendet werden
- Read-only Tools (list_courts, get_decision_statistics) sind Resource-Migrations-Kandidaten

### Risk Description

Rein Tools-basiert; read-only Lookups, die sich als Resources eigneten, sind nicht als solche exponiert. Kein funktionaler Schaden, aber suboptimale Primitive-Nutzung.

### Remediation

Mindestens zwei Primitive (z.B. list_courts/Statistik als Resources) ODER README-Begründung, warum nur Tools.

### Effort Estimate

M


### ARCH-011

## Finding: ARCH-011 — Standardisierte Repo-Struktur (tools/-Split bei >5 Tools)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `ARCH-011` |
| **PDF-Reference** | Anhang A |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Pflicht-Files vorhanden: README.md, README.de.md, CHANGELOG.md, LICENSE, pyproject.toml
- src-Layout korrekt (src/swiss_courts_mcp/), tests/, .github/workflows/ vorhanden
- CI: ci.yml (test) + publish.yml vorhanden
- README.de.md parallel zu README.md (gleiche Top-Level-Sektionen)

### Expected Behavior

Bei >5 Tools tools/-Verzeichnis mit Gruppen-Files ODER dokumentierte Begründung der Single-File-Abweichung im README.

### Evidence / Gaps

- 7 Tools (>5) liegen alle in server.py; kein tools/-Verzeichnis mit File-pro-Gruppe und keine README-Begründung der Abweichung

### Risk Description

7 Tools in einer einzigen server.py erschweren Wartung/Review mit wachsender Tool-Zahl. Kein akutes Risiko.

### Remediation

Bei >5 Tools tools/-Verzeichnis mit Gruppen-Files ODER dokumentierte Begründung der Single-File-Abweichung im README.

### Effort Estimate

S


### ARCH-012

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


### CH-004

## Finding: CH-004 — OGD-CH Lizenz-Compliance: Attribution

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `CH-004` |
| **PDF-Reference** | Custom CH |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Jede Tool-Antwort enthält Quellen-Footer 'Quelle: entscheidsuche.ch' (SOURCE_FOOTER, server.py:33)
- README dokumentiert Datenquelle und Lizenz (BGG Art. 27, public domain — README.md:173)

### Expected Behavior

Lizenz im maschinenlesbaren source-Feld jeder Antwort; Provenienz pro Datensatz (nicht nur globaler Footer).

### Evidence / Gaps

- Lizenz fehlt im maschinenlesbaren source-Feld der Antwort (nur im Fliesstext-Footer)
- Keine Provenienz pro Datensatz (nur globaler Footer)

### Risk Description

Lizenz-/Provenienz-Information ist nur als Prosa-Footer vorhanden, nicht maschinenlesbar pro Datensatz — erschwert lizenzkonforme Weiterverwendung.

### Remediation

Lizenz im maschinenlesbaren source-Feld jeder Antwort; Provenienz pro Datensatz (nicht nur globaler Footer).

### Effort Estimate

S


### OBS-001

## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OBS-001` |
| **PDF-Reference** | Sec 6 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Tool-Handler fangen Exceptions ab und mappen sie auf handlungsweisende Meldungen (server.py:354, api_client.handle_error api_client.py:338-356)
- Error-Pfad teilweise getestet (handle_error-Tests test_api_client.py:271-277)

### Expected Behavior

Anwendungsfehler als Tool-Result mit isError:true; Protocol-Fehler über standardisierte JSON-RPC-Codes; Tests für beide Pfade.

### Evidence / Gaps

- Anwendungsfehler werden als normaler Text-Result zurückgegeben, NICHT mit isError:true markiert
- Keine standardisierten Protocol-Level-Fehlercodes; kein Test, der den isError-Pfad abdeckt

### Risk Description

Anwendungsfehler werden als normaler Text-Result zurückgegeben statt mit isError:true. Der Client kann Erfolg nicht von Fehler unterscheiden; LLMs interpretieren Fehlertext ggf. als gültiges Ergebnis.

### Remediation

Anwendungsfehler als Tool-Result mit isError:true; Protocol-Fehler über standardisierte JSON-RPC-Codes; Tests für beide Pfade.

### Effort Estimate

M


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine internen Exception-Repr ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- handle_error liefert überwiegend generische, benutzerfreundliche Meldungen (HTTP 400/429/503, Timeout, ConnectError — api_client.py:340-355)
- Keine traceback.format_exc()-Ausgaben in Tool-Returns

### Expected Behavior

FastMCP(mask_error_details=True); generischer Fallback ohne Exception-Repr; Originalfehler nur ins Server-Log.

### Evidence / Gaps

- FastMCP ohne mask_error_details=True (server.py:89)
- Fallback leakt interne Exception-Details an den Client: f'Fehler: {type(e).__name__}: {e}' (api_client.py:356)

### Risk Description

Der Fallback in handle_error gibt type(e).__name__ und die Exception-Message direkt an den Client/das LLM zurück. Unerwartete Fehler können so interne Details (Bibliotheks-Interna, Pfade, Payload-Fragmente) leaken.

### Remediation

FastMCP(mask_error_details=True); generischer Fallback ohne Exception-Repr; Originalfehler nur ins Server-Log.

### Effort Estimate

S


### OBS-003

## Finding: OBS-003 — Structured Logging mit Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | fail |

### Observed Behavior

- (keine — Pass-Criteria nicht erfüllt)

### Expected Behavior

structlog/loguru als Dependency, JSON-Output auf stderr, >=4 Severity-Stufen, bound context pro Tool-Call.

### Evidence / Gaps

- Kein strukturiertes Logging: grep findet keinerlei logging/structlog/loguru in src/
- Kein structlog/loguru in dependencies
- Keine bound context (tool name, session_id, correlation_id) pro Tool-Call

### Risk Description

Ohne strukturiertes Logging gibt es keinerlei Server-seitige Observability: Fehler, Latenzen und Tool-Nutzung sind nicht nachvollziehbar. Incident-Analyse und SIEM-Anbindung sind unmöglich.

### Remediation

structlog/loguru als Dependency, JSON-Output auf stderr, >=4 Severity-Stufen, bound context pro Tool-Call.

### Effort Estimate

M


### OPS-001

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


### OPS-003

## Finding: OPS-003 — Phasenarchitektur explizit deklarieren

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Tool-Annotations sind durchgehend read-only — konsistent mit einer Phase-1-Architektur (server.py)

### Expected Behavior

Phase im README explizit deklarieren (Phase 1: read-only) + Roadmap-File mit phasenspezifischen Tasks.

### Evidence / Gaps

- Keine explizite Phasen-Deklaration im README (grep: kein 'Phase')
- Kein Roadmap-File mit phasenspezifischen Tasks

### Risk Description

Ohne deklarierte Phase ist unklar, welche Sicherheits-/Prozess-Gates gelten; Phasenübergänge sind nicht nachvollziehbar.

### Remediation

Phase im README explizit deklarieren (Phase 1: read-only) + Roadmap-File mit phasenspezifischen Tasks.

### Effort Estimate

S


### SCALE-002

## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Transport dual; HTTP-Modus über FastMCP streamable-http verfügbar (server.py:767)

### Expected Behavior

Sticky-Sessions auf LB-Ebene (Mcp-Session-Id) oder Shared-State-Session-Manager (Redis); explizite Session-TTL; Failover-Nachweis.

### Evidence / Gaps

- Keine Sticky-Sessions / kein Shared-State-Session-Manager (Redis/Durable Objects) für horizontale Skalierung
- Keine explizite Session-TTL; kein Failover-Nachweis — vor Multi-Instance-HTTP-Deployment erforderlich

### Risk Description

Bei horizontaler Skalierung des HTTP-Modus ohne Sticky-Sessions/Shared-State brechen Streamable-HTTP-Sessions zwischen Instanzen ab.

### Remediation

Sticky-Sessions auf LB-Ebene (Mcp-Session-Id) oder Shared-State-Session-Manager (Redis); explizite Session-TTL; Failover-Nachweis.

### Effort Estimate

L


### SDK-001

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


### SDK-002

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


### SDK-003

## Finding: SDK-003 — Context Injection für Progress/Logging

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SDK-003` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Tools sind async (server.py:322 ff.)

### Expected Behavior

ctx: Context-Parameter, ctx.report_progress() bei langlaufenden Suchen, ctx.warning/ctx.error für nicht-fatale Fehler.

### Evidence / Gaps

- Such-Tools machen Netzwerk-Calls mit bis zu 30s Timeout (api_client.py:27), aber kein ctx: Context-Parameter
- Kein ctx.report_progress() für potentiell langlaufende Suchen
- Fehler werden nicht über ctx.warning()/ctx.error() geloggt

### Risk Description

Langlaufende Suchen (bis 30s Timeout) geben keinen Progress; der Client kann nicht zwischen 'hängt' und 'arbeitet' unterscheiden.

### Remediation

ctx: Context-Parameter, ctx.report_progress() bei langlaufenden Suchen, ctx.warning/ctx.error für nicht-fatale Fehler.

### Effort Estimate

M


### SDK-004

## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SDK-004` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | fail |

### Observed Behavior

- (keine — Pass-Criteria nicht erfüllt)

### Expected Behavior

CORSMiddleware mit expose_headers=['Mcp-Session-Id'], allow_headers inkl. Mcp-Session-Id, explizite allow_origins (keine Wildcard in Prod).

### Evidence / Gaps

- Transport ist dual (HTTP aktivierbar), aber keine CORS-Middleware konfiguriert (grep: keine CORSMiddleware/expose_headers)
- Mcp-Session-Id wird nicht via expose_headers/allow_headers freigegeben — Browser-Clients können Session nicht lesen
- allow_origins nicht explizit gesetzt

### Risk Description

Wird der HTTP-Transport genutzt, fehlt jegliche CORS-Konfiguration. Browser-basierte MCP-Clients können den Mcp-Session-Id-Header nicht lesen und damit keine Folge-Requests korrelieren; der HTTP-Modus ist für Web-Clients praktisch unbrauchbar.

### Remediation

CORSMiddleware mit expose_headers=['Mcp-Session-Id'], allow_headers inkl. Mcp-Session-Id, explizite allow_origins (keine Wildcard in Prod).

### Effort Estimate

S


### SEC-005

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


### SEC-007

## Finding: SEC-007 — Container-Sandboxing für HTTP-/Cloud-Modus

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-courts-mcp` |
| **Check-Reference** | `SEC-007` |
| **PDF-Reference** | Sec 4 |
| **Audit-Datum** | 2026-05-29 |
| **Auditor** | mcp-audit Skill (Claude) |
| **Check-Status** | partial |

### Observed Behavior

- Reiner stdio/Python-Server ohne externe Prozess-/Datei-Privilegien

### Expected Behavior

Dockerfile mit non-root USER (>=10000), readOnlyRootFilesystem, cap drop ALL, seccomp RuntimeDefault — sofern HTTP/Cloud deployt wird.

### Evidence / Gaps

- Kein Dockerfile/Container-Hardening vorhanden, obwohl HTTP-/Cloud-Modus existiert (kein non-root USER, kein readOnlyRootFilesystem, keine cap drop)
- Vor einem Cloud-Deployment des HTTP-Modus muss Sandboxing nachgezogen werden

### Risk Description

Ohne Container-Hardening würde ein Cloud-Deployment des HTTP-Modus als root mit vollem Filesystem-Zugriff laufen — unnötige Angriffsfläche bei Kompromittierung.

### Remediation

Dockerfile mit non-root USER (>=10000), readOnlyRootFilesystem, cap drop ALL, seccomp RuntimeDefault — sofern HTTP/Cloud deployt wird.

### Effort Estimate

M


### SEC-009

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


### SEC-016

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


### SEC-021

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


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SEC-009** (critical, partial)
2. **SEC-016** (critical, fail)
3. **OBS-001** (high, partial)
4. **OBS-002** (high, partial)
5. **OPS-001** (high, partial)
6. **OPS-003** (high, partial)
7. **SCALE-002** (high, partial)
8. **SDK-001** (high, fail)
9. **SDK-004** (high, fail)
10. **SEC-005** (high, partial)
11. **SEC-007** (high, partial)
12. **SEC-021** (high, partial)
13. **ARCH-003** (medium, partial)
14. **ARCH-008** (medium, partial)
15. **ARCH-011** (medium, partial)
16. **ARCH-012** (medium, partial)
17. **CH-004** (medium, partial)
18. **OBS-003** (medium, fail)
19. **SDK-002** (medium, partial)
20. **SDK-003** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| skill_version | `v1.0.0` |
| catalog_version | `2026-05 (catalog_hash 091f446b…)` |
| applies_when_dsl_version | `1.0` |
| policy | `fail-or-partial` |
| audit_date | `2026-05-29` |


_Generated by tools/build_report.py — do not edit by hand._
