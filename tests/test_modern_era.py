"""Die Modern-Ära (Spec `2026-07-28`) am Draht nachgemessen.

`tests/test_protocol.py` prüft die Legacy-Ära: ein `initialize` mit
`protocolVersion: "2026-07-28"` bekommt `2025-11-25` zurück. Aus diesem einen
Befund war geschlossen worden, der Server spreche `2026-07-28` nicht — und die
README sagte es so. Der Handshake ist bloss der falsche Weg dorthin: Spec
`2026-07-28` hat ihn abgeschafft und durch einen Per-Request-Envelope ersetzt.

Dieselbe Falle wie `lotId` in `swiss-procurement-mcp`: ein deterministischer
Fehlschlag auf dem einen Pfad ist keine Auskunft über den anderen. Hier ist der
andere Pfad ein POST mit `_meta`-Envelope und den Routing-Headern — und darauf
antwortet dieser Server mit 200. Der SDK-eigene Client wählt genau diesen Pfad
(`test_der_sdk_client_landet_auf_der_modern_aera`), er ist also nicht der
exotische, sondern der übliche.

Geprüft wird durch den zusammengebauten ASGI-Stack, nicht am Handler: die Ära
entscheidet sich im Transport (`mcp.shared.inbound`), und ein direkt gerufener
Handler kann nicht zeigen, welche Ära eine HTTP-Anfrage erreicht.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
    SERVER_INFO_META_KEY,
)
from mcp_types.jsonrpc import (
    HEADER_MISMATCH,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    UNSUPPORTED_PROTOCOL_VERSION,
)
from starlette.testclient import TestClient

from swiss_courts_mcp import __homepage__, __version__
from swiss_courts_mcp.config import Settings
from swiss_courts_mcp.server import (
    LIST_CACHE_TTL_MS,
    MODERN_PROTOCOL_VERSION,
    SERVER_TITLE,
    build_http_app,
    create_mcp,
    mcp,
)

HOST = "127.0.0.1:8000"

# Sentinel: «Header nicht überschrieben» ist nicht dasselbe wie «Header weglassen».
_UNSET: Any = object()


@pytest.fixture
def http() -> Any:
    """Der echte ASGI-Stack dieses Servers, einmal pro Test."""
    server = create_mcp(Settings(host="127.0.0.1", port=8000), http=True)
    with TestClient(server.streamable_http_app(host="127.0.0.1")) as client:
        yield client


def _envelope(version: str = MODERN_PROTOCOL_VERSION) -> dict[str, Any]:
    """Der Per-Request-Envelope, den Spec `2026-07-28` in `params._meta` verlangt.

    `clientInfo` ist ein SHOULD und darf fehlen; die beiden anderen Schlüssel
    sind Pflicht — ohne sie antwortet das SDK mit -32602, noch vor jeder
    Versionsfrage.
    """
    return {
        PROTOCOL_VERSION_META_KEY: version,
        CLIENT_CAPABILITIES_META_KEY: {},
        CLIENT_INFO_META_KEY: {"name": "modern-test-client", "version": "1"},
    }


def _post(
    client: TestClient,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    name: str | None = None,
    version: str = MODERN_PROTOCOL_VERSION,
    header_version: str | None = _UNSET,
    header_method: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Eine Modern-Anfrage; liefert (HTTP-Status, JSON-Body).

    `header_version` / `header_method` überschreiben nur den Header, nicht den
    Körper — damit ist die Header-Prüfung des SDK überhaupt auslösbar.
    `header_version=None` lässt den Header ganz weg; ohne das Sentinel wäre
    «weglassen» von «nicht überschrieben» nicht zu unterscheiden, und der Test
    über den fehlenden Header prüfte in Wahrheit den gesetzten.
    """
    body_params = dict(params or {})
    body_params["_meta"] = _envelope(version)
    headers = {
        "Host": HOST,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Method": header_method if header_method is not None else method,
    }
    effective_version = version if header_version is _UNSET else header_version
    if effective_version is not None:
        headers["MCP-Protocol-Version"] = effective_version
    if name is not None:
        headers["Mcp-Name"] = name
    response = client.post(
        "/mcp",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": body_params},
    )
    payload = response.text
    for line in payload.splitlines():  # SSE-Framing abziehen, falls committet
        if line.startswith("data: "):
            payload = line[len("data: ") :]
    return response.status_code, json.loads(payload)


# ---------------------------------------------------------------------------
# Der tragende Befund
# ---------------------------------------------------------------------------


