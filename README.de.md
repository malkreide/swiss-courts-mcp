[English Version](README.md)

> **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# swiss-courts-mcp

![Version](https://img.shields.io/badge/version-0.1.0-blue)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Kein API-Key](https://img.shields.io/badge/Auth-keiner%20erforderlich-brightgreen)](https://github.com/malkreide/swiss-courts-mcp)
![CI](https://github.com/malkreide/swiss-courts-mcp/actions/workflows/ci.yml/badge.svg)

> MCP-Server für Schweizer Gerichtsentscheide — Bundesgericht (BGer), Bundesverwaltungsgericht (BVGer), Bundesstrafgericht (BStGer) und alle 26 kantonalen Gerichte via entscheidsuche.ch

<p align="center">
  <img src="assets/demo.svg" alt="Demo: Claude durchsucht Schweizer Gerichtsentscheide via MCP Tool Call" width="720">
</p>

---

## Übersicht

Zugriff auf Schweizer Gerichtsentscheide aller Instanzen über eine einzige MCP-Schnittstelle. Kombiniert Volltextsuche mit strukturierten Filtern nach Kanton, Gerichtsebene, Datumsbereich und Gesetzesreferenzen.

| Quelle | Abdeckung | Daten |
|--------|-----------|-------|
| [entscheidsuche.ch](https://entscheidsuche.ch) | Bund + 26 Kantone | Gerichtsentscheide seit ca. 2000 |

**Synergie mit [fedlex-mcp](https://github.com/malkreide/fedlex-mcp):** Gesetzestext (SR) + Rechtsprechung = vollständige Rechtsrecherche.

---

## Features

- Volltextsuche über alle Schweizer Gerichtsentscheide
- Mehrstufige Gesetzesartikel-Suche mit Regex-Parser und Elasticsearch Boost-Scoring
- Dedizierte Bundesgerichts-Suche mit Abteilungsfilter
- Kantons- und Gerichtsebenen-Filter
- Feed der neuesten Entscheide
- Gerichts-Taxonomie-Auflistung
- Entscheid-Statistiken mit Aggregationen
- Dreisprachig (Deutsch, Französisch, Italienisch)
- Kein API-Key erforderlich

---

## Voraussetzungen

- Python 3.11 oder höher
- Ein MCP-kompatibler Client (Claude Desktop, Cursor, Windsurf, etc.)

---

## Installation

```bash
pip install swiss-courts-mcp
```

Oder aus dem Quellcode:

```bash
git clone https://github.com/malkreide/swiss-courts-mcp.git
cd swiss-courts-mcp
pip install -e ".[dev]"
```

---

## Schnellstart

```bash
# Direkt starten
swiss-courts-mcp

# Oder als Python-Modul
python -m swiss_courts_mcp
```

---

## Konfiguration

### Claude Desktop

In `claude_desktop_config.json` eintragen:

```json
{
  "mcpServers": {
    "swiss-courts": {
      "command": "python",
      "args": ["-m", "swiss_courts_mcp"]
    }
  }
}
```

### Cloud-Deployment (HTTP-Transport)

Der HTTP-Transport ist **standardmässig aus**. Der Default-Bind-Host ist
`127.0.0.1` (nur lokal) — `0.0.0.0` muss bewusst aktiviert werden (das
Dockerfile tut dies). HTTP ohne Authentifizierung loggt eine Warnung; nur hinter
einem authentifizierenden Reverse-Proxy betreiben.

```bash
# Lokales HTTP (Loopback), ohne Auth — nur Entwicklung
swiss-courts-mcp --http --port 8000

# Container (bindet 0.0.0.0, Auth aktiv) — siehe Dockerfile
docker build -t swiss-courts-mcp .
docker run -p 8000:8000 -e MCP_AUTH_SECRET="$(openssl rand -hex 32)" swiss-courts-mcp
```

Relevante Umgebungsvariablen (siehe [`.env.example`](.env.example)):

| Variable | Default | Zweck |
|---|---|---|
| `MCP_HOST` | `127.0.0.1` | Bind-Host. Nur in Containern auf `0.0.0.0`. |
| `MCP_PORT` | `8000` | Bind-Port. |
| `MCP_ALLOW_PUBLIC_BIND` | `false` | Unterdrückt die `0.0.0.0`-Warnung (Container). |
| `MCP_STATELESS_HTTP` | `true` | Stateless HTTP → horizontale Skalierung ohne Sticky-Sessions. |
| `MCP_AUTH_ENABLED` | `false` | Aktiviert Bearer-Token-Auth für HTTP. |
| `MCP_AUTH_SECRET` | — | HS256-Signing-Key (Entwicklung). |
| `MCP_OAUTH_JWKS_URL` | — | JWKS-URL für RS256-Validierung (Produktion). |
| `MCP_REQUIRED_SCOPES` | — | Komma-separierte erforderliche Scopes. |
| `MCP_CORS_ORIGINS` | — | Komma-separierte erlaubte Origins (keine Wildcard in Prod). |

Die User-Identität stammt aus dem validierten JWT-`sub`-Claim; siehe
[ADR 0001](docs/adr/0001-http-auth.md).

---

## MCP-Protocol-Version

Der Server pinnt die MCP-Protocol-Version **`2025-11-25`** (Konstante
`PROTOCOL_VERSION` in `server.py`). Ein Regressionstest erkennt Drift gegen die
installierte SDK-Version, sodass ein Protocol-Bump eine bewusste Änderung ist
(Wert + CHANGELOG + diese Sektion). SDK-Updates kommen monatlich via Dependabot.

## Projekt-Phase

**Phase 1 — read-only** (siehe [ROADMAP.md](ROADMAP.md)). Alle Tools sind
`readOnlyHint: true`; keine schreibenden oder destruktiven Operationen. Der
Übergang zu Phase 2 erfordert einen sauberen Re-Audit und die in der Roadmap
genannten Gates.

---

## Verfügbare Tools

### Entscheid-Suche

| Tool | Beschreibung |
|------|-------------|
| `search_court_decisions` | Volltextsuche mit Kanton-, Ebenen- und Datumsfilter |
| `get_court_decision` | Einzelnen Entscheid anhand der Signatur abrufen |
| `search_bger_decisions` | Bundesgerichtsentscheide mit optionalem Abteilungsfilter |
| `search_by_law_reference` | Entscheide zu einem Gesetzesartikel finden (z.B. «Art. 8 BV») |

### Gerichts-Informationen

| Tool | Beschreibung |
|------|-------------|
| `list_courts` | Alle indexierten Gerichte auflisten, optional nach Kanton |
| `get_recent_decisions` | Neueste Entscheide, filterbar nach Kanton und Ebene |
| `get_decision_statistics` | Statistiken nach Kanton und Jahr |

### Tool-Annotations

Alle sieben Tools teilen dieselben Hints — read-only, idempotent,
nicht-destruktiv, externes System:

| Annotation | Wert |
|---|---|
| `readOnlyHint` | `true` |
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `true` |

Zusätzlich gibt es einen `rechtsrecherche`-**Prompt** (zweites MCP-Primitiv
neben den Tools).

### Anwendungsbeispiele

| Anwendungsfall | Tool-Kette |
|----------------|------------|
| Rechtsprechung zu Datenschutz | `search_court_decisions("Datenschutz")` |
| Praxis zu einem Grundrecht | `search_by_law_reference("Art. 8 BV")` |
| Neueste BGer-Entscheide | `search_bger_decisions("Arbeitsrecht", date_from="2024-01-01")` |
| Kombiniert: Gesetz + Praxis | `fedlex_search_laws("DSG")` dann `search_by_law_reference("Art. 25 DSG")` |

[→ Weitere Anwendungsbeispiele nach Zielgruppe →](EXAMPLES.md)

---

## Architektur

```
┌─────────────────────────────────────┐
│         MCP-Client (KI)             │
│   Claude / Cursor / Windsurf        │
└──────────────┬──────────────────────┘
               │ MCP-Protokoll
┌──────────────▼──────────────────────┐
│       swiss-courts-mcp              │
│  7 Tools · Pydantic-Validierung     │
│  Elasticsearch Query-Builder        │
└──────────────┬──────────────────────┘
               │ HTTPS (POST/GET)
┌──────────────▼──────────────────────┐
│       entscheidsuche.ch             │
│  Elasticsearch-Backend              │
│  Keine Authentifizierung nötig      │
│  Bund + 26 kantonale Gerichte       │
└─────────────────────────────────────┘
```

---

## Sicherheit & Limits

| Aspekt | Details |
|--------|---------|
| **Zugriff** | Nur lesend (`readOnlyHint: true`) — der Server kann keine Daten ändern oder löschen |
| **Personendaten** | Keine Personendaten — alle Entscheide sind öffentliche Gerichtsurteile |
| **Rate Limits** | Eingebaute Limits (max. 50 Ergebnisse pro Suche, 50 Aggregations-Buckets) |
| **Timeout** | 30 Sekunden pro API-Aufruf |
| **Datenquellen-Auth** | Kein API-Key nötig — entscheidsuche.ch ist öffentlich zugänglich |
| **HTTP-Transport-Auth** | Optionale Bearer-Token-Auth (JWT, `sub`-Claim-Identität); siehe [ADR 0001](docs/adr/0001-http-auth.md) |
| **Egress** | Code-Layer-Allow-List (nur `entscheidsuche.ch`, HTTPS erzwungen); siehe [Egress-Policy](docs/network-egress.md) |
| **Error-Masking** | Interne Exceptions nur serverseitig geloggt; Clients erhalten freundliche Meldungen |
| **Secrets** | Keine Secrets im Code/Log; `.env` git-ignoriert, Gitleaks auf PRs; siehe [Secret-Management](docs/secret-management.md) |
| **Lizenzen** | Gerichtsentscheide sind gemäss Schweizer Recht gemeinfrei ([BGG Art. 27](https://www.fedlex.admin.ch/eli/cc/2006/218/de#art_27)) |
| **Nutzungsbedingungen** | Gemäss [entscheidsuche.ch](https://entscheidsuche.ch) — bitte den Server schonend nutzen |

---

## Bekannte Einschränkungen

- Suche ist auf die von entscheidsuche.ch indexierten Entscheide beschränkt
- Volltext-Dokumente werden nicht zurückgegeben — nur Metadaten, Titel und Zusammenfassung
- Statistiken hängen von der Aggregations-Unterstützung des Backends ab
- Die Gerichts-Taxonomie aus `Facetten_alle.json` kann variieren

---

## Tests

Unit-Tests mocken HTTP mit `respx`; Live-Tests laufen in einem separaten
nächtlichen Workflow ([`live.yml`](.github/workflows/live.yml)) und blockieren
PRs nie.

```bash
# Unit-Tests (HTTP gemockt) — das läuft in der CI
pytest tests/ -v -m "not live"

# Live-API-Tests (echtes entscheidsuche.ch)
pytest tests/ -v -m live

# Linting
ruff check src/ tests/
ruff format src/ tests/
```

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md).

---

## Mitwirken

Siehe [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Lizenz

[MIT](LICENSE)

---

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

## Credits & Verwandte Projekte

- [entscheidsuche.ch](https://entscheidsuche.ch) — Schweizer Gerichtsentscheid-Suchmaschine
- [fedlex-mcp](https://github.com/malkreide/fedlex-mcp) — MCP-Server für Schweizer Bundesrecht (Gesetzes-Synergie)
- [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) — MCP-Server für Zürcher Open Data
- [Model Context Protocol](https://modelcontextprotocol.io/) — Offenes Protokoll für KI-Tool-Integration
