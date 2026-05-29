# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-05-29

> **Audit verification:** production-ready ✅ — mcp-audit skill `v1.0.0`,
> 36 pass · 0 fail · 0 partial. Run `2026-05-29T191910-Z-swiss-courts-mcp`.

### Security

- HTTP transport now supports bearer-token authentication via the SDK-native
  `TokenVerifier` (JWT, identity from validated `sub` claim; HS256 + RS256/JWKS).
  See `docs/adr/0001-http-auth.md`. (SEC-009)
- Safe default bind host `127.0.0.1`; `0.0.0.0` requires explicit opt-in and logs
  a warning otherwise. (SEC-016)
- Egress allow-list (`entscheidsuche.ch` only, HTTPS-enforced) checked before
  every outbound request; see `docs/network-egress.md`. (SEC-021/SEC-004/SEC-005)
- Error masking: internal exceptions are logged server-side only; clients receive
  friendly messages. (OBS-002)
- Added `.gitignore` (`.env*` excluded), `.env.example`, and a Gitleaks CI
  workflow. (ARCH-005)

### Added

- CORS configuration for the HTTP transport exposing `Mcp-Session-Id`. (SDK-004)
- Stateless HTTP mode for horizontal scaling without sticky sessions. (SCALE-002)
- Structured logging (structlog) on stderr. (OBS-003)
- Context injection with progress reporting in search tools. (SDK-003)
- Machine-readable `match_type` and source/license provenance in responses.
  (ARCH-003/CH-004)
- All tools now emit `structuredContent` (a consistent response envelope with
  `source`, `license`, `match_type`, `count`, `total`, `results`/provenance)
  alongside the curated Markdown, via `CallToolResult` + `structured_output=False`.
  (SDK-002)
- `rechtsrecherche` prompt as a second MCP primitive. (ARCH-008)
- Hardened `Dockerfile` (non-root UID 10001), Dependabot, nightly live-test
  workflow, and `ROADMAP.md` with the explicit read-only Phase 1 declaration.
  (SEC-007/ARCH-012/OPS-001/OPS-003)
- `docs/`: network egress, secret management, and ADR 0001.

### Changed

- Tools now raise `ToolError` for upstream failures so errors surface as
  `isError` results instead of plain text. (OBS-001)
- Single shared `httpx.AsyncClient` via a FastMCP lifespan instead of one client
  per tool call. (SDK-001)
- Pinned MCP protocol version `2025-11-25` with a drift-detection test. (ARCH-012)
- README/README.de expanded (protocol version, phase, annotations, security);
  CONTRIBUTING is now bilingual. (OPS-002)

### Notes

- MCP protocol version: **2025-11-25**. No phase transition — server remains
  Phase 1 (read-only).

## [0.1.0] - 2026-04-12

### Added

- Full-text search across all Swiss court decisions (`search_court_decisions`)
- Single decision retrieval by signature (`get_court_decision`)
- Dedicated Federal Supreme Court search with chamber filter (`search_bger_decisions`)
- Multi-stage law reference search with regex parser and boost scoring (`search_by_law_reference`)
- Court taxonomy listing from Facetten_alle.json (`list_courts`)
- Recent decisions feed with canton and court level filters (`get_recent_decisions`)
- Decision statistics with Elasticsearch aggregations (`get_decision_statistics`)
- Pydantic input validation with all 26 Swiss cantons
- Trilingual support (German, French, Italian)
- Dual transport: stdio (local) and streamable-http (cloud)
- 55 unit and live API tests
- PyPI publication via GitHub Actions trusted publishing
