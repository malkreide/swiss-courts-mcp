"""Security-Tests: Egress-Allow-List (SEC-021), Auth (SEC-009), Config (SEC-016)."""

from __future__ import annotations

import time
import warnings

import pytest
from mcp.shared.exceptions import MCPDeprecationWarning
from starlette.testclient import TestClient
from structlog.testing import capture_logs

from swiss_courts_mcp import api_client
from swiss_courts_mcp.api_client import EgressNotAllowedError, assert_host_allowed
from swiss_courts_mcp.auth import AuthConfigError, JWTTokenVerifier, issue_dev_token
from swiss_courts_mcp.config import Settings
from swiss_courts_mcp.server import _build_auth, _public_url, build_http_app

# --- SEC-021 / SEC-004: Egress-Allow-List ---


def test_allowed_host_passes():
    assert_host_allowed("https://entscheidsuche.ch/_search.php")


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example.com/x",
        "http://entscheidsuche.ch/x",  # kein HTTPS
        "https://169.254.169.254/latest/meta",  # Cloud-Metadata
        "https://entscheidsuche.ch.evil.com/x",
    ],
)
def test_disallowed_targets_blocked(url):
    with pytest.raises(EgressNotAllowedError):
        assert_host_allowed(url)


def test_allowed_hosts_is_frozenset():
    assert isinstance(api_client.ALLOWED_HOSTS, frozenset)


# --- SEC-016: sicherer Bind-Default ---


