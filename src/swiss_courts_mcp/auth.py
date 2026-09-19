"""
Bearer-Token-Authentifizierung für den HTTP-Transport (SEC-009).
================================================================
Implementiert das SDK-native ``TokenVerifier``-Protokoll. Die User-Identität
stammt ausschliesslich aus dem **validierten** JWT (``sub``-Claim) — niemals
aus Client-Headern. Die Token-Lebensdauer (``exp``) erzwingt die Session-TTL;
ein abgelaufenes Token wird abgelehnt.

Zwei Validierungsmodi:

* **HS256** — symmetrisches Secret (``MCP_AUTH_SECRET``), für Entwicklung und
  einfache Deployments.
* **RS256 via JWKS** — asymmetrisch gegen die JWKS-URL des IdP
  (``MCP_OAUTH_JWKS_URL``), für Produktion.

In beiden Modi sind ``MCP_OAUTH_AUDIENCE`` und ``MCP_OAUTH_ISSUER`` Pflicht.
Beide Claims beantworten dieselbe Frage von zwei Seiten, und fehlte eines,
schaltete dieser Verifier die zugehörige Prüfung lautlos ab:

* ``aud`` bindet das Token an *diesen* Server. Ohne die Variable kam jedes
  korrekt signierte Token desselben Issuers durch — auch eines, das für einen
  ganz anderen Dienst ausgestellt wurde.
* ``iss`` bindet es an *den* IdP, dem dieser Server traut. Ohne die Variable
  kam ein Token mit fremdem ``iss`` durch, und eines ganz ohne ``iss``
  ebenfalls. Das trägt, sobald mehrere Mandanten dieselbe JWKS-URL teilen:
  die Signatur ist dann für alle gültig, und nur ``iss`` trennt sie.

Nur relevant im HTTP-Modus mit ``MCP_AUTH_ENABLED=true``. Der stdio-Transport
läuft ohne Auth (lokal = vertrauenswürdig, SEC-006).
"""

from __future__ import annotations

import time

import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier

from swiss_courts_mcp.config import Settings
from swiss_courts_mcp.logging_config import get_logger

log = get_logger(__name__)


class AuthConfigError(RuntimeError):
    """Auth aktiviert, aber unvollständig konfiguriert."""


class MissingVerificationTargetError(jwt.InvalidTokenError):
    """Der Wert, gegen den geprüft würde, fehlt — dann wird abgelehnt.

    Erbt bewusst von ``jwt.InvalidTokenError``: ``verify_token`` fängt
    ``jwt.PyJWTError``, das Token wird also mit 401 abgelehnt statt den Prozess
    mit einem 500 zu quittieren. Der Log-Grund nennt diese Klasse, nicht einen
    Token-Fehler — das Token ist in Ordnung, die Konfiguration nicht.
    """


