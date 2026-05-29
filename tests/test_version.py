"""Version-Konsistenz zwischen Paket und pyproject (Release-Disziplin)."""

from __future__ import annotations

import re
from pathlib import Path

from swiss_courts_mcp import __version__


def test_package_version_matches_pyproject():
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m is not None, "version not found in pyproject.toml"
    assert __version__ == m.group(1)


def test_changelog_has_release_entry():
    changelog = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
    assert f"## [{__version__}]" in changelog.read_text(encoding="utf-8")