def test_default_host_is_loopback(monkeypatch):
    for var in ("MCP_HOST", "MCP_PORT", "MCP_ALLOW_PUBLIC_BIND"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings.from_env()
    assert settings.host == "127.0.0.1"
    assert settings.allow_public_bind is False


# --- SEC-009: JWT-Token-Validierung ---


#: Der Resource-Identifier, auf den ein IdP Tokens fuer diesen Server bindet.
#: Seit dem Publikumszwang ist er in jedem Auth-Setup Pflicht.
AUDIENCE = "swiss-courts-mcp"

#: Der Issuer des IdP. Seit dem Issuerzwang ebenfalls Pflicht — ohne ihn
#: entsteht kein Verifier, weshalb `_settings` ihn vorbelegt.
ISSUER = "https://idp.example.ch"


def _settings(secret="test-secret-please-change-0123456789abcdef", **kw):
    kw.setdefault("oauth_audience", AUDIENCE)
    kw.setdefault("oauth_issuer", ISSUER)
    return Settings(auth_enabled=True, auth_secret=secret, **kw)


async def test_valid_token_accepted():
    s = _settings(required_scopes=["courts:read"])
    token = issue_dev_token(s, sub="user-123", scopes=["courts:read"])
    verifier = JWTTokenVerifier(s)
    access = await verifier.verify_token(token)
    assert access is not None
    assert access.client_id == "user-123"  # User-ID aus validiertem sub-Claim
    assert "courts:read" in access.scopes


async def test_expired_token_rejected():
    s = _settings()
    token = issue_dev_token(s, sub="u", ttl_seconds=-10)
    assert await JWTTokenVerifier(s).verify_token(token) is None


async def test_tampered_token_rejected():
    s = _settings()
    token = issue_dev_token(s, sub="u") + "x"
    assert await JWTTokenVerifier(s).verify_token(token) is None


async def test_wrong_secret_rejected():
    token = issue_dev_token(_settings(secret="secret-a-" + "0" * 32), sub="u")
    verifier = JWTTokenVerifier(_settings(secret="secret-b-" + "0" * 32))
    assert await verifier.verify_token(token) is None


async def test_insufficient_scope_rejected():
    s = _settings(required_scopes=["courts:read", "courts:admin"])
    token = issue_dev_token(s, sub="u", scopes=["courts:read"])
    assert await JWTTokenVerifier(s).verify_token(token) is None


def test_auth_enabled_without_credentials_raises():
    with pytest.raises(AuthConfigError):
        JWTTokenVerifier(Settings(auth_enabled=True, oauth_audience=AUDIENCE))


# --- SEC-009: Publikumsbindung (aud) ist Pflicht ---


def test_auth_enabled_without_audience_raises():
    """Ohne Publikum darf kein Verifier entstehen.

    Vorher hing `verify_aud` an `bool(oauth_audience)`: fehlte die Variable,
    schaltete sich die Pruefung selbst ab — lautlos, und der Server galt
    weiterhin als «Auth aktiviert».
    """
    with pytest.raises(AuthConfigError, match="MCP_OAUTH_AUDIENCE"):
        JWTTokenVerifier(Settings(auth_enabled=True, auth_secret="x" * 40, oauth_audience=None))


_WEGLASSEN = object()


def _token_for(audience: str | None, secret: str, issuer=_WEGLASSEN) -> str:
    """Ein korrekt signiertes Token mit frei waehlbarem `aud`- und `iss`-Claim.

    Nicht ueber `issue_dev_token`: das setzt beide Claims aus denselben
    Settings, mit denen der Verifier prueft, und koennte eine fremde Angabe
    deshalb gar nicht ausdruecken.

    `issuer` hat einen eigenen Weglass-Marker statt `None` als Default: sonst
    liesse sich «Claim ganz weg» nicht von «nicht ueberschrieben» trennen, und
    genau dieser Unterschied ist bei `iss` ein eigener Testfall. Vorbelegt ist
    der richtige Issuer, damit ein Test ueber das Publikum nicht am Issuer
    scheitert — sonst waere jede Ablehnung hier gruen, ohne dass der Grund
    stimmt.
    """
    import jwt

    now = int(time.time())
    claims: dict = {"sub": "u", "iat": now, "exp": now + 3600, "scope": ""}
    if audience is not None:
        claims["aud"] = audience
    if issuer is _WEGLASSEN:
        claims["iss"] = ISSUER
    elif issuer is not None:
        claims["iss"] = issuer
    return jwt.encode(claims, secret, algorithm="HS256")


async def test_token_fuer_fremde_resource_wird_abgelehnt():
    """Der Confused Deputy, den die Publikumspflicht schliesst.

    Derselbe Issuer (hier: dasselbe HS256-Secret) stellt ein Token fuer einen
    anderen Dienst aus. Ohne aud-Pruefung kam es hier durch — nachgemessen,
    bevor die Pflicht eingebaut wurde.

    Positivkontrolle im selben Test: das Token mit dem richtigen Publikum
    kommt durch. Sonst waere die Ablehnung auch mit einem Verifier gruen, der
    grundsaetzlich alles abweist.
    """
    s = _settings()
    verifier = JWTTokenVerifier(s)

    fremd = _token_for("https://ganz-anderer-dienst.example", s.auth_secret)
    assert await verifier.verify_token(fremd) is None

    eigen = _token_for(AUDIENCE, s.auth_secret)
    assert await verifier.verify_token(eigen) is not None


async def test_token_ohne_aud_claim_wird_abgelehnt():
    """Auch das Fehlen des Claims ist eine Ablehnung, nicht ein Durchlassen."""
    s = _settings()
    assert await JWTTokenVerifier(s).verify_token(_token_for(None, s.auth_secret)) is None


async def test_die_publikumspruefung_schaltet_sich_nicht_selbst_ab():
    """Zweite Schicht, eigenstaendig geprueft — und der Test fehlte zuerst.

    Die Gegenprobe deckte es auf: nimmt man den Konstruktor-Zwang UND das
    unbedingte `verify_aud` heraus, fiel nur der Zwang-Test. Die beiden Tests
    oben bauen ihre Settings immer mit Publikum, dort ist
    `bool(oauth_audience)` also ebenfalls True — sie koennen die alte,
    nachgiebige Fassung gar nicht widerlegen. Ein Test, der gruen bleibt, wenn
    man die Implementierung entfernt, prueft nichts.

    Darum wird das Publikum hier NACH dem Bauen entfernt, am Konstruktor
    vorbei: genau der Zustand, den die alte Fassung als «dann eben nicht
    pruefen» gelesen hat. Unbedingt geprueft wird ein Token fuer einen fremden
    Dienst weiterhin abgelehnt.
    """
    s = _settings()
    verifier = JWTTokenVerifier(s)
    fremd = _token_for("https://ganz-anderer-dienst.example", s.auth_secret)

    verifier.settings.oauth_audience = None

    assert await verifier.verify_token(fremd) is None

    # Und der Fall, der bis zum 19.9.2026 durchkam. `verify_aud: True` allein
    # traegt die Schicht nicht: `_validate_aud(audience=None)` wirft nur, wenn
    # das Token ein `aud` FUEHRT — gemessen und in der pyjwt-Quelle nachgelesen.
    # Ein Token ganz ohne `aud` wurde hier AKZEPTIERT. Den Riegel gegen den
    # fehlenden Erwartungswert in `_decode` neutralisiert man, und genau diese
    # Zusicherung faellt.
    ohne_aud = _token_for(None, s.auth_secret)
    assert await verifier.verify_token(ohne_aud) is None


def test_token_ttl_reflected_in_exp():
    s = _settings()
    token = issue_dev_token(s, sub="u", ttl_seconds=60)
    import jwt

    # `audience` muss mit: seit der Publikumspflicht traegt jedes Dev-Token ein
    # `aud`-Claim, und `jwt.decode` prueft es dann auch — ohne das Argument
    # scheitert dieser Test an `InvalidAudienceError` statt an der TTL.
    claims = jwt.decode(token, s.auth_secret, algorithms=["HS256"], audience=AUDIENCE)
    assert claims["exp"] - int(time.time()) <= 60


# --- SEC-009: Issuerbindung (iss) ist Pflicht ---


def test_auth_enabled_without_issuer_raises():
    """Ohne Issuer darf kein Verifier entstehen.

    Derselbe Zuschnitt wie beim Publikum, andere Seite des Tokens: `verify_iss`
    hing an `bool(oauth_issuer)`, fehlte die Variable, schaltete sich die
    Pruefung lautlos ab — und der Server galt weiterhin als «Auth aktiviert».
    """
    with pytest.raises(AuthConfigError, match="MCP_OAUTH_ISSUER"):
        JWTTokenVerifier(
            Settings(
                auth_enabled=True,
                auth_secret="x" * 40,
                oauth_audience=AUDIENCE,
                oauth_issuer=None,
            )
        )


async def test_token_von_fremdem_mandanten_wird_abgelehnt():
    """Der Confused Deputy, den die Issuerpflicht schliesst.

    Das Publikum allein reicht dafuer nicht. Teilen mehrere Mandanten eine
    JWKS-URL — der Normalfall bei einem gehosteten IdP —, ist die Signatur fuer
    alle gueltig, und ein Mandant koennte ein Token auf DIESES Publikum
    ausstellen. Nur `iss` trennt sie. Hier steht dasselbe HS256-Secret fuer
    dieselbe Lage, mit korrektem `aud`.

    Positivkontrolle im selben Test: das Token des richtigen Issuers kommt
    durch. Sonst waere die Ablehnung auch mit einem Verifier gruen, der
    grundsaetzlich alles abweist.
    """
    s = _settings()
    verifier = JWTTokenVerifier(s)

    fremd = _token_for(AUDIENCE, s.auth_secret, issuer="https://fremder-tenant.example")
    assert await verifier.verify_token(fremd) is None

    eigen = _token_for(AUDIENCE, s.auth_secret)
    assert await verifier.verify_token(eigen) is not None


async def test_token_ohne_iss_claim_wird_abgelehnt():
    """Auch das Fehlen des Claims ist eine Ablehnung — und `require` sagt das nicht.

    Im `options["require"]` von `_decode` steht kein `"iss"`. Die Ablehnung
    kommt von pyjwt selbst, das das Claim bei gesetztem `issuer` einfordert
    (`MissingRequiredClaimError`). Dieser Test ist der Grund, warum dort kein
    zweiter Pin derselben Tatsache steht: aendert pyjwt das Verhalten, faellt
    hier ein Test statt still ein Token durchzukommen.
    """
    s = _settings()
    ohne_iss = _token_for(AUDIENCE, s.auth_secret, issuer=None)
    assert await JWTTokenVerifier(s).verify_token(ohne_iss) is None


async def test_die_issuerpruefung_schaltet_sich_nicht_selbst_ab():
    """Zweite Schicht, eigenstaendig geprueft — wie beim Publikum.

    Die Gegenprobe verlangt es: nimmt man den Konstruktor-Zwang UND das
    unbedingte `verify_iss` heraus, fiel nur der Zwang-Test. Alle Tests oben
    bauen ihre Settings mit Issuer, dort ist `bool(oauth_issuer)` also ebenfalls
    True — sie koennen die alte, nachgiebige Fassung gar nicht widerlegen.

    Darum wird der Issuer hier NACH dem Bauen entfernt, am Konstruktor vorbei:
    genau der Zustand, den die alte Fassung als «dann eben nicht pruefen»
    gelesen hat.

    Dieser Test hat beim Schreiben etwas aufgedeckt, das die Messung vorher
    nicht hatte: `verify_iss: True` traegt die Schicht NICHT. Er war zuerst rot,
    und zwar zu Recht — `_validate_iss(issuer=None)` kehrt in pyjwt 2.14.0 in
    der ersten Zeile zurueck, das fremde Token kam also durch. Getragen wird die
    Zusicherung erst vom Riegel in `_decode`, der einen fehlenden
    Erwartungswert als Ablehnung liest. Neutralisiert man ihn, faellt dieser
    Test — das Flag rettet ihn nicht.
    """
    s = _settings()
    verifier = JWTTokenVerifier(s)
    fremd = _token_for(AUDIENCE, s.auth_secret, issuer="https://fremder-tenant.example")

    verifier.settings.oauth_issuer = None

    assert await verifier.verify_token(fremd) is None


def test_build_auth_ohne_issuer_meldet_die_variable():
    """Die Reihenfolge in `_build_auth` — und sie war ungeprueft.

    Die Gegenprobe deckte es auf: ersetzt man `issuer_url=settings.oauth_issuer`
    wieder durch `... or base`, bleibt die ganze Suite gruen. Der Rueckfall ist
    unerreichbar, und genau darum ist er weg — aber «unerreichbar» ist selbst
    eine Zusicherung, und die haengt daran, dass der Verifier VOR dem
    `AuthSettings` gebaut wird.

    Steht er dahinter, scheitert `_build_auth` an `issuer_url=None` mit einem
    Pydantic-Fehler, der von Feldnamen des SDK spricht statt von der Variable,
    die der Betreiber setzen muss. Dieser Test haelt deshalb nicht bloss das
    Scheitern, sondern die Fehlerklasse und die genannte Variable fest.
    """
    ohne_issuer = Settings(
        auth_enabled=True, auth_secret="x" * 40, oauth_audience=AUDIENCE, oauth_issuer=None
    )

    with pytest.raises(AuthConfigError, match="MCP_OAUTH_ISSUER"):
        _build_auth(ohne_issuer)


async def test_ein_schraegstrich_am_iss_claim_ist_ein_anderer_issuer():
    """Der Issuer wird NICHT normalisiert, anders als die Resource-URL.

    `_public_url` schneidet bei `MCP_RESOURCE_URL` einen abschliessenden
    Schraegstrich ab. Beim Issuer waere dasselbe ein Fehler: RFC 8414/9207
    vergleichen zeichengleich, und manche IdP stellen `iss` mit Schraegstrich
    aus. Ein `rstrip` machte deren Tokens ungueltig — dieser Test haelt fest,
    dass der Vergleich exakt ist, und damit auch, dass das Weglassen der
    Normalisierung eine Entscheidung und kein Versehen war.
    """
    s = _settings()
    mit_schraegstrich = _token_for(AUDIENCE, s.auth_secret, issuer=ISSUER + "/")
    assert await JWTTokenVerifier(s).verify_token(mit_schraegstrich) is None


# --- SEC-009: `validate_token_resource` ist ausdruecklich entschieden ---


def _auth_stack_settings() -> Settings:
    """Loopback-Auth-Setup, wie `build_http_app` es verdrahtet."""
    return _settings(host="127.0.0.1", port=8000)


def test_die_resource_pruefung_steht_ausdruecklich_auf_false():
    """Ungesetzt ist keine Entscheidung, sondern eine verschobene.

    `AuthSettings` warnt bei ungesetztem Feld und gesetztem
    `resource_server_url` — und `mcp` 3.0 dreht den Default dort auf True. Die
    Wahl gehoert deshalb in diesen Code und nicht in einen kuenftigen Bump.
    Geprueft wird beides: der Wert und dass keine Warnung mehr faellt.
    """
    with warnings.catch_warnings(record=True) as gesehen:
        warnings.simplefilter("always")
        auth_settings, verifier = _build_auth(_auth_stack_settings())

    assert auth_settings.validate_token_resource is False
    assert verifier is not None
    deprecations = [w for w in gesehen if issubclass(w.category, MCPDeprecationWarning)]
    assert not deprecations, [str(w.message) for w in deprecations]


def _initialize_with_bearer(token: str) -> int:
    """Ein echtes `initialize` mit Bearer-Token durch den gebauten ASGI-Stack."""
    settings = _auth_stack_settings()
    with TestClient(build_http_app(settings)) as client:
        response = client.post(
            "/mcp",
            headers={
                "Host": "127.0.0.1:8000",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "auth-test", "version": "1"},
                },
            },
        )
    return response.status_code


