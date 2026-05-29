"""
Zentrale Konfiguration via Pydantic-Settings-Objekt (ARCH-004).
=================================================================
Statt globaler Modul-Variablen wird die Laufzeit-Konfiguration in einem
einzigen, validierten Settings-Objekt gebündelt. Alle Werte stammen aus
Environment-Variablen — keine Secrets im Code (ARCH-005, SEC-013).

Für den lokalen stdio-Betrieb sind sämtliche Felder optional; die Defaults
sind bewusst sicher (Host 127.0.0.1, Auth aus).
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings(BaseModel):
    """Validierte Laufzeit-Konfiguration des Servers."""

    # --- Transport / Netzwerk ---
    host: str = Field(default="127.0.0.1", description="Bind-Host im HTTP-Modus.")
    port: int = Field(default=8000, ge=1, le=65535)
    allow_public_bind: bool = Field(default=False)
    stateless_http: bool = Field(default=True)

    # --- Auth (SEC-009) ---
    auth_enabled: bool = Field(default=False)
    auth_secret: str | None = Field(default=None)
    oauth_jwks_url: str | None = Field(default=None)
    oauth_issuer: str | None = Field(default=None)
    oauth_audience: str | None = Field(default=None)
    required_scopes: list[str] = Field(default_factory=list)

    # --- CORS (SDK-004) ---
    cors_origins: list[str] = Field(default_factory=list)

    @classmethod
    def from_env(cls) -> Settings:
        """Baut das Settings-Objekt aus Environment-Variablen."""
        return cls(
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8000")),
            allow_public_bind=_env_bool("MCP_ALLOW_PUBLIC_BIND"),
            stateless_http=_env_bool("MCP_STATELESS_HTTP", default=True),
            auth_enabled=_env_bool("MCP_AUTH_ENABLED"),
            auth_secret=os.environ.get("MCP_AUTH_SECRET"),
            oauth_jwks_url=os.environ.get("MCP_OAUTH_JWKS_URL"),
            oauth_issuer=os.environ.get("MCP_OAUTH_ISSUER"),
            oauth_audience=os.environ.get("MCP_OAUTH_AUDIENCE"),
            required_scopes=_env_list("MCP_REQUIRED_SCOPES"),
            cors_origins=_env_list("MCP_CORS_ORIGINS"),
        )
