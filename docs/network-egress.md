# Network Egress Policy (SEC-021)

Der Server kommuniziert ausgehend mit zwei fest verdrahteten Hosts: der
Live-Quelle und — nur im Offline-Fallback — dem Dump-Anbieter.

## Erlaubte Ziele

| Host | Zweck | Schema | Layer |
|---|---|---|---|
| `entscheidsuche.ch` | Such-API + Dokument-/Facetten-Abruf (live) | HTTPS | `api_client.ALLOWED_HOSTS` |
| `zenodo.org` | SCD-Dump: Metadaten, Versions-API, CSV-Download (Fallback) | HTTPS | `fallback.ALLOWED_HOSTS` |

## Code-Layer-Schranke

Beide Allow-Lists sind als **`frozenset`** definiert und zur Laufzeit nicht
mutierbar — bewusst getrennt pro Layer:

- Der Live-Client (`src/swiss_courts_mcp/api_client.py`, `ALLOWED_HOSTS`) ruft
  vor **jedem** Request `assert_host_allowed(url)` auf (HTTPS + Host-Check).
- Der Fallback-Layer (`src/swiss_courts_mcp/fallback.py`, `ALLOWED_HOSTS`) ruft
  vor jedem Zenodo-Request `_assert_zenodo(url)` auf (HTTPS + Host-Check).

Verstösse werfen `EgressNotAllowedError` bzw. `FallbackUnavailableError` und
werden serverseitig geloggt. User-Eingaben fliessen nie in die Request-URL; die
Ziel-URLs werden ausschliesslich aus konstanten Basis-URLs und der
Zenodo-Record-ID gebildet (SEC-004, SEC-005).

> Hinweis: Zenodo liefert Datei-Downloads teils via 301/302-Redirect aus. httpx
> folgt diesen innerhalb des Requests; der Egress-Guard prüft die initiale URL
> (stets `zenodo.org`). Im Cloud-Betrieb sollte die Netzwerk-Schranke unten
> `zenodo.org` und dessen Storage-Redirect-Ziele einschliessen.

## Network-Layer-Schranke (Deployment)

Im Cloud-Betrieb zusätzlich auf Infrastruktur-Ebene absichern:

- Kubernetes `NetworkPolicy` / Security Group: Egress nur zu `entscheidsuche.ch`
  und `zenodo.org` (Port 443) plus DNS (Port 53).
- Optional Egress-Proxy (z.B. Smokescreen) als Defense-in-Depth.

## Erweiterung der Allow-List

Neue Hosts werden bewusst in der jeweiligen `ALLOWED_HOSTS` (`api_client` bzw.
`fallback`) ergänzt, mit Eintrag in dieser Datei und im `CHANGELOG.md`. Keine
Konfiguration zur Laufzeit.