def test_ein_gueltiges_token_kommt_durch_den_stack():
    """Der tragende Fall gegen ein voreiliges True.

    `validate_token_resource=True` vergleicht `AccessToken.resource` — hier
    `oauth_audience` — als URL woertlich mit `resource_server_url`, und das ist
    die Bind-URL. Nachgemessen: mit True antwortet derselbe Stack auf genau
    diese Anfrage mit 401, weil `"swiss-courts-mcp"` keine URL ist. Ein Wechsel
    auf True laesst also diesen Test fallen, statt still jeden Client
    auszusperren.
    """
    assert _initialize_with_bearer(issue_dev_token(_auth_stack_settings(), sub="u")) == 200


def test_ein_token_fuer_fremde_resource_scheitert_am_stack():
    """Gegenstueck zum Test darueber, damit die 200 etwas bedeutet.

    Ohne diesen Fall waere die 200 auch mit einer Auth-Schicht gruen, die gar
    nichts prueft. Der Verifier haengt also wirklich im Stack, und seine
    Publikumspruefung wirkt bis zum Statuscode.
    """
    settings = _auth_stack_settings()
    fremd = _token_for("https://ganz-anderer-dienst.example", settings.auth_secret)

    assert _initialize_with_bearer(fremd) == 401


def test_ein_token_von_fremdem_mandanten_scheitert_am_stack():
    """Die Issuerpruefung wirkt bis zum Statuscode, nicht nur im Verifier.

    Dasselbe Argument wie beim Publikum eine Ebene hoeher: der Verifier koennte
    korrekt pruefen und trotzdem nicht im Stack haengen. Das `aud` ist hier
    richtig — abgelehnt wird genau am `iss`.
    """
    settings = _auth_stack_settings()
    fremd = _token_for(AUDIENCE, settings.auth_secret, issuer="https://fremder-tenant.example")

    assert _initialize_with_bearer(fremd) == 401


