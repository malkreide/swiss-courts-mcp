# Network Egress Policy (SEC-021)

Der Server kommuniziert ausgehend ausschliesslich mit einem einzigen Host.

## Erlaubte Ziele

| Host | Zweck | Schema |
|---|---|---|
| `entscheidsuche.ch` | Such-API + Dokument-/Facetten-Abruf | HTTPS |

## Code-Layer-Schranke

Die Allow-List ist als **`frozenset`** in `src/swiss_courts_mcp/api_client.py`
(`ALLOWED_HOSTS`) definiert und zur Laufzeit nicht mutierbar. Vor **jedem**
ausgehenden Request wird `assert_host_allowed(url)` aufgerufen; es erzwingt
HTTPS und prüft den Host gegen die Allow-List. Verstösse werfen
`EgressNotAllowedError` und werden serverseitig geloggt.

Da nur ein fester Host erlaubt ist, ist die SSRF- und DNS-Rebinding-Fläche
praktisch null (SEC-004, SEC-005): User-Eingaben fliessen nie in die Request-URL.

## Network-Layer-Schranke (Deployment)

Im Cloud-Betrieb zusätzlich auf Infrastruktur-Ebene absichern:

- Kubernetes `NetworkPolicy` / Security Group: Egress nur zu `entscheidsuche.ch`
  (Port 443) plus DNS (Port 53).
- Optional Egress-Proxy (z.B. Smokescreen) als Defense-in-Depth.

## Erweiterung der Allow-List

Neue Hosts werden bewusst in `ALLOWED_HOSTS` ergänzt, mit Eintrag in dieser
Datei und im `CHANGELOG.md`. Keine Konfiguration zur Laufzeit.