async def test_der_sdk_client_landet_auf_der_modern_aera() -> None:
    """Der übliche Weg, nicht der exotische.

    `mcp.Client` probt `server/discover` und fällt nur bei Ablehnung auf den
    Handshake zurück. Gegen diesen Server fällt er nicht zurück — die Aussage
    «dieser Server pinnt 2025-11-25» beschrieb also die Ära, in der seine
    Clients gerade *nicht* sprechen.

    Pinnt SDK-Verhalten, nicht eigenen Code: an dieser Stelle gibt es nichts zu
    neutralisieren. Sie steht hier, weil die README-Aussage darauf ruht.
    """
    async with Client(mcp) as client:
        assert client.protocol_version == MODERN_PROTOCOL_VERSION


def test_discover_antwortet_und_nennt_die_gepinnte_revision(http: TestClient) -> None:
    status, body = _post(http, "server/discover")

    assert status == 200, body
    result = body["result"]
    assert result["supportedVersions"] == [MODERN_PROTOCOL_VERSION]
    # Spec 2026-07-28: `resultType` ist Pflicht — ein Client ohne das Feld muss
    # «complete» annehmen, und diese Rückwärtsbrücke gilt nur für ältere Server.
    assert result["resultType"] == "complete"
    assert "entscheidsuche.ch" in result["instructions"]


# ---------------------------------------------------------------------------
# Die Server-Identität, die es in dieser Ära nur noch hier gibt
# ---------------------------------------------------------------------------


def _server_info(body: dict[str, Any]) -> dict[str, Any]:
    return body["result"]["_meta"][SERVER_INFO_META_KEY]


def test_der_stempel_traegt_die_paketversion(http: TestClient) -> None:
    """Der gemessene Fehlbefund, der diese Änderung ausgelöst hat.

    `MCPServer(version=...)` defaultet auf den Leerstring, und `create_mcp`
    übergab nichts: `server/discover` antwortete mit `"version": ""`. In der
    Handshake-Ära reiste `serverInfo` einmal im `initialize`-Resultat; in der
    Modern-Ära gibt es keinen Handshake — der Stempel am `_meta` jeder Antwort
    ist die einzige Stelle, an der ein Client den Build erfährt.
    """
    _, body = _post(http, "server/discover")

    assert _server_info(body)["version"] == __version__
    assert __version__ != ""


async def test_ein_server_ohne_version_stempelt_den_leerstring() -> None:
    """Negativkontrolle zum Test darüber: gleiches SDK, kein `version=`.

    Ohne sie könnte der Test oben auch dann grün sein, wenn das SDK die Version
    von sich aus aus den Paket-Metadaten zöge — dann prüfte er nicht mehr, dass
    *wir* sie setzen.
    """
    async with Client(MCPServer("kontrolle")) as client:
        assert client.server_info is not None
        assert client.server_info.version == ""


def test_der_stempel_traegt_den_anzeigenamen(http: TestClient) -> None:
    """`title` — dasselbe Argument wie bei der Version.

    `name` ist der Programm-Name (`swiss_courts_mcp`), den ein Host nur als
    Rückfallebene zeigt; `title` ist das, was ein Mensch lesen soll. Dass die
    beiden auseinandergehen, ist der Punkt — sonst wäre das Feld überflüssig.
    """
    info = _server_info(_post(http, "server/discover")[1])

    assert info["title"] == SERVER_TITLE
    assert info["title"] != info["name"]


def test_der_stempel_traegt_die_projekt_url(http: TestClient) -> None:
    """`websiteUrl` aus `[project.urls] Homepage`, nicht aus einem Literal.

    Eigener Test statt einer zweiten Zusicherung im Test darüber: sonst fiele
    bei einer Neutralisierung nicht erkennbar, welches der beiden Felder fehlt.
    """
    info = _server_info(_post(http, "server/discover")[1])

    assert __homepage__ is not None
    assert info["websiteUrl"] == __homepage__


def test_die_projekt_url_stimmt_mit_dem_registry_manifest_ueberein() -> None:
    """`server.json` nennt dieselbe Adresse — und nichts erzwang das bisher.

    `scripts/check_version_sync.py` hält nur die *Versions*-Wiederholungen nach.
    Die URL steht in `pyproject.toml` (Quelle des Stempels) und in `server.json`
    (Quelle für die MCP-Registry); driften sie auseinander, sagt der Server auf
    dem Draht etwas anderes als sein Manifest.
    """
    manifest = json.loads(
        (pathlib.Path(__file__).resolve().parent.parent / "server.json").read_text(encoding="utf-8")
    )

    assert manifest["websiteUrl"] == __homepage__


def test_der_stempel_bleibt_ohne_zweckbeschreibung(http: TestClient) -> None:
    """Bewusste Auslassung, damit sie nicht als Versehen nachgetragen wird.

    Der Stempel hängt an JEDER Antwort dieser Ära. Die Zweckbeschreibung steht
    in `instructions`, und die reist einmalig in `server/discover` — ein
    zweites Mal dasselbe pro Antwort wäre Bytes ohne Empfänger.
    """
    assert "description" not in _server_info(_post(http, "server/discover")[1])