class JWTTokenVerifier(TokenVerifier):
    """Validiert Bearer-JWTs und liefert eine ``AccessToken``-Identität."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks_client: jwt.PyJWKClient | None = None

        if not (settings.auth_secret or settings.oauth_jwks_url):
            raise AuthConfigError(
                "MCP_AUTH_ENABLED=true erfordert entweder MCP_AUTH_SECRET "
                "(HS256) oder MCP_OAUTH_JWKS_URL (RS256)."
            )
        if not settings.oauth_audience:
            # Ohne Publikum prueft `_decode` das `aud`-Claim nicht — und ein
            # korrekt signiertes Token, das derselbe Issuer fuer einen ANDEREN
            # Dienst ausgestellt hat, kommt durch. Nachgemessen, nicht
            # geschlossen: ein Token mit
            # `aud: "https://ganz-anderer-dienst.example"` wurde ohne diese
            # Pruefung akzeptiert und mit ihr als `InvalidAudienceError`
            # abgelehnt. Das ist der klassische Confused Deputy, und die
            # Pflicht hier ist der Grund, warum `AuthSettings` in
            # `server._build_auth` mit `validate_token_resource=False`
            # wahrheitsgemaess sagen darf, der Verifier pruefe selbst.
            raise AuthConfigError(
                "MCP_AUTH_ENABLED=true erfordert MCP_OAUTH_AUDIENCE — den "
                "Resource-Identifier, auf den der IdP Tokens fuer diesen "
                "Server bindet. Ohne ihn wird das aud-Claim nicht geprueft, "
                "und Tokens fuer fremde Dienste desselben Issuers gelten hier."
            )
        if not settings.oauth_issuer:
            # Dieselbe Klasse wie oben, andere Seite des Tokens: ohne Issuer
            # stand `verify_iss` auf False, und `_decode` liess alles durch.
            # Nachgemessen am 19.9.2026, HS256, Publikum korrekt gesetzt:
            #
            #   ohne die Variable   iss fremder Tenant  -> AKZEPTIERT
            #                       iss fehlt ganz      -> AKZEPTIERT
            #   mit der Variable    iss fremder Tenant  -> InvalidIssuerError
            #                       iss fehlt ganz      -> MissingRequiredClaimError
            #                       iss == Issuer       -> AKZEPTIERT (Kontrolle)
            #
            # Das `require` unten braucht darum kein "iss": pyjwt fordert das
            # Claim bei gesetztem `issuer` von sich aus ein — gemessen als
            # `MissingRequiredClaimError`, nicht angenommen. Ein zweiter Pin
            # derselben Tatsache waere eine Drift-Quelle; ein Test haelt sie.
            raise AuthConfigError(
                "MCP_AUTH_ENABLED=true erfordert MCP_OAUTH_ISSUER — den "
                "Issuer des IdP, der die Tokens ausstellt. Ohne ihn wird das "
                "iss-Claim nicht geprueft: Tokens fremder Mandanten desselben "
                "JWKS gelten hier, und ein Token ganz ohne iss ebenfalls. Der "
                "Wert muss dem iss-Claim zeichengleich entsprechen, "
                "abschliessender Schraegstrich inbegriffen (RFC 8414/9207)."
            )
        if settings.oauth_jwks_url:
            self._jwks_client = jwt.PyJWKClient(settings.oauth_jwks_url)

    def _decode(self, token: str) -> dict:
        # Der Vorbehalt, der hier stand — `_build_auth` setze ersatzweise die
        # eigene Basis-URL als `issuer_url` ein, ein erzwungenes `verify_iss`
        # pruefe also gegen einen Wert, den kein IdP ausgestellt hat — ist mit
        # dem Issuerzwang weg: `issuer_url` ist jetzt unbedingt `oauth_issuer`,
        # und die Ersatzebene existiert nicht mehr.
        #
        # `oauth_issuer` wird NICHT normalisiert. Anders als bei
        # `MCP_RESOURCE_URL`, wo `_public_url` einen abschliessenden
        # Schraegstrich abschneidet, ist er hier bedeutungstragend: gemessen
        # ergibt `iss` mit Schraegstrich gegen einen Issuer ohne ihn
        # `InvalidIssuerError`. Manche IdP stellen `iss` mit Schraegstrich aus;
        # ein `rstrip` hier machte deren Tokens ungueltig.

        # Fail-closed, und dieser Riegel ist nicht Zierde: die `verify_*`-Flags
        # allein tragen die zweite Schicht NICHT. Nachgemessen und in der
        # pyjwt-Quelle (2.14.0, `api_jwt.py`) nachgelesen:
        #
        #   `_validate_iss(issuer=None)` kehrt in der ersten Zeile zurueck —
        #   `verify_iss: True` prueft dann gar nichts, und ein Token mit
        #   fremdem `iss` wird AKZEPTIERT.
        #
        #   `_validate_aud(audience=None)` wirft nur, wenn das Token ein `aud`
        #   FUEHRT. Ein Token ganz ohne `aud` wird AKZEPTIERT.
        #
        # Der Konstruktor laesst diesen Zustand nicht entstehen, aber genau
        # darauf hatte sich die Publikumsschicht verlassen: ein Verifier, dem
        # jemand die Settings nachtraeglich aendert, prueft sonst lautlos nichts
        # mehr. Ein fehlender Erwartungswert ist deshalb eine Ablehnung.
        audience = self.settings.oauth_audience
        issuer = self.settings.oauth_issuer
        if not audience or not issuer:
            fehlend = [
                name
                for name, wert in (("MCP_OAUTH_AUDIENCE", audience), ("MCP_OAUTH_ISSUER", issuer))
                if not wert
            ]
            raise MissingVerificationTargetError(f"Erwartungswert fehlt: {', '.join(fehlend)}")

        # `verify_aud`/`verify_iss` stehen fest auf True; der Konstruktor laesst
        # keinen Verifier ohne Publikum und ohne Issuer entstehen. Vorher hingen
        # die Flags an `bool(...)` der jeweiligen Einstellung — die Pruefungen
        # schalteten sich also selbst ab, sobald die Variable fehlte, lautlos.
        common = {
            "audience": audience,
            "issuer": issuer,
            "options": {
                "require": ["exp", "sub"],
                "verify_aud": True,
                "verify_iss": True,
            },
        }
        if self._jwks_client is not None:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(token, signing_key.key, algorithms=["RS256"], **common)
        return jwt.decode(token, self.settings.auth_secret, algorithms=["HS256"], **common)

    async def verify_token(self, token: str) -> AccessToken | None:
        """Validiert das Token. Gibt ``None`` bei jedem Fehler zurück (→ 401)."""
        try:
            claims = self._decode(token)
        except jwt.PyJWTError as exc:
            # Niemals Token-Inhalt loggen; nur den Fehlertyp.
            log.warning("token_rejected", reason=type(exc).__name__)
            return None

        sub = claims.get("sub")
        if not sub:
            log.warning("token_rejected", reason="missing_sub")
            return None

        scopes = _extract_scopes(claims)
        required = set(self.settings.required_scopes)
        if required and not required.issubset(set(scopes)):
            log.warning("token_rejected", reason="insufficient_scope", sub=sub)
            return None

        expires_at = claims.get("exp")
        log.info("token_accepted", sub=sub, scopes=scopes)
        return AccessToken(
            token=token,
            client_id=str(sub),
            scopes=scopes,
            expires_at=int(expires_at) if expires_at else None,
            resource=self.settings.oauth_audience,
        )


def _extract_scopes(claims: dict) -> list[str]:
    """Scopes aus ``scope`` (space-delimited) oder ``scopes`` (list)."""
    raw = claims.get("scope") or claims.get("scopes") or []
    if isinstance(raw, str):
        return [s for s in raw.split() if s]
    if isinstance(raw, list):
        return [str(s) for s in raw]
    return []


def issue_dev_token(
    settings: Settings,
    sub: str = "dev-user",
    scopes: list[str] | None = None,
    ttl_seconds: int = 3600,
) -> str:
    """Erzeugt ein HS256-Token für lokale Tests/Entwicklung.

    Nur nutzbar wenn ``MCP_AUTH_SECRET`` gesetzt ist.
    """
    if not settings.auth_secret:
        raise AuthConfigError("issue_dev_token benötigt MCP_AUTH_SECRET (HS256).")
    now = int(time.time())
    payload: dict = {
        "sub": sub,
        "iat": now,
        "exp": now + ttl_seconds,
        "scope": " ".join(scopes or settings.required_scopes or []),
    }
    if settings.oauth_issuer:
        payload["iss"] = settings.oauth_issuer
    if settings.oauth_audience:
        payload["aud"] = settings.oauth_audience
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")
