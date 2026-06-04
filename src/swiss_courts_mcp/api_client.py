"""
HTTP-Client für entscheidsuche.ch
=================================
Zentraler API-Client für die Elasticsearch-basierte Suchschnittstelle
von entscheidsuche.ch (Schweizer Gerichtsentscheide).

Endpunkte:
  - POST _search.php     → Volltextsuche (Elasticsearch-Body)
  - GET  /docs/{id}.json → Einzelnes Urteil
  - GET  /docs/Facetten_alle.json → Gerichts-Taxonomie
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from swiss_courts_mcp.logging_config import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

SEARCH_URL = "https://entscheidsuche.ch/_search.php"
DOCS_BASE = "https://entscheidsuche.ch/docs"
FACETS_URL = f"{DOCS_BASE}/Facetten_alle.json"

REQUEST_TIMEOUT = 30.0
MAX_SIZE = 50

# Egress-Allow-List (SEC-021): Code-Layer-Schranke gegen ungewollte Ziele.
# Bewusst als frozenset, nicht zur Laufzeit mutierbar.
ALLOWED_HOSTS: frozenset[str] = frozenset({"entscheidsuche.ch"})

USER_AGENT = "swiss-courts-mcp/0.2.0"


class EgressNotAllowedError(RuntimeError):
    """Ziel-Host steht nicht auf der Egress-Allow-List."""


def assert_host_allowed(url: str) -> None:
    """Validiert Schema (HTTPS) und Host gegen die Allow-List (SEC-004, SEC-021).

    Wird vor jedem ausgehenden Request aufgerufen. Da nur ein fester Host
    erlaubt ist, begrenzt das zugleich die DNS-Rebinding-Fläche (SEC-005).
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise EgressNotAllowedError(f"Nur HTTPS erlaubt, nicht {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise EgressNotAllowedError(f"Host {host!r} nicht auf der Egress-Allow-List")

# Mapping: Spider-Prefix → Gerichts-Hierarchie für Filter
COURT_LEVEL_PREFIXES = {
    "bundesgericht": ["CH_BGer", "CH_BGE"],
    "bundesverwaltungsgericht": ["CH_BVGE"],
    "bundesstrafgericht": ["CH_BSTG"],
    "bundespatentgericht": ["CH_PATG"],
}


# ---------------------------------------------------------------------------
# Query-Builder
# ---------------------------------------------------------------------------


def build_search_body(
    query: str | None = None,
    canton: str | None = None,
    court_level: str | None = None,
    court_prefixes: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    size: int = 20,
    offset: int = 0,
) -> dict:
    """Baut den Elasticsearch-Request-Body aus den Suchparametern."""
    body: dict = {
        "size": min(size, MAX_SIZE),
        "from": offset,
        "sort": [{"date": {"order": "desc"}}],
    }

    must_clauses: list[dict] = []
    filter_clauses: list[dict] = []

    # Volltextsuche
    if query:
        must_clauses.append({
            "simple_query_string": {
                "query": query,
                "default_operator": "and",
            }
        })

    # Kantons-Filter (über hierarchy-Feld)
    if canton:
        filter_clauses.append({"term": {"hierarchy.keyword": canton}})

    # Gerichts-Ebene oder spezifische Prefixes
    prefixes = court_prefixes or (
        COURT_LEVEL_PREFIXES.get(court_level, []) if court_level else []
    )
    if prefixes:
        # Mehrere Prefixes → should (OR)
        prefix_clauses = [{"prefix": {"_id": p}} for p in prefixes]
        if len(prefix_clauses) == 1:
            filter_clauses.append(prefix_clauses[0])
        else:
            filter_clauses.append({
                "bool": {"should": prefix_clauses, "minimum_should_match": 1}
            })

    # Datumsbereich
    if date_from or date_to:
        range_filter: dict = {}
        if date_from:
            range_filter["gte"] = date_from
        if date_to:
            range_filter["lte"] = date_to
        filter_clauses.append({"range": {"date": range_filter}})

    # Query zusammenbauen
    if must_clauses or filter_clauses:
        bool_query: dict = {}
        if must_clauses:
            bool_query["must"] = must_clauses
        if filter_clauses:
            bool_query["filter"] = filter_clauses
        body["query"] = {"bool": bool_query}
    else:
        body["query"] = {"match_all": {}}

    return body


def build_id_query(signature: str) -> dict:
    """Baut Query für exakten ID-Lookup."""
    return {
        "query": {"term": {"_id": signature}},
        "size": 1,
    }


# ---------------------------------------------------------------------------
# Gesetzesreferenz-Parser
# ---------------------------------------------------------------------------

# Pattern: "Art. 8 BV", "Art. 328 OR", "§ 123 StGB", "Art. 25 Abs. 1 DSG"
_LAW_REF_PATTERN = re.compile(
    r"(?:Art\.?|Artikel|§)\s*"          # Prefix: Art., Artikel, §
    r"(\d+[a-z]?)"                      # Artikelnummer (z.B. 8, 328, 25a)
    r"(?:\s+(?:Abs\.?\s*\d+))?"         # Optional: Abs. 1
    r"(?:\s+(?:lit\.?\s*[a-z]))?"       # Optional: lit. a
    r"(?:\s+(?:Ziff\.?\s*\d+))?"        # Optional: Ziff. 1
    r"\s+"
    r"([A-ZÄÖÜa-zäöü]{2,})",           # Gesetzeskürzel (BV, OR, DSG, StGB)
    re.IGNORECASE,
)


def parse_law_reference(ref: str) -> dict:
    """Zerlegt eine Gesetzesreferenz in Bestandteile.

    Returns:
        Dict mit 'article', 'law', 'original'. Felder können leer sein
        wenn das Parsing fehlschlägt.
    """
    match = _LAW_REF_PATTERN.search(ref)
    if match:
        return {
            "article": match.group(1),
            "law": match.group(2),
            "original": ref,
        }
    return {"article": "", "law": "", "original": ref}


def build_law_reference_body(
    law_reference: str,
    date_from: str | None = None,
    date_to: str | None = None,
    size: int = 20,
    offset: int = 0,
) -> dict:
    """Baut eine mehrstufige Suche für Gesetzesreferenzen.

    Strategie (Elasticsearch bool/should mit Boost):
    1. Exakte Phrase "Art. 8 BV" (höchster Boost) → findet exakte Nennungen
    2. Artikelnummer + Kürzel nahe beieinander (mittlerer Boost) → findet Varianten
    3. Nur Gesetzeskürzel als Kontext (niedriger Boost) → breitere Abdeckung
    """
    body: dict = {
        "size": min(size, MAX_SIZE),
        "from": offset,
        "sort": [{"_score": {"order": "desc"}}, {"date": {"order": "desc"}}],
    }

    parsed = parse_law_reference(law_reference)
    should_clauses: list[dict] = []

    # 1. Exakte Phrase (höchster Boost)
    should_clauses.append({
        "simple_query_string": {
            "query": f"\"{law_reference}\"",
            "default_operator": "and",
            "boost": 10,
        }
    })

    # 2. Wenn geparst: Artikelnummer + Kürzel (mittlerer Boost)
    if parsed["article"] and parsed["law"]:
        # Varianten: "Art. 8" + "BV", "Artikel 8" + "BV", etc.
        should_clauses.append({
            "simple_query_string": {
                "query": f"{parsed['article']} {parsed['law']}",
                "default_operator": "and",
                "boost": 3,
            }
        })

    # 3. Nur Gesetzeskürzel (niedriger Boost, für Kontext)
    if parsed["law"]:
        should_clauses.append({
            "simple_query_string": {
                "query": f"\"{parsed['law']}\"",
                "default_operator": "and",
                "boost": 1,
            }
        })

    # Bool-Query: mindestens eine Klausel muss matchen
    bool_query: dict = {
        "should": should_clauses,
        "minimum_should_match": 1,
    }

    # Datumsfilter
    filter_clauses: list[dict] = []
    if date_from or date_to:
        range_filter: dict = {}
        if date_from:
            range_filter["gte"] = date_from
        if date_to:
            range_filter["lte"] = date_to
        filter_clauses.append({"range": {"date": range_filter}})

    if filter_clauses:
        bool_query["filter"] = filter_clauses

    body["query"] = {"bool": bool_query}
    return body


# ---------------------------------------------------------------------------
# HTTP-Funktionen
# ---------------------------------------------------------------------------


def new_client() -> httpx.AsyncClient:
    """Erstellt einen konfigurierten httpx-Client.

    Wird vom Lifespan (SDK-001) einmalig erzeugt und über den Server-Kontext
    allen Tool-Calls bereitgestellt. Kein Client-Aufbau pro Request mehr.
    """
    # Kein globaler "Content-Type": Als Client-Default würde er auch GET-Requests
    # (z.B. die Facetten/Taxonomie als statische .json-Datei) ohne Body mit
    # "Content-Type: application/json" versehen. Das WAF/CDN von entscheidsuche.ch
    # quittiert solche bodylosen, aber Content-Type-deklarierenden GETs mit
    # HTTP 415 (Unsupported Media Type). httpx setzt den Content-Type beim POST
    # ohnehin automatisch pro Request über `json=`. Zusätzlich signalisiert
    # "Accept: application/json" explizit das gewünschte Antwortformat (statt des
    # httpx-Defaults "*/*", der WAF-Bot-Mitigation triggern kann).
    return httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )


