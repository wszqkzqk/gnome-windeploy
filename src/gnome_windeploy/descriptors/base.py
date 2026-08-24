"""Declarative component descriptions consumed by the deployment engine.

Everything the engine knows about a GNOME component is pure data: which DLLs
trigger it, which prefix-relative directories to mirror, which caches to
regenerate, and which gettext domains to ship locales for. The engine itself
contains zero per-component logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheFixup:
    """Regenerate a cache file inside the staging tree and rewrite its paths.

    The tool is located in a source prefix at ``tool`` (prefix-relative) and is
    run with ``args``, where the placeholder ``{target}`` expands to the
    absolute staged target directory ``target_dir`` (skipped silently when that
    directory was not staged). Afterwards the generated ``cache_file``
    (prefix-relative, may contain one ``*`` glob segment for versioned
    directories) has its absolute source-prefix paths rewritten relative to
    its own location.

    ``stdout_to_cache``: the tool prints the cache to stdout instead of writing
    it in place (e.g. gdk-pixbuf-query-loaders); the engine captures stdout and
    writes it to ``cache_file``. ``relativize``: disable for binary caches such
    as ``gschemas.compiled`` that contain no paths to rewrite.
    """

    tool: str
    args: tuple[str, ...] = ()
    target_dir: str = ""
    cache_file: str = ""
    stdout_to_cache: bool = False
    relativize: bool = True


@dataclass(frozen=True)
class Descriptor:
    """Pure-data description of a deployable component of the GNOME stack.

    ``trigger_dlls``: lower-cased DLL names activating this component when any
    appears in the dependency closure (empty means activation only via
    ``implies`` or ``always``). ``mirror_dirs``: prefix-relative directories to
    mirror when present. ``stage_files``: groups of alternative prefix-relative
    files; the first existing alternative of each group is staged at the same
    relative location. ``cache_fixups``: cache regeneration operations run
    against the staged tree. ``gettext_domains``: message catalog names used
    for locale mirroring in ``deps`` mode. ``implies``: names of descriptors
    activated transitively. ``always``: activate unconditionally.
    """

    name: str
    trigger_dlls: frozenset[str] = frozenset()
    mirror_dirs: tuple[str, ...] = ()
    stage_files: tuple[tuple[str, ...], ...] = ()
    cache_fixups: tuple[CacheFixup, ...] = ()
    gettext_domains: tuple[str, ...] = ()
    implies: tuple[str, ...] = ()
    always: bool = False
