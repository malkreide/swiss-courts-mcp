# Contributing to swiss-courts-mcp

[:de: Deutsche Version](CONTRIBUTING.de.md)

Thank you for your interest in contributing! This server is part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide). The project follows a **No-Auth-First** principle — all data sources must be publicly accessible without API keys.

---

## Reporting Issues

Use [GitHub Issues](https://github.com/malkreide/swiss-courts-mcp/issues) to report bugs or request features.

Please include:
- Python version and OS
- Full error message or description of unexpected behaviour
- Steps to reproduce
- For API issues, note whether entscheidsuche.ch itself is reachable

---

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make your changes and add tests
5. Ensure tests and linting pass:
   ```bash
   pytest tests/ -v -m "not live"
   ruff check src/ tests/
   ```
6. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `feat: add new tool`
7. Push and open a Pull Request

---

## Code Style

- Python 3.11+, async/await throughout
- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting (config in `pyproject.toml`)
- Type hints required for all public functions
- Pydantic models for all tool inputs with `extra="forbid"`
- German for user-facing strings (error messages, tool descriptions); English for code identifiers
- Tests required for new tools; follow the existing FastMCP / Pydantic v2 patterns in `server.py`

---

## Data Source

This server uses the public entscheidsuche.ch endpoint — no authentication required.

| Source | URL | Auth |
|--------|-----|------|
| entscheidsuche.ch | https://entscheidsuche.ch | None |

When adding new queries, verify them manually against the endpoint first and handle edge cases (missing optional fields, timeout on broad queries).

---

## Project Phase

The server is in **Phase 1 (read-only)** — see [ROADMAP.md](ROADMAP.md). Writing tools are only accepted after Phase 2 is cleared.

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
