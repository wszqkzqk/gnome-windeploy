"""DLL-anchored installation prefix derivation.

The theoretical basis is GLib's Windows relocatability contract: every
GLib-family DLL resolves its installation prefix at runtime from its own module
location and finds ``share/...`` and ``lib/...`` relative to it. A DLL living in
``<prefix>/bin`` or ``<prefix>/lib`` therefore anchors *prefix*; a DLL anywhere
else anchors its own directory as a nonstandard-but-legal root.
"""

from __future__ import annotations

from pathlib import Path

ANCHOR_DIR_NAMES: frozenset[str] = frozenset({"bin", "lib"})


def derive_prefix(dll_path: Path) -> Path:
    """Return the installation prefix anchored by a DLL (or exe) location.

    If the binary's directory is named ``bin`` or ``lib`` (case-insensitive),
    the prefix is the parent of that directory; otherwise the binary's own
    directory serves as the anchor root.
    """
    parent = dll_path.parent
    if parent.name.lower() in ANCHOR_DIR_NAMES:
        return parent.parent
    return parent
