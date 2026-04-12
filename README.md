# swiss-courts-mcp

MCP-Server für Schweizer Gerichtsentscheide via [entscheidsuche.ch](https://entscheidsuche.ch).

Aggregiert Urteile des **Bundesgerichts (BGer)**, **Bundesverwaltungsgerichts (BVGer)**, **Bundesstrafgerichts (BStGer)** und **kantonaler Gerichte** aller 26 Kantone.

## Synergie mit fedlex-mcp

Kombiniert mit [fedlex-mcp](https://github.com/malkreide/fedlex-mcp) ergibt sich eine vollständige Rechtsrecherche:

| Server | Funktion | Beispiel |
|--------|----------|----------|
| **fedlex-mcp** | Gesetzestext (SR) | `fedlex_search_laws("Datenschutz")` |
| **swiss-courts-mcp** | Rechtsprechung | `search_by_law_reference("Art. 25 DSG")` |

## Tools

| Tool | Beschreibung |
|------|-------------|
| `search_court_decisions` | Volltextsuche in allen Gerichtsentscheiden |
| `get_court_decision` | Einzelnes Urteil anhand der Signatur abrufen |
| `search_bger_decisions` | Bundesgerichtsentscheide gezielt suchen |
| `search_by_law_reference` | Entscheide zu einem Gesetzesartikel finden |
| `list_courts` | Verfügbare Gerichte auflisten |
| `get_recent_decisions` | Neueste Entscheide abrufen |
| `get_decision_statistics` | Statistiken über indexierte Entscheide |

## Installation

```bash
# Aus dem Repository
git clone https://github.com/malkreide/swiss-courts-mcp.git
cd swiss-courts-mcp
pip install -e ".[dev]"
```

## Claude Desktop Konfiguration

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "swiss-courts": {
      "command": "python",
      "args": ["-m", "swiss_courts_mcp"],
      "env": {}
    }
  }
}
```

## Nutzung

### Volltextsuche
```
Suche nach Gerichtsentscheiden zum Thema "Datenschutz" im Kanton Zürich
→ search_court_decisions(query="Datenschutz", canton="ZH")
```

### Praxis zu Gesetzesartikel
```
Finde Urteile die Art. 8 BV (Rechtsgleichheit) zitieren
→ search_by_law_reference(law_reference="Art. 8 BV")
```

### Bundesgericht
```
Neueste BGer-Entscheide zum Arbeitsrecht
→ search_bger_decisions(query="Arbeitsrecht", date_from="2024-01-01")
```

### Neueste Entscheide
```
Aktuelle Urteile des Bundesverwaltungsgerichts
→ get_recent_decisions(court_level="bundesverwaltungsgericht", limit=10)
```

## Entwicklung

```bash
# Tests
pytest tests/ -v

# Live-Tests (gegen echte API)
pytest tests/ -v -m live

# Linting
ruff check src/ tests/
ruff format src/ tests/
```

## Datenquelle

- **API:** [entscheidsuche.ch](https://entscheidsuche.ch) (Elasticsearch-basiert)
- **Lizenz:** Freie Nutzung, kein API-Key nötig
- **Abdeckung:** Bundesgerichte + 26 Kantone, ab ca. 2000
- **Sprachen:** Deutsch, Französisch, Italienisch

## Lizenz

MIT
