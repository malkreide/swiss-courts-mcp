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
   - **Nachtrag 19.9.2026 (SEC-009): `MCP_OAUTH_ISSUER` ist Pflicht** — der
     offene Punkt darüber ist geschlossen, und die Begründung liegt anders als
     dort vermutet. Nicht gemessen war, welche Clients `authorization_servers`
     auswerten; das bleibt ungemessen und trägt die Entscheidung auch nicht.
     Zwei Messungen tragen sie:

     1. **Das `iss`-Claim wurde nicht geprüft.** `verify_iss` hing an
        `bool(oauth_issuer)`. Ohne die Variable wurde ein Token mit
        `iss: https://fremder-tenant.example` **akzeptiert**, und eines ganz
        ohne `iss` ebenfalls; mit ihr `InvalidIssuerError` bzw.
        `MissingRequiredClaimError`. Dieselbe Confused-Deputy-Gestalt wie beim
        Publikum, und sie trägt, sobald mehrere Mandanten eine JWKS-URL teilen:
        die Signatur gilt dann für alle, nur `iss` trennt sie.
     2. **Die Discovery-Kette war tot.** `authorization_servers[0]` ist der
        Wert, den ein SDK-Client als `auth_server_url` übernimmt
        (`mcp/client/auth/oauth2.py`). Trug der Server sich selbst ein,
        antworteten `/.well-known/oauth-authorization-server`,
        `/.well-known/openid-configuration`, `/authorize`, `/token` und
        `/register` alle mit 404 — gemessen. Der Rückfall auf die eigene Basis-URL
        war also keine Milde, sondern ein Verweis ins Leere; er ist entfernt.

     Der Wert wird **nicht** normalisiert. Anders als bei `MCP_RESOURCE_URL`,
     wo ein abschliessender Schrägstrich abgeschnitten wird, ist er hier
     bedeutungstragend: `iss` mit Schrägstrich gegen einen Issuer ohne ihn ergibt
     gemessen `InvalidIssuerError`, und manche IdP stellen `iss` mit Schrägstrich
     aus.

     **Nebenbefund, und er korrigiert den Nachtrag über dem Publikumszwang:**
     die `verify_*`-Flags tragen die zweite Schicht nicht. In der pyjwt-Quelle
     (2.14.0) kehrt `_validate_iss(issuer=None)` in der ersten Zeile zurück, und
     `_validate_aud(audience=None)` wirft nur, wenn das Token ein `aud` *führt* —
     ein Token ganz ohne `aud` kam durch. Aufgefallen ist das an einer roten
     Gegenprobe, nicht an einer Überlegung. `_decode` liest deshalb einen
     fehlenden Erwartungswert selbst als Ablehnung
     (`MissingVerificationTargetError`, Unterklasse von
     `jwt.InvalidTokenError`, also 401 und kein 500).

   - **Offen bleibt:** `MCP_RESOURCE_URL` hat keinen Zwang. Die Rückfallebene
     auf die Bind-Adresse ist dort anders als beim Issuer nicht sinnlos — bei
     einem Loopback-Bind stimmt sie —, und das SDK verlangt einen Wert. Ob eine
     Warnung genügt oder ein Zwang bei Nicht-Loopback-Bind richtig wäre, ist
     nicht entschieden.
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
