[English Version](README.md)

> **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# 🏛️ swiss-courts-mcp

![Version](https://img.shields.io/badge/version-0.5.0-blue)
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

**🎯 Anker-Demo-Query:** *«Finde Bundesgerichts-Rechtsprechung zum Datenschutz (Art. 25 DSG) seit 2020 — und wenn entscheidsuche.ch ausfällt, antworte trotzdem aus dem Offline-Dump, klar gekennzeichnet.»*

| Quelle | Abdeckung | Daten |
|--------|-----------|-------|
| [entscheidsuche.ch](https://entscheidsuche.ch) (live, Default) | Bund + 26 Kantone | Gerichtsentscheide seit ca. 2000 |
| [SCD-Dump](https://doi.org/10.5281/zenodo.14867950) (Offline-Fallback) | **nur Bundesgericht, 2007–2024** | Metadaten/Regesten, **kein Volltext** |

**Synergie mit [fedlex-mcp](https://github.com/malkreide/fedlex-mcp):** Gesetzestext (SR) + Rechtsprechung = vollständige Rechtsrecherche.

**Verfügbarkeit:** entscheidsuche.ch ist Non-Profit-Infrastruktur ohne SLA. Fällt sie aus, weicht der Server transparent auf einen gecachten öffentlichen Dump aus (siehe [Offline-Fallback](#offline-fallback)). Jede Antwort deklariert ihre Herkunft (`source: "live" | "dump"`), und Dump-Antworten tragen ein `coverage_note` — der Fallback ist **partiell, nicht äquivalent**.

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
- **Offline-Fallback** auf einen gecachten öffentlichen Dump, wenn entscheidsuche.ch nicht erreichbar ist — mit expliziter Herkunft in jeder Antwort
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
| `MCP_OAUTH_AUDIENCE` | — | **Pflicht mit Auth.** Resource-Identifier, auf den der IdP Tokens bindet (`aud`). |
| `MCP_OAUTH_ISSUER` | — | **Pflicht mit Auth.** Issuer des IdP, der die Tokens ausstellt (`iss`), zeichengleich verglichen. |
| `MCP_RESOURCE_URL` | Bind-Adresse | **Öffentliche URL dieses Servers** — der Resource-Identifier nach RFC 9728. Bei Nicht-Loopback-Bind setzen. |
| `MCP_REQUIRED_SCOPES` | — | Komma-separierte erforderliche Scopes. |
| `MCP_CORS_ORIGINS` | — | Komma-separierte erlaubte Origins (keine Wildcard in Prod). |

Die User-Identität stammt aus dem validierten JWT-`sub`-Claim; siehe
[ADR 0001](docs/adr/0001-http-auth.md).

**`MCP_OAUTH_AUDIENCE` ist Pflicht, sobald Auth aktiv ist.** Das `aud`-Claim
bindet ein Token an *diesen* Server. Ohne die Variable prüfte der Verifier das
Publikum gar nicht und nahm jedes korrekt signierte Token desselben Issuers an
— auch eines, das für einen anderen Dienst ausgestellt wurde (Confused Deputy).
Der Server startet im Auth-Modus jetzt nicht mehr ohne sie.

**`MCP_OAUTH_ISSUER` ist ebenfalls Pflicht**, aus demselben Grund auf der
anderen Seite des Tokens. Das `iss`-Claim bindet ein Token an *den* IdP, dem
dieser Server traut. Das trägt, sobald mehrere Mandanten dieselbe JWKS-URL
teilen — der Normalfall bei einem gehosteten IdP: die Signatur ist dann für alle
gültig, und nur `iss` trennt sie. Nachgemessen ohne die Variable, Publikum
korrekt: ein Token mit `iss: https://fremder-tenant.example` wurde
**akzeptiert**, und ein Token ganz ohne `iss` ebenfalls. Der Wert wird nach
RFC 8414/9207 zeichengleich verglichen, abschliessender Schrägstrich
inbegriffen, und deshalb *nicht* normalisiert — anders als
`MCP_RESOURCE_URL`, wo ein Schrägstrich am Ende abgeschnitten wird.

Und er ist es, der die Discovery überhaupt erst tragfähig macht.
`authorization_servers[0]` im RFC-9728-Dokument ist der Wert, den ein SDK-Client
als seinen Authorization Server übernimmt. Ohne die Variable trug der Server
*sich selbst* dort ein — und unter dieser Adresse antworten
`/.well-known/oauth-authorization-server`,
`/.well-known/openid-configuration`, `/authorize`, `/token` und `/register`
alle mit 404, denn er ist ein Resource Server und kein Authorization Server.

**`MCP_RESOURCE_URL` ist das, was ein OAuth-Client braucht.** Nach RFC 9728
publiziert der Server einen Resource-Identifier unter
`/.well-known/oauth-protected-resource` und nennt ihn im `WWW-Authenticate`-
Header jeder 401 — dort sieht ein Client nach, wo er ein Token holt. Ohne die
Variable publiziert er seine *Bind*-Adresse; nachgemessen mit Container-Bind war
das `{"resource": "http://0.0.0.0:8000", …}`, eine Adresse, die kein Client
anwählen kann. Bei jedem Nicht-Loopback-Bind setzen; fehlt sie, warnt der
Server beim Start.

Das SDK-eigene `validate_token_resource` bleibt aus **einem gemessenen Grund
aus**: es vergleicht den Resource-Indicator des Tokens wörtlich mit
`resource_server_url`, und das ist hier die *Bind*-Adresse. Ein Token, dessen
Publikum nicht genau diese URL ist, wird mit 401 abgewiesen — eingeschaltet
würde es also jeden realen Client aussperren, während die Publikumsprüfung
oben das ist, was den Server tatsächlich schützt.

### Offline-Fallback (ENV)

| Variable | Default | Zweck |
|---|---|---|
| `SWISS_COURTS_FALLBACK_ENABLED` | `true` | Hauptschalter. `0` deaktiviert den Dump-Fallback (nur Live). |
| `SWISS_COURTS_FORCE_DUMP` | `false` | Erzwingt den Dump-Pfad (überspringt Live) — zum Vorwärmen oder für Offline-Tests. |
| `SWISS_COURTS_CACHE_DIR` | `platformdirs`-Cache | Überschreibt das Cache-Verzeichnis des heruntergeladenen Dumps. |
| `SWISS_COURTS_DUMP_RECORD` | `14867950` | Zenodo-Record-ID des zu nutzenden SCD-Dumps. |

Cache vorwärmen (lädt den ~120-MB-SCD-CSV einmalig, damit der erste echte
Ausfall nicht die Download-Zeit zahlt):

```bash
SWISS_COURTS_FORCE_DUMP=1 python -m swiss_courts_mcp  # dann eine Suche absetzen
```

---

## MCP-Protocol-Versionen

Der Server bedient **zwei Protokoll-Ären** über denselben Endpunkt; die erste
Anfrage des Clients entscheidet, welche er bekommt:

| Ära | Revision | Konstante in `server.py` | Handshake |
|-----|----------|--------------------------|-----------|
| Legacy | `2025-11-25` | `HANDSHAKE_PROTOCOL_VERSION` | `initialize`, Session-ID |
| Modern | `2026-07-28` | `MODERN_PROTOCOL_VERSION` | keiner — `_meta`-Envelope je Request |

Beide Revisionen sind gepinnt, und beide haben einen Drift-Guard gegen die
installierte SDK-Version — ein Protocol-Bump bleibt damit eine bewusste Änderung
(Konstante + CHANGELOG + diese Sektion). SDK-Updates kommen monatlich via
Dependabot.

**Spec `2026-07-28` ist die Ära, die der SDK-eigene Client wählt.** `mcp.Client`
probt `server/discover` und fällt nur bei Ablehnung auf den Handshake zurück;
gegen diesen Server fällt er nicht zurück. Nachgemessen durch den
zusammengebauten ASGI-Stack in `tests/test_modern_era.py`, nicht aus
Konstantennamen geschlossen.

Was in der Modern-Ära anders ist:

- **Kein `initialize`, keine Session-ID.** Jeder POST steht für sich und trägt
  in `params._meta` die Protokoll-Revision und die Client-Capabilities, dazu die
  Routing-Header `MCP-Protocol-Version`, `Mcp-Method` und — bei `tools/call`,
  `prompts/get`, `resources/read` — `Mcp-Name`.
- **`server/discover`** ersetzt den Handshake für die Capability-Auskunft,
  `subscriptions/listen` ersetzt die Änderungs-Notifications.
- **`ping`, `logging/setLevel` und das `resources/subscribe`-Paar gibt es nicht
  mehr.** In dieser Ära antwortet der Server darauf mit `-32601`; in der
  Legacy-Ära bleiben sie erreichbar.
- **`ttlMs` / `cacheScope`** hängen an den auflistenden Methoden (SEP-2549) —
  siehe `CACHE_HINTS`.
- **`serverInfo` wird in das `_meta` jeder Antwort gestempelt**, weil es keinen
  Handshake gibt, der es einmalig überträgt. Der Stempel nennt Build-Version,
  Anzeigename und Projekt-URL; der Zwecktext bleibt in `instructions`, und die
  reist einmalig mit `server/discover`.

Ein `initialize`, das `2026-07-28` anfragt, bekommt weiterhin `2025-11-25`
zurück: der Handshake ist nicht der Weg in die Modern-Ära, und diese Antwort
sagt nichts darüber, ob der Server sie spricht.

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
| `get_fallback_status` | Zustand des Offline-Dump-Caches, Abdeckung, Version, Vorwärmen (read-only) |

### Tool-Annotations

Alle acht Tools teilen dieselben Hints — read-only, idempotent,
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
┌──────────────▼──────────────────────────────┐
│              swiss-courts-mcp               │
│  8 Tools · Pydantic-Validierung             │
│  Elasticsearch Query-Builder                │
│  Provenance-Envelope: source = live | dump  │
└───────┬──────────────────────────────┬──────┘
        │ ① live (Default)             │ ② Fallback
        │ HTTPS POST/GET               │ bei Bot-Block / 5xx / 429 /
        │                              │ Timeout, oder SWISS_COURTS_FORCE_DUMP=1
┌───────▼──────────────────┐   ┌───────▼───────────────────────────────┐
│     entscheidsuche.ch    │   │   SCD-Dump — Zenodo 14867950 (CC BY)  │
│  Elasticsearch-Backend   │   │   Lazy-Download → platformdirs-Cache  │
│  Bund + 26 Kantone       │   │   → lokale SQLite-Suche               │
│  keine Auth · kein SLA   │   │   nur BGer · 2007–2024 · kein Volltext │
└──────────────────────────┘   └───────────────────────────────────────┘
```

Immer Live-first: Der Offline-Dump greift nur bei einem Verfügbarkeitsfehler
(Bot-Block, HTTP 5xx/429, Timeout) oder wenn erzwungen. Er ist ein Verhalten
der bestehenden Tools, kein zusätzliches Such-Tool — warum diese Quelle und
nicht die Volltext-Variante, steht in
[ADR 0002](docs/adr/0002-offline-fallback.md); was er abdeckt und was nicht,
unter [Bekannte Einschränkungen](#bekannte-einschränkungen). Cache jederzeit
mit `get_fallback_status` einsehbar.

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
| **Egress** | Code-Layer-Allow-Lists (`entscheidsuche.ch` für Live; `zenodo.org` für den Offline-Dump), HTTPS erzwungen; siehe [Egress-Policy](docs/network-egress.md) |
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

**Offline-Fallback (partielle Abdeckung — bitte lesen):** Der Fallback ist ein
Sicherheitsnetz für die Verfügbarkeit, **kein gleichwertiger Spiegel** der
Live-Quelle:

- **Gerichts-Umfang:** nur Bundesgericht (BGer/BGE). Bundesverwaltungsgericht,
  Bundesstrafgericht und **alle 26 kantonalen Gerichte sind nicht abgedeckt.**
- **Zeitraum:** 2007 – Dezember 2024 (Zeitspanne des SCD-Dumps). Entscheide
  ausserhalb dieses Fensters sind nicht enthalten.
- **Inhalt:** nur Metadaten/Regesten — **offline kein Volltext**.
- **Aktualisierungslatenz:** Der SCD-Dump wird auf Zenodo etwa quartalsweise
  aktualisiert; die Offline-Daten hinken dem Live-Index also nach.
  `get_fallback_status` zeigt die gecachte Version und kann Zenodo auf eine
  neuere prüfen.
- **Gesetzesreferenz-Suche** trifft offline nur Referenzen, die im Betreff/Regest
  (`topic`/`issue`) des Entscheids genannt sind — es gibt keinen Offline-Index
  zitierter Gesetze.
- **`get_court_decision` ist offline best-effort:** SCD-Aktenzeichen (`docref`,
  z.B. `1C_517/2016`) unterscheiden sich von entscheidsuche-Signaturen, daher
  werden manche Lookups ehrlich als nicht auflösbar gemeldet.
- Antworten deklarieren ihre Herkunft stets über `source` (`live`/`dump`) und ein
  `coverage_note`; der Server reduziert die Abdeckung nie stillschweigend — eine
  nicht abgedeckte Anfrage bekommt eine explizite «nicht abgedeckt»-Antwort, nie
  ein stilles leeres Resultat.

---

## Tests

Unit-Tests mocken HTTP mit `respx`. Vom Projekt-Root ausführen. Die fünf
Gates, die die CI fährt — `check_gate_docs.py` hält diese Liste gegen
`ci.yml`, sie kann also nicht still veralten:

<!-- gates:start -->
```bash
PYTHONPATH=src pytest tests/ -m "not live"
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py
python scripts/check_gate_docs.py
```
<!-- gates:end -->

Die Live-Tests sind kein Gate — sie fragen die echte Quelle ab und laufen nach
Plan ([`live.yml`](.github/workflows/live.yml)), nicht auf Pull Requests:

<!-- live:start -->
```bash
PYTHONPATH=src pytest tests/ -v -m live
```
<!-- live:end -->

Sonderfall `live.yml`: GitHub beachtet `schedule` nur auf dem Default-Branch,
Änderungen wirken also erst nach dem Merge — vorher von Hand auslösen
(`workflow_dispatch`).

Die Offline-Fallback-Tests mocken den Zenodo-Download mit `respx` und nutzen
eine kleine mitgelieferte Fixture — der ~120-MB-Dump wird in der CI nie
heruntergeladen.

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md).

---

## Mitwirken

Siehe [CONTRIBUTING.de.md](CONTRIBUTING.de.md).

---

## Sicherheit

Siehe [SECURITY.de.md](SECURITY.de.md) für die Sicherheitslage und das Melden von Schwachstellen.

---

## Lizenz

[MIT](LICENSE)

---

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

## Credits & Verwandte Projekte

- [entscheidsuche.ch](https://entscheidsuche.ch) — Schweizer Gerichtsentscheid-Suchmaschine (Live-Quelle)
- **Swiss Federal Supreme Court Dataset (SCD)** — Offline-Fallback-Quelle, **CC BY 4.0**:
  Geering, F. & Merane, J. (2025). *Swiss Federal Supreme Court Dataset (SCD)*, Version 2024-3. Zenodo. https://doi.org/10.5281/zenodo.14867950
- [fedlex-mcp](https://github.com/malkreide/fedlex-mcp) — MCP-Server für Schweizer Bundesrecht (Gesetzes-Synergie)
- [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) — MCP-Server für Zürcher Open Data
- [Model Context Protocol](https://modelcontextprotocol.io/) — Offenes Protokoll für KI-Tool-Integration