class _TransientClient:
    """Fallback-Context-Manager, wenn kein gepoolter Client übergeben wird.

    Hält den Code rückwärtskompatibel (z.B. Live-Tests, die die HTTP-Funktionen
    direkt ohne Client aufrufen).
    """

    def __init__(self, client: httpx.AsyncClient | None) -> None:
        self._provided = client
        self._owned: httpx.AsyncClient | None = None

    async def __aenter__(self) -> httpx.AsyncClient:
        if self._provided is not None:
            return self._provided
        self._owned = new_client()
        return self._owned

    async def __aexit__(self, *exc) -> None:
        if self._owned is not None:
            await self._owned.aclose()


async def search_decisions(body: dict, client: httpx.AsyncClient | None = None) -> dict:
    """POST-Suche an entscheidsuche.ch mit Elasticsearch-Body."""
    assert_host_allowed(SEARCH_URL)
    async with _TransientClient(client) as http:
        response = await http.post(SEARCH_URL, json=body)
        response.raise_for_status()
        return response.json()


async def get_decision_by_id(
    signature: str, client: httpx.AsyncClient | None = None
) -> dict | None:
    """Einzelnen Entscheid anhand der Signatur abrufen."""
    body = build_id_query(signature)
    result = await search_decisions(body, client=client)
    hits = result.get("hits", {}).get("hits", [])
    return hits[0] if hits else None


