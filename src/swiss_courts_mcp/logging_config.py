"""
Strukturiertes Logging auf stderr (OBS-003, OBS-004).
=====================================================
structlog mit JSON-Output, fest auf ``sys.stderr``. Das ist für
stdio-Transport zwingend: stdout ist exklusiv dem MCP-Protokoll
vorbehalten — jede Log-Zeile auf stdout würde den JSON-RPC-Stream
zerstören (OBS-004).

Verwendung:

    from swiss_courts_mcp.logging_config import configure_logging, get_logger
    configure_logging()
    log = get_logger(__name__)
    log.info("tool_call", tool="search_court_decisions", session_id=sid)
"""

from __future__ import annotations

import logging
import sys

import structlog

_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Konfiguriert structlog idempotent. JSON auf stderr."""
    global _configured
    if _configured:
        return

    # Stdlib-Logging-Root ebenfalls auf stderr lenken, damit fremde
    # Bibliotheken nicht auf stdout schreiben (OBS-004).
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.WriteLoggerFactory(file=sys.stderr),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Liefert einen gebundenen Logger (konfiguriert bei Bedarf)."""
    if not _configured:
        configure_logging()
    return structlog.get_logger(name)
