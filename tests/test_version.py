"""Keeps the User-Agent version from ever drifting.

The literal in `api_client.py` and the one in `__init__.py` both read 0.3.0 and
happened to match `pyproject.toml` — but nothing enforced that. The next version
bump would have left entscheidsuche.ch looking at a stale value, which is
exactly how it played out in five sibling servers of this portfolio.

These tests fail if anyone reintroduces a literal.
"""

import tomllib
from pathlib import Path

import swiss_courts_mcp
from swiss_courts_mcp import api_client

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _pyproject_version() -> str:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]


def test_version_matches_pyproject():
    assert swiss_courts_mcp.__version__ == _pyproject_version()


def test_user_agent_carries_the_real_version():
    assert api_client.USER_AGENT == f"swiss-courts-mcp/{_pyproject_version()}"


def test_user_agent_is_not_a_source_checkout_marker():
    assert "+source" not in api_client.USER_AGENT
