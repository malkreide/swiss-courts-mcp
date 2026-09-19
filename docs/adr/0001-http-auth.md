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
   - **`MCP_RESOURCE_URL`** (Nachtrag 2026-09-19, zweiter Teil): die
     öffentliche URL dieses Servers, als `resource_server_url`. Der obige
     Nachtrag nannte ihr Fehlen einen offenen Punkt und verortete ihn beim
     Token-Check — das war zu eng. Nachgemessen betrifft es vor allem, was der
     Server **publiziert**: mit 0.0.0.0-Bind gab
     `/.well-known/oauth-protected-resource` (RFC 9728)
     `{"resource": "http://0.0.0.0:8000", "authorization_servers":
     ["http://0.0.0.0:8000"]}` heraus, und die 401 nannte dieselbe Adresse als
     `resource_metadata`. Ein Client, der dem Standard folgt, um den Ort fürs
     Token zu finden, landete auf einer nicht anwählbaren Adresse.

     Rückfallebene bleibt die Bind-Adresse — das SDK verlangt eine
     `resource_server_url`, und ohne sie fielen Metadaten-Route und
     401-Hinweis ganz weg; eine unerreichbare Angabe mit Warnung ist besser als
     gar keine. Bei Nicht-Loopback-Bind warnt `_public_url`, wie
     `build_transport_security` es bei `allowed_hosts` tut: der erreichbare
     Name steht nicht in der Bind-Adresse, also nicht raten.

     An `validate_token_resource` ändert das nichts. `True` prüfte
     `AccessToken.resource` gegen `resource_server_url`, und dieser Server
     stellt dort `oauth_audience` ein — dasselbe Feld, das der Verifier bereits
     unbedingt prüft. Eine zweite Prüfung derselben Tatsache sichert nichts
     zusätzlich.
   - **Offen:** ohne `MCP_OAUTH_ISSUER` trägt der Server sich selbst als
     `authorization_servers` ein, was sachlich falsch ist — er stellt keine
     Tokens aus. Die Adresse ist jetzt wenigstens erreichbar, und `_public_url`
     warnt; richtig wird es erst mit gesetztem Issuer. Ein Zwang wie bei
     `MCP_OAUTH_AUDIENCE` wäre denkbar, ist hier aber nicht gemessen: welche
     Clients das Feld überhaupt auswerten, wurde nicht geprüft.
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
