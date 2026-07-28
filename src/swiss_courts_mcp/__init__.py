"""Swiss Courts MCP Server — Schweizer Gerichtsentscheide via entscheidsuche.ch."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

try:
    # Read the version from the installed distribution metadata, built from
    # pyproject.toml. The literal here and the one in the User-Agent happened to
    # agree at 0.3.0, but nothing enforced that — the next version bump would
    # have silently left entscheidsuche.ch looking at a stale value, which is
    # exactly how it played out in five sibling servers.
    __version__ = _distribution_version("swiss-courts-mcp")
except PackageNotFoundError:
    # Source tree without an install. Deliberately not a plausible-looking
    # number: an obviously non-release marker beats a wrong version on the wire.
    __version__ = "0.0.0+source"