async def get_court_taxonomy(client: httpx.AsyncClient | None = None) -> dict:
    """Gerichts-Taxonomie (Facetten) abrufen."""
    assert_host_allowed(FACETS_URL)
    async with _TransientClient(client) as http:
        response = await http.get(FACETS_URL)
        response.raise_for_status()
        return response.json()


async def get_decision_document_url(signature: str, fmt: str = "json") -> str:
    """Generiert die Dokument-URL für einen Entscheid."""
    # Spider-Prefix aus der Signatur extrahieren
    # Format: CH_BGer_005_5F-23-2025_2025-07-01
    parts = signature.split("_")
    if len(parts) >= 2:
        spider = "_".join(parts[:2])  # z.B. "CH_BGer"
        if len(parts) >= 3 and parts[0] == "CH":
            spider = "_".join(parts[:2])
        else:
            spider = parts[0]
    else:
        spider = parts[0]
    return f"{DOCS_BASE}/{spider}/{signature}.{fmt}"


# ---------------------------------------------------------------------------
# Ergebnis-Extraktion
# ---------------------------------------------------------------------------


def extract_hit(hit: dict, lang: str = "de") -> dict:
    """Extrahiert die relevanten Felder aus einem Elasticsearch-Hit."""
    source = hit.get("_source", {})
    hierarchy = source.get("hierarchy", [])

    # Titel und Abstract in gewünschter Sprache
    title_obj = source.get("title", {})
    abstract_obj = source.get("abstract", {})
    title = title_obj.get(lang) or title_obj.get("de") or next(iter(title_obj.values()), "")
    abstract = (
        abstract_obj.get(lang)
        or abstract_obj.get("de")
        or next(iter(abstract_obj.values()), "")
    )

    references = source.get("reference", [])
    if isinstance(references, str):
        references = [references]

    return {
        "signature": hit.get("_id", ""),
        "date": source.get("date", ""),
        "court": hierarchy[1] if len(hierarchy) > 1 else (hierarchy[0] if hierarchy else ""),
        "canton": hierarchy[0] if hierarchy else "",
        "references": references,
        "title": title,
        "abstract": abstract,
        "language": source.get("attachment", {}).get("language", ""),
        "url": f"https://entscheidsuche.ch/docs/{hit.get('_id', '')}.html",
    }


def extract_total(result: dict) -> int:
    """Gesamtzahl der Treffer aus dem ES-Response."""
    total = result.get("hits", {}).get("total", 0)
    if isinstance(total, dict):
        return total.get("value", 0)
    return total


# ---------------------------------------------------------------------------
# Fehlerbehandlung
# ---------------------------------------------------------------------------


def handle_error(e: Exception) -> str:
    """Einheitliche, handlungsweisende Fehlermeldungen.

    Maskiert interne Details (OBS-002): an den Client/das LLM geht nur eine
    benutzerfreundliche Meldung ohne Stacktrace, Exception-Repr oder Internals.
    Der Originalfehler wird ausschliesslich serverseitig geloggt.
    """
    if isinstance(e, EgressNotAllowedError):
        log.error("egress_blocked", error=str(e))
        return "Fehler: Ziel-Adresse ist nicht erlaubt (Egress-Policy)."
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        log.warning("upstream_http_error", status_code=code)
        if code == 400:
            return "Fehler: Ungültige Suchabfrage (HTTP 400). Suchparameter überprüfen."
        if code == 429:
            return "Fehler: Rate Limit erreicht. Bitte kurz warten und erneut versuchen."
        if code == 503:
            return "Fehler: entscheidsuche.ch vorübergehend nicht verfügbar."
        return f"Fehler: HTTP {code} von entscheidsuche.ch."
    if isinstance(e, (httpx.TimeoutException, httpx.ReadTimeout)):
        log.warning("upstream_timeout")
        return (
            "Fehler: Timeout bei entscheidsuche.ch. "
            "Komplexe Suchen können länger dauern — bitte erneut versuchen."
        )
    if isinstance(e, httpx.ConnectError):
        log.warning("upstream_connect_error")
        return "Fehler: Verbindung zu entscheidsuche.ch fehlgeschlagen. Internetverbindung prüfen."
    # Unerwarteter Fehler: Details NUR ins Server-Log, nicht an den Client.
    log.error("unexpected_error", error_type=type(e).__name__, exc_info=e)
    return "Fehler: Interner Fehler bei der Verarbeitung der Anfrage."
