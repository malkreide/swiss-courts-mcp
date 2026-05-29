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
        if settings.oauth_jwks_url:
            self._jwks_client = jwt.PyJWKClient(settings.oauth_jwks_url)

    def _decode(self, token: str) -> dict:
        common = {
            "audience": self.settings.oauth_audience,
            "issuer": self.settings.oauth_issuer,
            "options": {
                "require": ["exp", "sub"],
                "verify_aud": bool(self.settings.oauth_audience),
                "verify_iss": bool(self.settings.oauth_issuer),
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
