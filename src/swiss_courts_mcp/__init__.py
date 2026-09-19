"""Swiss Courts MCP Server — Schweizer Gerichtsentscheide via entscheidsuche.ch."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as _distribution_metadata
from importlib.metadata import version as _distribution_version

_DIST = "swiss-courts-mcp"

try:
    # Read the version from the installed distribution metadata, built from
    # pyproject.toml. The literal here and the one in the User-Agent happened to
    # agree at 0.3.0, but nothing enforced that — the next version bump would
    # have silently left entscheidsuche.ch looking at a stale value, which is
    # exactly how it played out in five sibling servers.
    __version__ = _distribution_version(_DIST)
except PackageNotFoundError:
    # Source tree without an install. Deliberately not a plausible-looking
    # number: an obviously non-release marker beats a wrong version on the wire.
    __version__ = "0.0.0+source"


def _project_url(label: str) -> str | None:
    """Eine ``[project.urls]``-Adresse aus den Metadaten, ``None`` ohne Install.

    Dieselbe Quelle wie ``__version__`` und aus demselben Grund: was hier als
    Literal stünde, wiederholte einen Wert aus ``pyproject.toml``, und
    ``scripts/check_version_sync.py`` hält nur die *Versions*-Wiederholungen
    nach — eine abgedriftete URL fiele nirgends auf.

    ``Project-URL`` kommt je Eintrag einmal vor, als ``"<Label>, <URL>"``.
    """
    try:
        md = _distribution_metadata(_DIST)
    except PackageNotFoundError:
        return None
    for entry in md.get_all("Project-URL") or ():
        name, _, url = entry.partition(",")
        if name.strip().lower() == label.lower():
            return url.strip() or None
    return None


#: Projekt-URL, wie sie ``pyproject.toml`` unter ``[project.urls] Homepage``
#: deklariert. Sie reist in der Modern-Ära (Spec 2026-07-28) im
#: ``serverInfo``-Stempel mit: dort gibt es keinen ``initialize``, der die
#: Server-Identität einmalig übertragen könnte.
__homepage__ = _project_url("Homepage")
