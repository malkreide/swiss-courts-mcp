# Secret Management (SEC-013, ARCH-005)

## Datenklasse: Public Open Data

Die Datenquelle `entscheidsuche.ch` ist öffentlich und benötigt **keinen
API-Key**. Im read-only Standardbetrieb (stdio) verarbeitet der Server keine
Secrets.

## Secrets im HTTP-Modus

Aktiviert man die Bearer-Token-Auth (SEC-009), kommen Secrets ins Spiel:

| Secret | Variable | Zweck |
|---|---|---|
| HS256-Signing-Key | `MCP_AUTH_SECRET` | symmetrische Token-Validierung |
| JWKS-URL | `MCP_OAUTH_JWKS_URL` | asymmetrische (RS256) Validierung |

### Regeln

- Secrets werden **ausschliesslich** zur Laufzeit über Environment-Variablen
  bzw. einen Secret-Manager geladen — niemals im Code, niemals im Container-Layer
  (`docker history`-sauber, siehe `Dockerfile`).
- `.env` ist in `.gitignore`; nur `.env.example` mit Platzhaltern ist eingecheckt.
- Gitleaks läuft auf jedem PR (`.github/workflows/security.yml`).
- Keine Secrets in Logs: `handle_error` maskiert Internas, der Token-Verifier
  loggt nie den Token-Inhalt (nur Fehlertyp / `sub`).

### Empfehlung Produktion

Für `Verwaltungsdaten`/`PII` (aktuell nicht zutreffend) wäre ein Secret-Manager
(Stufe 3) mit Region Schweiz/EU und Rotation ohne Code-Änderung verbindlich.
Für Public Open Data ist die Env-Var-Stufe ausreichend und hier dokumentiert.
