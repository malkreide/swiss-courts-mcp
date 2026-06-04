# Sicherheitsrichtlinie & Sicherheitslage

[:gb: English Version](SECURITY.md)

`swiss-courts-mcp` wurde gegen den internen MCP-Best-Practice-Audit-Katalog gehärtet. Dieses Dokument fasst die Sicherheitslage zusammen und erklärt, wie Schwachstellen gemeldet werden.

## Schwachstelle melden

Bitte eröffnen Sie ein privates Security Advisory im GitHub-Repository oder kontaktieren Sie die in `README.md` genannte verantwortliche Person. Erstellen Sie für ausnutzbare Schwachstellen **keine** öffentlichen Issues.

## Zusammenfassung der Sicherheitslage

Dies ist ein **rein lesender**, **PII-freier** MCP-Server für **öffentliche Open Data**. Alle 7 Tools stellen ausschliesslich lesende Abfragen an das Elasticsearch-Backend von entscheidsuche.ch (`entscheidsuche.ch`); die Daten bestehen aus öffentlichen Gerichtsentscheiden. Bereits umgesetzte Härtungsmassnahmen:

| Bereich | Kontrolle |
|---|---|
| Zugriff | Nur lesend (`readOnlyHint: true`) — der Server kann keine Daten ändern oder löschen |
| Egress | HTTPS-erzwungene Allow-List ausschliesslich für `entscheidsuche.ch` (SEC-021; siehe [Egress-Policy](docs/network-egress.md)) |
| Binding | Netzwerk-Transporte binden standardmässig an `127.0.0.1`; `0.0.0.0` muss bewusst aktiviert werden (SEC-016) |
| HTTP-Auth | Optionale Bearer-Token-Auth (JWT, nur `sub`-Claim-Identität), TTL über Token-`exp`, HS256 (Entwicklung) / RS256+JWKS (Produktion) (SEC-009; siehe [ADR 0001](docs/adr/0001-http-auth.md)) |
| Transport | Stateless Streamable HTTP mit CORS, das nur explizit konfigurierte Origins exponiert (SDK-004) |
| Input | Pydantic-v2-Strict-Validierung (`extra="forbid"`) an allen Grenzen (SEC-018) |
| Secrets | Nur Umgebungsvariablen, `.gitignore` schützt `.env`, Gitleaks auf PRs, keine hartcodierten Secrets (SEC-013; siehe [Secret-Management](docs/secret-management.md)) |
| Fehler | Upstream-Antworten werden nach stderr geloggt, niemals an das Modell weitergegeben (OBS-002) |
| Stdout | Reserviert für den JSON-RPC-Stream; Logging fest auf stderr (OBS-004) |
| Limits | Pro-Abfrage-Limits (max. 50 Ergebnisse pro Suche, 50 Aggregations-Buckets), 30 s Timeout pro API-Aufruf |

Der jüngste Audit-Lauf (`2026-05-29T191910-Z-swiss-courts-mcp`) meldet **produktionsreif**: 36 bestanden · 0 fehlgeschlagen · 0 partiell. Den vollständigen Bericht finden Sie unter `audits/`, die Härtungshistorie in `CHANGELOG.md`.

## Re-Evaluierungs-Auslöser

Die Sicherheitslage sollte neu auditiert werden, falls der Server jemals:

- **Schreib**-Funktionalität erhält oder beginnt, **PII** zu verarbeiten, oder
- eine neue **Datenquelle** hinzufügt oder die Egress-Allow-List lockert, oder
- sein **Authentifizierungs**-Modell ändert, oder
- Tools **dynamisch** / aus entfernten Quellen registriert, oder
- hinter einem gemeinsamen MCP-Gateway aggregiert wird (dann das Tool-Allow-Listing und die Tool-Poisoning-Erkennung des Gateways aktivieren).