# --- SEC-009: die oeffentliche Resource-URL (RFC 9728) ---


def _pinned(**kw) -> Settings:
    """Container-Szenario: 0.0.0.0-Bind mit Host-Allow-List, wie im Dockerfile."""
    return _settings(
        host="0.0.0.0",  # noqa: S104 — Container
        port=8000,
        allowed_hosts=["mcp.example.ch"],
        **kw,
    )


def _published(settings: Settings) -> tuple[dict, str]:
    """Was der Server als Resource-Identifier herausgibt.

    Beides zusammen, weil beides aus `resource_server_url` folgt und ein Test
    nur eines davon pruefen koennte, waehrend das andere abdriftet: das
    Metadaten-Dokument nach RFC 9728 und der `resource_metadata`-Hinweis, mit
    dem die 401 einen Client dorthin schickt.
    """
    with TestClient(build_http_app(settings)) as client:
        metadata = client.get(
            "/.well-known/oauth-protected-resource",
            headers={"Host": "mcp.example.ch"},
        )
        unauthorized = client.post(
            "/mcp",
            headers={
                "Host": "mcp.example.ch",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )

    assert metadata.status_code == 200
    assert unauthorized.status_code == 401
    return metadata.json(), unauthorized.headers["www-authenticate"]


def test_die_resource_url_wird_publiziert():
    """Der tragende Fall: `MCP_RESOURCE_URL` landet dort, wo Clients suchen."""
    document, www_authenticate = _published(_pinned(resource_url="https://mcp.example.ch"))

    assert document["resource"] == "https://mcp.example.ch"
    assert "https://mcp.example.ch/.well-known/oauth-protected-resource" in www_authenticate


def test_ohne_resource_url_steht_die_bind_adresse_da():
    """Negativkontrolle — und der gemessene Befund, der die Einstellung ausloeste.

    Ohne die Variable publiziert der Server die Bind-Adresse. Im Container ist
    das `http://0.0.0.0:8000`, also der Ort zum Token-Holen, den kein Client
    anwaehlen kann. Ohne diesen Test waere der Test darueber auch dann gruen,
    wenn `resource_url` nie im `AuthSettings` ankaeme — die Bind-Adresse
    enthaelt denselben Host, sobald man sie zufaellig gleich waehlt.
    """
    document, www_authenticate = _published(_pinned())

    assert document["resource"] == "http://0.0.0.0:8000"
    assert "http://0.0.0.0:8000" in www_authenticate


def test_ein_abschliessender_schraegstrich_wird_abgeschnitten():
    """RFC 8414/9207 vergleichen Issuer und Resource als exakte Zeichenketten.

    Ein versehentliches `https://mcp.example.ch/` wuerde sonst als anderer
    Identifier gelten als `https://mcp.example.ch` — und `AuthSettings` haelt
    den Pfad ausdruecklich fest (`url_preserve_empty_path`), schneidet also
    nichts von sich aus ab.
    """
    document, _ = _published(_pinned(resource_url="https://mcp.example.ch/"))

    assert document["resource"] == "https://mcp.example.ch"


def test_der_server_nennt_immer_den_idp_als_authorization_server():
    """`authorization_servers` nennt den IdP, nie diesen Server.

    Bis zum 19.9.2026 stand in `_build_auth` `settings.oauth_issuer or base`:
    ohne Issuer trug der Server sich selbst ein. Das war nicht bloss unsauber,
    sondern eine tote Kette — `authorization_servers[0]` ist der Wert, den ein
    SDK-Client als `auth_server_url` uebernimmt, und darunter antwortete dieser
    Server auf `/.well-known/oauth-authorization-server`,
    `/.well-known/openid-configuration`, `/authorize`, `/token` und `/register`
    mit 404.

    Der Rueckfall ist weg, und mit ihm der Zustand: ohne `MCP_OAUTH_ISSUER`
    entsteht kein Verifier (siehe `test_auth_enabled_without_issuer_raises`).
    Was dieser Test hier haelt, ist das Durchreichen — beide Felder kommen aus
    demselben `AuthSettings` und wurden einmal aus derselben Quelle gespeist,
    also muss geprueft bleiben, dass sie auseinanderlaufen koennen.
    """
    document, _ = _published(_pinned(resource_url="https://mcp.example.ch"))

    assert document["authorization_servers"] == [ISSUER]
    assert document["resource"] == "https://mcp.example.ch"
    assert document["authorization_servers"] != [document["resource"]]


def test_der_server_warnt_wenn_die_resource_url_fehlt():
    """Nicht raten, sondern warnen — wie bei `allowed_hosts`.

    Der erreichbare Name steht nicht in der Bind-Adresse. Statt ihn zu erfinden
    nennt der Server den publizierten Wert und die Variable, die ihn richtig
    stellt.
    """
    with capture_logs() as entries:
        _public_url(_pinned())

    events = {entry["event"] for entry in entries}
    assert "public_resource_url_unset" in events


def test_public_url_warnt_nicht_mehr_ueber_den_issuer():
    """Die zweite Warnung ist weg, und das ist pruefbar — mit dem richtigen Fall.

    Hier stand zuerst ein `assert "oauth_issuer_unset" not in events` im Test
    darueber. Die Gegenprobe zeigte, dass es nichts prueft: `_pinned` belegt den
    Issuer vor, die Warnung koennte dort also gar nicht feuern, und baute man sie
    wieder ein, blieb die Suite gruen. Ein Test, der die Implementierung nicht
    widerlegen kann, ist keiner.

    Also der Zustand, in dem sie feuern WUERDE: Settings ohne Issuer, am
    Verifier vorbei gebaut. Dass `_public_url` dort nur noch die eine Warnung
    kennt, ist der Beleg — die Zustaendigkeit fuer den Issuer liegt jetzt im
    Konstruktor, der gar keinen Server ohne ihn entstehen laesst.
    """
    ohne_issuer = Settings(
        auth_enabled=True,
        auth_secret="x" * 40,
        oauth_audience=AUDIENCE,
        host="0.0.0.0",  # noqa: S104 — Container
        port=8000,
    )

    with capture_logs() as entries:
        _public_url(ohne_issuer)

    assert [entry["event"] for entry in entries] == ["public_resource_url_unset"]


def test_bei_loopback_warnt_er_nicht():
    """Gegenprobe zur Warnung: bei einem Loopback-Bind stimmt die Bind-Adresse.

    Ohne diesen Fall waere der Test darueber auch mit einer Warnung gruen, die
    immer feuert — und eine Warnung, die immer kommt, wird ueberlesen.
    """
    with capture_logs() as entries:
        result = _public_url(_settings(host="127.0.0.1", port=8000))

    assert result == "http://127.0.0.1:8000"
    assert [entry["event"] for entry in entries] == []


def test_die_resource_url_kommt_aus_dem_environment(monkeypatch):
    """Die Verdrahtung in `from_env`, und sie fehlte zuerst.

    Die Gegenprobe deckte es auf: nimmt man
    `resource_url=os.environ.get("MCP_RESOURCE_URL")` aus `Settings.from_env`
    heraus, bleibt die ganze Suite gruen — alle Tests oben bauen ihr `Settings`
    direkt und kommen an der Environment-Auswertung vorbei. Eine Einstellung,
    die niemand ueber ihre dokumentierte Variable setzen kann, ist keine
    Einstellung.
    """
    monkeypatch.setenv("MCP_RESOURCE_URL", "https://mcp.example.ch")

    assert Settings.from_env().resource_url == "https://mcp.example.ch"


def test_ohne_die_variable_bleibt_die_resource_url_leer(monkeypatch):
    """Gegenstueck dazu: kein stiller Default, der die Warnung aushebelt."""
    monkeypatch.delenv("MCP_RESOURCE_URL", raising=False)

    assert Settings.from_env().resource_url is None


def test_die_gesetzte_url_schlaegt_den_bind():
    """`_public_url` bevorzugt die Einstellung und warnt dann nicht."""
    with capture_logs() as entries:
        result = _public_url(_pinned(resource_url="https://mcp.example.ch"))

    assert result == "https://mcp.example.ch"
    assert [entry["event"] for entry in entries] == []
