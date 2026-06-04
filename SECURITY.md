# Security Policy & Posture

[:de: Deutsche Version](SECURITY.de.md)

`swiss-courts-mcp` was hardened against the internal MCP best-practice audit catalogue. This document summarises the security posture and explains how to report a vulnerability.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the maintainer listed in `README.md`. Do not file public issues for exploitable vulnerabilities.

## Posture summary

This is a **read-only**, **no-PII**, **public-open-data** MCP server. All 7 tools only issue read queries against the entscheidsuche.ch Elasticsearch backend (`entscheidsuche.ch`); the data consists of public court decisions. Hardening already in place:

| Area | Control |
|---|---|
| Access | Read-only (`readOnlyHint: true`) — the server cannot modify or delete any data |
| Egress | HTTPS-enforced allow-list to `entscheidsuche.ch` only (SEC-021; see [egress policy](docs/network-egress.md)) |
| Binding | Network transports default to `127.0.0.1`; `0.0.0.0` must be opted into explicitly (SEC-016) |
| HTTP auth | Optional bearer-token auth (JWT, `sub`-claim identity only), TTL via token `exp`, HS256 (dev) / RS256+JWKS (prod) (SEC-009; see [ADR 0001](docs/adr/0001-http-auth.md)) |
| Transport | Stateless streamable HTTP with CORS exposing only explicitly configured origins (SDK-004) |
| Input | Pydantic v2 strict validation (`extra="forbid"`) at all boundaries (SEC-018) |
| Secrets | Env-vars only, `.gitignore` guards `.env`, Gitleaks on PRs, no hardcoded secrets (SEC-013; see [secret management](docs/secret-management.md)) |
| Errors | Upstream bodies logged to stderr, never forwarded to the model (OBS-002) |
| Stdout | Reserved for the JSON-RPC stream; logging pinned to stderr (OBS-004) |
| Limits | Per-query caps (max 50 results per search, 50 aggregation buckets), 30 s timeout per API call |

The latest audit run (`2026-05-29T191910-Z-swiss-courts-mcp`) reports **production-ready**: 36 pass · 0 fail · 0 partial. See `audits/` for the full report and `CHANGELOG.md` for the hardening history.

## Re-evaluation triggers

The security posture should be re-audited if the server ever:

- gains **write** capability or starts processing **PII**, or
- adds a new **data source** or relaxes the egress allow-list, or
- changes its **authentication** model, or
- registers tools **dynamically** / from remote sources, or
- is aggregated behind a shared MCP gateway (then enable the gateway's tool allow-listing and tool-poisoning detection).
