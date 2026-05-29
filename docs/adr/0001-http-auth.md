# ADR 0001 — Authentifizierung im HTTP-Transport

**Status:** akzeptiert · **Datum:** 2026-05-29 · **Bezug:** SEC-009, SEC-016

## Kontext

Der Server unterstützt Dual-Transport: `stdio` (lokal) und `streamable-http`
(Cloud). Der HTTP-Modus ist ohne Schutz über das Netzwerk erreichbar; in
Kombination mit einem `0.0.0.0`-Bind wäre er vollständig offen (NeighborJack).

## Entscheidung

1. **stdio bleibt ohne Auth.** Lokaler Betrieb (Claude Desktop) ist
   vertrauenswürdig (SEC-006); der Default-Transport öffnet keinen Port.
2. **HTTP-Modus erhält Bearer-Token-Auth** über das SDK-native
   `TokenVerifier`-Protokoll (`JWTTokenVerifier`):
   - User-Identität stammt **ausschliesslich** aus dem validierten JWT
     (`sub`-Claim), nie aus Client-Headern.
   - Token-`exp` erzwingt die Session-TTL; abgelaufene Token werden abgelehnt.
   - HS256 (Secret) für Entwicklung, RS256/JWKS für Produktion.
   - Optionale Scope-Prüfung (`MCP_REQUIRED_SCOPES`).
3. **Sicherer Bind-Default** `127.0.0.1`; `0.0.0.0` nur bewusst per
   `MCP_HOST` + `MCP_ALLOW_PUBLIC_BIND` (im Dockerfile gesetzt).
4. **`stateless_http`** standardmässig aktiv → horizontale Skalierung ohne
   Sticky-Sessions (SCALE-002).
5. **CORS** wird nur mit explizit konfigurierten Origins aktiviert; `Mcp-Session-Id`
   wird via `expose_headers`/`allow_headers` freigegeben (SDK-004).

## Konsequenzen

- Wird der HTTP-Modus ohne `MCP_AUTH_ENABLED=true` gestartet, loggt der Server
  eine Warnung — der Betreiber muss dann selbst einen authentifizierenden
  Reverse-Proxy vorschalten.
- Die Trifecta-Bewertung (SEC-019) bleibt unkritisch: read-only, eine Fähigkeit.
