# syntax=docker/dockerfile:1
# Container für den HTTP-/Cloud-Modus (SEC-007, SEC-016).
FROM python:3.12-slim AS base

# Nicht-root-User mit hoher UID (SEC-007).
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Abhängigkeiten zuerst (Layer-Caching).
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir ".[http]"

# Im Container bewusst an alle Interfaces binden — nur hier, nicht im Code (SEC-016).
ENV MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_ALLOW_PUBLIC_BIND=1 \
    MCP_STATELESS_HTTP=true \
    MCP_AUTH_ENABLED=true \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8000

# Auth-Konfiguration (MCP_AUTH_SECRET oder MCP_OAUTH_JWKS_URL) zur Laufzeit
# injizieren — niemals ins Image backen (SEC-013).
ENTRYPOINT ["python", "-m", "swiss_courts_mcp", "--http"]
