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
   <!-- gates:start -->
   ```bash
   pytest tests/ -m "not live"
   ruff check src/ tests/ scripts/
   ruff format --check src/ tests/ scripts/
   python scripts/check_version_sync.py
   python scripts/check_gate_docs.py
   ```
   <!-- gates:end -->
   These are the exact five gates CI runs — `scripts/` is a lint target,
   and the format check, the version sync and the gate-doc check are each
   their own gate. The version sync only bites when you touch the version:
   it holds `pyproject.toml` against `server.json` and the README badges,
   and fails on a version hardcoded in `src/`. The gate-doc check holds the
   list above against `ci.yml`, so adding a gate to CI without documenting
   it turns the build red. A command counts as a gate when its line carries the
   `# gate` marker — a YAML comment in `ci.yml`, a shell comment inside
   `live.yml`'s script block; neither reaches what actually runs. Mark a new
   gate there and the docs are required to name it.
6. Optional — run the live suite against the real source:
   <!-- live:start -->
   ```bash
   PYTHONPATH=src pytest tests/ -m live
   ```
   <!-- live:end -->
   Not a gate: it hits `entscheidsuche.ch` for real, so it is excluded from
   pull request CI and runs on a schedule (`live.yml`) instead. Worth doing
   by hand when you touch the client, the parsing, or anything that depends
   on the shape of the source's responses — that is exactly what the mocked
   unit tests cannot see. Red here does not automatically mean "our bug":
   query the source first, then judge.
7. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `feat: add new tool`
8. Push and open a Pull Request

---

## Code Style

- Python 3.11+, async/await throughout
- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting (config in `pyproject.toml`)
- Type hints required for all public functions
- Pydantic models for all tool inputs with `extra="forbid"`
- German for user-facing strings (error messages, tool descriptions); English for code identifiers
- Tests required for new tools; follow the existing FastMCP / Pydantic v2 patterns in `server.py`
- The 8 tools live in `server.py`, not a `tools/` package — a deliberate deviation from
  "split when > 5 tools". At this count one module stays readable and `register_tools` keeps
  registration declarative; revisit if the count grows. The offline fallback is isolated in
  `fallback.py`, separate from the live client.

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

## The live suite: when it runs, and who sees a red result

**Cadence:** daily at 04:00 UTC, plus on demand via *Actions → Live API Tests → Run
workflow*. See [`.github/workflows/live.yml`](.github/workflows/live.yml).

**Who sees it:** A red run opens an issue labelled `upstream` and the stable title “Live-Tests gegen entscheidsuche.ch rot (<Datum>)”. A second red run recognises the open issue by its title prefix and appends to that same thread rather than opening a second one. Once the suite is green again, the issue closes itself.

**Three answers, not two.** `scripts/classify_live_run.py` reads the JUnit XML rather than
the exit code and separates `clear` (ran, green), `finding` (ran, something
fell) and `unknown` (did not run — install failed, nothing collected,
everything skipped). An `unknown` never closes an issue: closing would claim a
comparison that never happened.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about entscheidsuche.ch. Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