# ---------------------------------------------------------------------------
# Die Primitive dieser Ära
# ---------------------------------------------------------------------------


def test_die_werkzeugliste_kommt_mit_frischehinweis_durch(http: TestClient) -> None:
    """SEP-2549 am HTTP-Draht, nicht nur am In-Memory-Client.

    `tests/test_cache_hints.py` prüft dieselben Felder über `mcp.Client`. Dort
    hängt die Ära an der Aushandlung des SDK; hier steht sie im Request, und
    nur so ist gezeigt, dass der Hinweis auch den Transport übersteht.
    """
    status, body = _post(http, "tools/list")

    assert status == 200, body
    assert body["result"]["ttlMs"] == LIST_CACHE_TTL_MS
    assert body["result"]["cacheScope"] == "public"
    assert [tool["name"] for tool in body["result"]["tools"]]


def test_ein_werkzeugaufruf_laeuft_in_dieser_aera(http: TestClient) -> None:
    """Der Envelope reicht bis in den Tool-Handler.

    `get_fallback_status` ist der einzige Aufruf, der ohne Netz auskommt: er
    liest den lokalen Cache-Zustand. Ein Tool, das entscheidsuche.ch abfragt,
    würde hier die Quelle prüfen und nicht die Ära.
    """
    status, body = _post(
        http,
        "tools/call",
        {"name": "get_fallback_status", "arguments": {"params": {}}},
        name="get_fallback_status",
    )

    assert status == 200, body
    assert "Offline-Fallback" in body["result"]["content"][0]["text"]
    assert body["result"]["structuredContent"]["status"]["dataset"]
    # Spec 2026-07-28: `resultType` ist Pflicht. Dieser Server baut sein
    # `CallToolResult` von Hand (`_result()`, `structured_output=False`) — das
    # Feld kommt hier also nicht aus einem SDK-generierten Resultat, sondern
    # aus der Sieb-Schicht, die ein handgebautes nachträglich ergänzt.
    assert body["result"]["resultType"] == "complete"


def test_ein_prompt_laeuft_in_dieser_aera(http: TestClient) -> None:
    """Zweites Primitiv (ARCH-008), damit die Ära nicht nur für Tools gemessen ist."""
    status, body = _post(
        http,
        "prompts/get",
        {"name": "rechtsrecherche", "arguments": {"thema": "Mietrecht"}},
        name="rechtsrecherche",
    )

    assert status == 200, body
    assert "Mietrecht" in body["result"]["messages"][0]["content"]["text"]


# ---------------------------------------------------------------------------
# Die Ära-Grenze
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method",
    ["initialize", "ping", "logging/setLevel", "resources/subscribe", "resources/unsubscribe"],
)
def test_was_diese_aera_abgeschafft_hat_ist_hier_nicht_erreichbar(
    http: TestClient, method: str
) -> None:
    """Die Grenze ist echt, nicht bloss dokumentiert.

    Spec `2026-07-28` kennt weder `initialize` noch `ping`, `logging/setLevel`
    oder das `resources/subscribe`-Paar (`mcp_types.methods`). Antwortete der
    Server hier trotzdem, wäre die Ära nur halb umgesetzt — und ein Client
    dürfte sich auf Mechanik stützen, die die Spec entfernt hat.

    Kein Fehlbefund über den Server: `ping` ist in der Legacy-Ära weiterhin da,
    was `tests/test_protocol.py` mit seinen `initialize`-Aufrufen belegt.
    """
    status, body = _post(http, method)

    assert status == 404, body
    assert body["error"]["code"] == METHOD_NOT_FOUND


def test_eine_unbekannte_revision_wird_benannt_abgelehnt(http: TestClient) -> None:
    """Deterministische Absage mit Statusangabe — kein «später erneut versuchen».

    Die Antwort nennt, was der Server kann, und was angefragt wurde. Genau das
    fehlte in `swiss-procurement-mcp`, wo aus einem 400 ein «Quelle nicht
    erreichbar» wurde.
    """
    status, body = _post(http, "tools/list", version="2099-01-01")

    assert status == 400, body
    assert body["error"]["code"] == UNSUPPORTED_PROTOCOL_VERSION
    assert body["error"]["data"]["supported"] == [MODERN_PROTOCOL_VERSION]
    assert body["error"]["data"]["requested"] == "2099-01-01"


