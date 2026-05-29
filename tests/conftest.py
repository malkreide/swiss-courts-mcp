"""Gemeinsame Test-Fixtures."""

from __future__ import annotations

import types

import httpx
import pytest

from swiss_courts_mcp import api_client


class FakeContext:
    """Minimaler Context-Ersatz für Unit-Tests der Tool-Handler.

    Stellt den gepoolten Client über `request_context.lifespan_context`
    bereit und no-op-Implementierungen für report_progress/info.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.request_context = types.SimpleNamespace(lifespan_context={"client": client})

    async def report_progress(self, *args, **kwargs) -> None:
        return None

    async def info(self, *args, **kwargs) -> None:
        return None

    async def warning(self, *args, **kwargs) -> None:
        return None

    async def error(self, *args, **kwargs) -> None:
        return None


@pytest.fixture
async def ctx():
    """Liefert einen FakeContext mit echtem (von respx abgefangenem) Client."""
    client = api_client.new_client()
    try:
        yield FakeContext(client)
    finally:
        await client.aclose()


# Beispiel-ES-Antwort für gemockte Suchen.
SAMPLE_ES_RESPONSE = {
    "hits": {
        "total": {"value": 1},
        "hits": [
            {
                "_id": "CH_BGer_005_test_2025-01-01",
                "_source": {
                    "date": "2025-01-01",
                    "hierarchy": ["CH", "Bundesgericht"],
                    "title": {"de": "Testurteil"},
                    "abstract": {"de": "Eine Zusammenfassung."},
                    "reference": ["5A_1/2025"],
                    "attachment": {"language": "de"},
                },
            }
        ],
    }
}

EMPTY_ES_RESPONSE = {"hits": {"total": {"value": 0}, "hits": []}}
