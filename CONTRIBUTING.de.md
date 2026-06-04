# Mitwirken an swiss-courts-mcp

[:gb: English Version](CONTRIBUTING.md)

Vielen Dank für Ihr Interesse an einem Beitrag! Dieser Server ist Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide). Das Projekt folgt dem **No-Auth-First**-Prinzip — alle Datenquellen müssen ohne API-Key öffentlich zugänglich sein.

---

## Probleme melden

Nutzen Sie [GitHub Issues](https://github.com/malkreide/swiss-courts-mcp/issues), um Fehler zu melden oder Funktionen vorzuschlagen.

Bitte geben Sie an:
- Python-Version und Betriebssystem
- Vollständige Fehlermeldung oder Beschreibung des unerwarteten Verhaltens
- Schritte zur Reproduktion
- Bei API-Problemen: ob entscheidsuche.ch selbst erreichbar ist

---

## Pull Requests

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feat/ihr-feature`
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"`
4. Nehmen Sie Ihre Änderungen vor und ergänzen Sie Tests
5. Stellen Sie sicher, dass Tests und Linting bestehen:
   ```bash
   pytest tests/ -v -m "not live"
   ruff check src/ tests/
   ```
6. Committen Sie nach [Conventional Commits](https://www.conventionalcommits.org/): `feat: neues Tool hinzufügen`
7. Pushen Sie und öffnen Sie einen Pull Request

---

## Code-Stil

- Python 3.11+, durchgängig async/await
- [Ruff](https://github.com/astral-sh/ruff) für Linting und Formatierung (Konfiguration in `pyproject.toml`)
- Type Hints für alle öffentlichen Funktionen erforderlich
- Pydantic-Modelle für alle Tool-Inputs mit `extra="forbid"`
- Deutschsprachige User-Strings (Fehlermeldungen, Tool-Beschreibungen); englische Code-Identifier
- Tests für neue Tools erforderlich; den bestehenden FastMCP-/Pydantic-v2-Mustern in `server.py` folgen

---

## Datenquelle

Dieser Server nutzt den öffentlichen entscheidsuche.ch-Endpoint — keine Authentifizierung erforderlich.

| Quelle | URL | Auth |
|--------|-----|------|
| entscheidsuche.ch | https://entscheidsuche.ch | Keine |

Wenn Sie neue Abfragen hinzufügen, prüfen Sie diese zuerst manuell gegen den Endpoint und behandeln Sie Randfälle (fehlende optionale Felder, Timeout bei breiten Abfragen).

---

## Projekt-Phase

Der Server ist in **Phase 1 (read-only)** — siehe [ROADMAP.md](ROADMAP.md). Schreibende Tools werden erst nach Phase-2-Freigabe akzeptiert.

---

## Lizenz

Mit Ihrem Beitrag erklären Sie sich damit einverstanden, dass Ihre Beiträge unter der [MIT-Lizenz](LICENSE) lizenziert werden.
