> **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**

# swiss-courts-mcp

![Version](https://img.shields.io/badge/version-0.1.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![No Auth Required](https://img.shields.io/badge/auth-none%20required-brightgreen)](https://github.com/malkreide/swiss-courts-mcp)
![CI](https://github.com/malkreide/swiss-courts-mcp/actions/workflows/ci.yml/badge.svg)

> MCP Server for Swiss court decisions — Federal Supreme Court (BGer), Federal Administrative Court (BVGer), Federal Criminal Court (BStGer), and all 26 cantonal courts via entscheidsuche.ch

[Deutsche Version](README.de.md)

<p align="center">
  <img src="assets/demo.svg" alt="Demo: Claude searches Swiss court decisions via MCP tool call" width="720">
</p>

---

## Overview

Access Swiss court decisions from all judicial levels through a single MCP interface. Combines full-text search with structured filters for canton, court level, date range, and law references.

| Source | Coverage | Data |
|--------|----------|------|
| [entscheidsuche.ch](https://entscheidsuche.ch) | Federal + 26 cantons | Court decisions since ~2000 |

**Synergy with [fedlex-mcp](https://github.com/malkreide/fedlex-mcp):** Legislation (SR) + case law = complete legal research.

---

## Features

- Full-text search across all Swiss court decisions
- Multi-stage law reference search with regex parser and Elasticsearch boost scoring
- Dedicated Federal Supreme Court search with chamber filter
- Canton and court level filtering
- Recent decisions feed
- Court taxonomy listing
- Decision statistics with aggregations
- Trilingual support (German, French, Italian)
- No API key required

---

## Prerequisites

- Python 3.11 or higher
- An MCP-compatible client (Claude Desktop, Cursor, Windsurf, etc.)

---

## Installation

```bash
pip install swiss-courts-mcp
```

Or install from source:

```bash
git clone https://github.com/malkreide/swiss-courts-mcp.git
cd swiss-courts-mcp
pip install -e ".[dev]"
```

---

## Quickstart

```bash
# Run directly
swiss-courts-mcp

# Or via Python module
python -m swiss_courts_mcp
```

---

## Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

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

### Cloud Deployment

```bash
swiss-courts-mcp --http --port 8000
```

---

## Available Tools

### Court Decision Search

| Tool | Description |
|------|-------------|
| `search_court_decisions` | Full-text search across all court decisions with canton, court level, and date filters |
| `get_court_decision` | Retrieve a single decision by its unique signature |
| `search_bger_decisions` | Search Federal Supreme Court decisions with optional chamber filter |
| `search_by_law_reference` | Find decisions citing a specific law article (e.g., "Art. 8 BV") |

### Court Information

| Tool | Description |
|------|-------------|
| `list_courts` | List all indexed courts, optionally filtered by canton |
| `get_recent_decisions` | Latest decisions, filterable by canton and court level |
| `get_decision_statistics` | Statistics on indexed decisions by canton and year |

### Example Use Cases

| Use Case | Tool Chain |
|----------|------------|
| Research case law on data protection | `search_court_decisions("Datenschutz")` |
| Find practice on a constitutional right | `search_by_law_reference("Art. 8 BV")` |
| Latest Federal Supreme Court rulings | `search_bger_decisions("Arbeitsrecht", date_from="2024-01-01")` |
| Combined: Law text + case law | `fedlex_search_laws("DSG")` then `search_by_law_reference("Art. 25 DSG")` |

---

## Architecture

```
┌─────────────────────────────────────┐
│         MCP Client (LLM)            │
│   Claude / Cursor / Windsurf        │
└──────────────┬──────────────────────┘
               │ MCP Protocol
┌──────────────▼──────────────────────┐
│       swiss-courts-mcp              │
│  7 tools · Pydantic validation      │
│  Elasticsearch query builder        │
└──────────────┬──────────────────────┘
               │ HTTPS (POST/GET)
┌──────────────▼──────────────────────┐
│       entscheidsuche.ch             │
│  Elasticsearch backend              │
│  No authentication required         │
│  Federal + 26 cantonal courts       │
└─────────────────────────────────────┘
```

---

## Safety & Limits

| Aspect | Details |
|--------|---------|
| **Access** | Read-only (`readOnlyHint: true`) — the server cannot modify or delete any data |
| **Personal data** | No personal data — all decisions are public court rulings |
| **Rate limits** | Built-in per-query caps (max 50 results per search, 50 aggregation buckets) |
| **Timeout** | 30 seconds per API call |
| **Authentication** | No API keys required — entscheidsuche.ch is publicly accessible |
| **Licenses** | Court decisions are public domain under Swiss law ([BGG Art. 27](https://www.fedlex.admin.ch/eli/cc/2006/218/de#art_27)) |
| **Terms of Service** | Subject to [entscheidsuche.ch](https://entscheidsuche.ch) usage terms — please be kind to the server |

---

## Project Structure

```
swiss-courts-mcp/
├── src/
│   └── swiss_courts_mcp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py            # MCP server + 7 tools
│       └── api_client.py        # HTTP client + ES query builder
├── tests/
│   ├── test_api_client.py
│   └── test_server.py
├── .github/workflows/
│   ├── ci.yml                   # Tests + linting
│   └── publish.yml              # PyPI trusted publishing
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                    # English
└── README.de.md                 # German
```

---

## Known Limitations

- Search is limited to decisions indexed by entscheidsuche.ch (not all decisions are publicly available)
- Full-text document content is not returned — only metadata, title, and abstract
- Statistics depend on Elasticsearch aggregation support of the backend
- The court taxonomy structure from `Facetten_alle.json` may vary

---

## Testing

```bash
# Unit tests
pytest tests/ -v -m "not live"

# Live API tests
pytest tests/ -v -m live

# Linting
ruff check src/ tests/
ruff format src/ tests/
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[MIT](LICENSE)

---

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

## Credits & Related Projects

- [entscheidsuche.ch](https://entscheidsuche.ch) — Swiss court decision search engine
- [fedlex-mcp](https://github.com/malkreide/fedlex-mcp) — MCP Server for Swiss federal law (legislation synergy)
- [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) — MCP Server for Zurich open data
- [Model Context Protocol](https://modelcontextprotocol.io/) — Open protocol for AI tool integration
