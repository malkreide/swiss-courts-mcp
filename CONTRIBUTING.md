# Contributing

Contributions are welcome! This project follows a **No-Auth-First** principle — all data sources must be publicly accessible without API keys.

## Reporting Issues

- Use [GitHub Issues](https://github.com/malkreide/swiss-courts-mcp/issues)
- Include steps to reproduce, expected vs. actual behavior
- For API issues, note whether entscheidsuche.ch itself is reachable

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make your changes
5. Run tests and linting:
   ```bash
   pytest tests/ -v -m "not live"
   ruff check src/ tests/
   ```
6. Commit with a descriptive message and open a PR

### Commit Messages

Use conventional commits where possible:

- `feat: add new tool for X`
- `fix: handle empty response from API`
- `docs: update README with new examples`
- `test: add tests for law reference parser`

## Code Style

- Python 3.11+, async/await throughout
- Ruff for formatting and linting (config in `pyproject.toml`)
- Pydantic models for all tool inputs with `extra="forbid"`
- German for user-facing strings (error messages, tool descriptions)
- English for code identifiers (function names, variables)

## Data Sources

| Source | URL | Auth |
|--------|-----|------|
| entscheidsuche.ch | https://entscheidsuche.ch | None |

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

## Beitragen (Deutsch)

Beiträge sind willkommen! Das Projekt folgt dem **No-Auth-First**-Prinzip —
alle Datenquellen müssen ohne API-Key öffentlich zugänglich sein.

- **Issues:** über [GitHub Issues](https://github.com/malkreide/swiss-courts-mcp/issues),
  mit Reproduktionsschritten und erwartetem vs. tatsächlichem Verhalten.
- **Pull Requests:** Feature-Branch, `pip install -e ".[dev]"`, dann
  `pytest tests/ -v -m "not live"` und `ruff check src/ tests/` ausführen.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`).
- **Code-Stil:** Python 3.11+, async/await, Ruff, Pydantic mit `extra="forbid"`;
  deutschsprachige User-Strings, englische Code-Identifier.
- **Phasen:** Der Server ist in **Phase 1 (read-only)** — siehe
  [ROADMAP.md](ROADMAP.md). Schreibende Tools erst nach Phase-2-Freigabe.
