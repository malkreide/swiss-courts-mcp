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
   - **Publikumsbindung ist Pflicht** (`MCP_OAUTH_AUDIENCE`, Nachtrag
     2026-09-19): das `aud`-Claim bindet das Token an *diesen* Server. Die
     ursprüngliche Fassung machte die Prüfung von der Variable abhängig
     (`verify_aud=bool(oauth_audience)`) — fehlte sie, entfiel die Prüfung
     lautlos, und ein Token, das derselbe Issuer für einen anderen Dienst
     ausgestellt hatte, galt hier ebenfalls (Confused Deputy, nachgemessen).
     Ohne die Variable entsteht jetzt gar kein Verifier mehr.
   - **`AuthSettings.validate_token_resource` steht ausdrücklich auf `False`**
     (Nachtrag 2026-09-19). Ungesetzt verhält sich das Feld heute wie `False`,
     warnt aber, und `mcp` 3.0 dreht den Default bei gesetztem
     `resource_server_url` auf `True` — die Entscheidung gehört also in den
     Code. `False` ist hier richtig, weil der Verifier das Publikum selbst
     prüft (siehe oben, seit dem Zwang unbedingt). `True` wäre falsch, und
     zwar messbar: das SDK vergleicht `AccessToken.resource` als URL wörtlich
     mit `resource_server_url`, und das ist die Bind-Adresse
     (`http://<host>:<port>`). Am zusammengebauten Stack, `initialize` mit
     gültigem Bearer: fehlendes Publikum → 401, Publikum `swiss-courts-mcp`
     → 401, Publikum gleich der Bind-URL → 200. Hinter einem Reverse-Proxy ist
     die erreichbare URL ein anderer Name, und `0.0.0.0:8000` schreibt kein
     IdP in ein `aud`. Was fehlt, ist eine Einstellung für die *öffentliche*
     Resource-URL; solange die fehlt, ist `resource_server_url` hier eine
     Verlegenheitsangabe.
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