@pytest.mark.parametrize(
    ("kwargs", "was"),
    [
        # Eine dem Server unbekannte Revision im Header: die Header-Sprosse des
        # SDK läuft VOR der Versions-Sprosse, ein Client, der sich selbst
        # widerspricht, hört das also und nicht «Revision nicht unterstützt».
        ({"header_version": "2099-01-01"}, "Version"),
        ({"header_method": "prompts/list"}, "Methode"),
    ],
)
def test_ein_client_der_sich_selbst_widerspricht_wird_abgewiesen(
    http: TestClient, kwargs: dict[str, str], was: str
) -> None:
    """Header und Körper müssen übereinstimmen (Spec `2026-07-28`, Routing).

    Ein Gateway routet nach den Headern, der Server antwortet nach dem Körper.
    Gingen die auseinander, entschieden zwei Stellen verschieden über dieselbe
    Anfrage. Deshalb ist der Widerspruch ein eigener Fehlercode und nicht
    einfach die Körper-Sicht.
    """
    status, body = _post(http, "tools/list", **kwargs)

    assert status == 400, body
    assert body["error"]["code"] == HEADER_MISMATCH, was


@pytest.mark.parametrize("header_version", [None, "2025-11-25"])
def test_der_header_waehlt_die_aera_nicht_der_envelope(
    http: TestClient, header_version: str | None
) -> None:
    """Die Falle, die aus dieser Änderung einen Fehlbefund machen könnte.

    Fehlt `MCP-Protocol-Version` oder nennt er eine Handshake-Revision, landet
    die Anfrage im Legacy-Transport — dort fehlt ihr die Session, und die
    Antwort lautet «Missing session ID» (-32600). Der Modern-Envelope im Körper
    ändert daran nichts, und die Fehlermeldung erwähnt ihn nicht.

    Wer daraus schliesst, der Server spreche `2026-07-28` nicht, wiederholt
    genau den Fehler, gegen den diese Datei geschrieben ist: nicht aus der
    Fehlermeldung schliessen, sondern den anderen Pfad abfragen.
    """
    status, body = _post(http, "tools/list", header_version=header_version)

    assert status == 400, body
    assert body["error"]["code"] == INVALID_REQUEST
    assert "session" in body["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Was in der neuen Ära weitergelten muss
# ---------------------------------------------------------------------------


def _modern_post_under_host(settings: Settings, host_header: str) -> int:
    """Eine Modern-`tools/list`-Anfrage unter `host_header`; HTTP-Status.

    Baut die App je Aufruf neu: der `StreamableHTTPSessionManager` einer App
    läuft nur einmal, zwei Anfragen an dieselbe Instanz enden im
    `RuntimeError` statt in einem Statuscode.
    """
    with TestClient(build_http_app(settings)) as client:
        response = client.post(
            "/mcp",
            headers={
                "Host": host_header,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": MODERN_PROTOCOL_VERSION,
                "Mcp-Method": "tools/list",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {"_meta": _envelope()},
            },
        )
    return response.status_code


# Nicht-Loopback-Bind mit Allow-List: nur so stammt die Host-Prüfung aus
# `build_transport_security` und nicht aus der Loopback-Liste, die das SDK bei
# einem 127.0.0.1-Bind von sich aus scharfschaltet. Mit der SDK-Liste wäre der
# Test unten auch dann grün, wenn unsere Schicht nie zum Einsatz käme.
_PINNED = Settings(
    host="0.0.0.0",  # noqa: S104 — Container-Szenario
    allowed_hosts=["mcp.example.ch"],
)


def test_der_host_schutz_gilt_auch_auf_dem_modern_pfad() -> None:
    """SEC-005 überlebt den Ära-Wechsel.

    Ein neuer Transportpfad ist die klassische Stelle, an der eine
    Schutzschicht danebenliegt: der DNS-Rebinding-Schutz hängt an einer
    Middleware, der Envelope wird in einem anderen Modul klassifiziert. Ohne
    diese Zusicherung wäre eine Lücke genau dort unsichtbar, wo sie niemand
    vermutet.

    Positivkontrolle im selben Test: der erlaubte Name kommt durch. Ein blosses
    421 könnte auch von einer Allow-List stammen, die alles abweist — dann
    prüfte der Test nicht den Schutz, sondern einen kaputten Server.
    """
    assert _modern_post_under_host(_PINNED, "mcp.example.ch") == 200
    assert _modern_post_under_host(_PINNED, "angreifer.example") == 421


def test_ohne_unsere_allow_list_prueft_das_sdk_den_host_nicht(monkeypatch) -> None:
    """Gegenprobe zum Test darüber, an genau der Zeile, die ihn tragen soll.

    `build_transport_security` liefert bewusst `None`, wenn keine Allow-List
    ableitbar ist — das SDK lässt den Host-Header dann ungeprüft (sein eigener
    Kommentar: «disable DNS rebinding protection by default for backwards
    compatibility»). Neutralisiert man die Funktion, kommt der fremde Host
    durch: der Test oben misst also unsere Schicht und nicht die des SDK.
    """
    monkeypatch.setattr("swiss_courts_mcp.server.build_transport_security", lambda _s: None)

    assert _modern_post_under_host(_PINNED, "angreifer.example") == 200
