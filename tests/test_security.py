"""Security-Tests: Egress-Allow-List (SEC-021), Auth (SEC-009), Config (SEC-016)."""

from __future__ import annotations

import time

import pytest

from swiss_courts_mcp import api_client
from swiss_courts_mcp.api_client import EgressNotAllowedError, assert_host_allowed
from swiss_courts_mcp.auth import AuthConfigError, JWTTokenVerifier, issue_dev_token
from swiss_courts_mcp.config import Settings

# --- SEC-021 / SEC-004: Egress-Allow-List ---

def test_allowed_host_passes():
    assert_host_allowed("https://entscheidsuche.ch/_search.php")


@pytest.mark.parametrize("url", [
    "https://evil.example.com/x",
    "http://entscheidsuche.ch/x",          # kein HTTPS
    "https://169.254.169.254/latest/meta",  # Cloud-Metadata
    "https://entscheidsuche.ch.evil.com/x",
])
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

def _settings(secret="test-secret-please-change-0123456789abcdef", **kw):
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
        JWTTokenVerifier(Settings(auth_enabled=True))


def test_token_ttl_reflected_in_exp():
    s = _settings()
    token = issue_dev_token(s, sub="u", ttl_seconds=60)
    import jwt
    claims = jwt.decode(token, s.auth_secret, algorithms=["HS256"])
    assert claims["exp"] - int(time.time()) <= 60
