"""Deployment orchestration: closure, staging, mirroring, fixups, leak scan.

The engine mirrors every source prefix into one staging tree preserving
relative layout (``bin/``, ``lib/``, ``share/``, ``etc/``), regenerates caches
with relativized paths, and verifies that no absolute source path leaks into
the bundle.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from collections import deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from gnome_windeploy import cachefix
from gnome_windeploy.descriptors import REGISTRY
from gnome_windeploy.descriptors.base import Descriptor
from gnome_windeploy.pe import ClosureResolver, ImportsProvider
from gnome_windeploy.prefix import derive_prefix

PE_SUFFIXES: frozenset[str] = frozenset({".exe", ".dll"})

TEXT_SUFFIXES: frozenset[str] = frozenset(
    {
        ".cache",
        ".theme",
        ".desktop",
        ".pc",
        ".conf",
        ".cfg",
        ".ini",
        ".xml",
        ".json",
        ".txt",
        ".schemas",
        ".list",
        ".types",
    }
)

LEAK_SCAN_MAX_BYTES = 1024 * 1024

APP_TAGS: frozenset[str] = frozenset({"app", "app-tree"})

# Callable running a cache tool; receives argv, returns stdout, raises on error.
ToolRunner = Callable[[Sequence[str]], str]


class DeployError(Exception):
    """A fatal deployment failure with a user-actionable message."""


class LeakError(DeployError):
    """Absolute source-prefix paths leaked into staged text files."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = list(problems)
        details = "\n".join(f"  {problem}" for problem in self.problems)
        super().__init__(f"absolute source paths leaked into the bundle:\n{details}")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same_content(first: Path, second: Path) -> bool:
    return first.stat().st_size == second.stat().st_size and _hash_file(first) == _hash_file(
        second
    )


class Stager:
    """Copy files into the staging tree, preserving prefix-relative layout.

    First writer wins: a conflicting file with different content is recorded as
    a collision (kept: the first), or as an override when the existing file
    came from the application itself (app files always win over dependencies).
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.index: dict[str, tuple[Path, str]] = {}
        self.collisions: list[str] = []
        self.overrides: list[str] = []
        self.new_sources: list[Path] = []

    def stage_file(self, src: Path, prefix: Path, tag: str) -> Path | None:
        """Stage *src* at its prefix-relative location; return the dest if new."""
        rel = src.relative_to(prefix)
        key = rel.as_posix()
        existing = self.index.get(key)
        if existing is not None:
            if _same_content(existing[0], src):
                return None
            if existing[1] in APP_TAGS and tag not in APP_TAGS:
                self.overrides.append(
                    f"{key}: keeping application file {existing[0]}, ignoring {src}"
                )
            else:
                self.collisions.append(
                    f"{key}: keeping {existing[0]} ({existing[1]}), conflicting {src} ({tag})"
                )
            return None
        dest = self.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        self.index[key] = (src, tag)
        self.new_sources.append(src)
        return dest

    def mirror_dir(
        self,
        prefix: Path,
        rel_dir: str,
        tag: str,
        file_filter: Callable[[Path], bool] | None = None,
    ) -> int:
        """Mirror the prefix-relative directory *rel_dir* if present; return count."""
        src_root = prefix / rel_dir
        if not src_root.is_dir():
            return 0
        count = 0
        for path in sorted(src_root.rglob("*")):
            if not path.is_file():
                continue
            if file_filter is not None and not file_filter(path.relative_to(prefix)):
                continue
            if self.stage_file(path, prefix, tag) is not None:
                count += 1
        return count


def icon_file_filter(policy: str) -> Callable[[Path], bool] | None:
    """Build a prefix-relative path predicate implementing the icon policy.

    ``full`` keeps everything (returns no filter). ``scalable`` keeps each
    theme's ``index.theme`` and its ``scalable/`` subtrees. ``symbolic``
    additionally restricts scalable files to ``*-symbolic.svg``. Subdirectories
    missing relative to index.theme are tolerated by GTK, so no index rewrite
    is needed.
    """
    if policy == "full":
        return None
    if policy not in {"scalable", "symbolic"}:
        raise ValueError(f"unknown icon policy: {policy}")

    def keep(rel: Path) -> bool:
        parts = rel.parts
        if len(parts) < 3 or parts[0] != "share" or parts[1] != "icons":
            return True
        theme_subpath = parts[2:]
        if len(theme_subpath) == 2 and theme_subpath[1] == "index.theme":
            return True
        if "scalable" not in theme_subpath[1:-1]:
            return False
        if policy == "scalable":
            return True
        return theme_subpath[-1].endswith("-symbolic.svg")

    return keep


def mirror_locales(
    stager: Stager,
    prefixes: Iterable[Path],
    domains: Iterable[str],
    *,
    mode: str,
    langs: Iterable[str] | None = None,
) -> None:
    """Mirror gettext message catalogs into staging.

    ``deps`` mirrors only ``share/locale/<lang>/LC_MESSAGES/<domain>.mo`` for
    the given domains, for every language present (optionally filtered to
    *langs*). ``full`` mirrors the whole ``share/locale`` tree of every prefix.
    ``none`` mirrors nothing.
    """
    if mode == "none":
        return
    if mode == "full":
        for prefix in prefixes:
            stager.mirror_dir(prefix, "share/locale", "locales")
        return
    if mode != "deps":
        raise ValueError(f"unknown locale mode: {mode}")
    lang_filter = set(langs) if langs else None
    domain_list = sorted(set(domains))
    for prefix in prefixes:
        locale_root = prefix / "share" / "locale"
        if not locale_root.is_dir():
            continue
        for lang_dir in sorted(locale_root.iterdir()):
            if not lang_dir.is_dir():
                continue
            if lang_filter is not None and lang_dir.name not in lang_filter:
                continue
            lc_messages = lang_dir / "LC_MESSAGES"
            if not lc_messages.is_dir():
                continue
            for domain in domain_list:
                catalog = lc_messages / f"{domain}.mo"
                if catalog.is_file():
                    stager.stage_file(catalog, prefix, "locales")


def resolve_activation(
    registry: dict[str, Descriptor], dll_names: Iterable[str]
) -> tuple[dict[str, Descriptor], dict[str, list[str]]]:
    """Activate descriptors from DLL triggers, expanding ``implies`` transitively.

    Returns the activated descriptors (in activation order) and a map of
    descriptor name to the names of the descriptors that implied it.
    """
    names = {name.lower() for name in dll_names}
    activated: dict[str, Descriptor] = {}
    implied_by: dict[str, list[str]] = {}
    queue: deque[str] = deque(
        desc.name
        for desc in registry.values()
        if desc.always or {trigger.lower() for trigger in desc.trigger_dlls} & names
    )
    while queue:
        name = queue.popleft()
        if name in activated:
            continue
        desc = registry.get(name)
        if desc is None:
            raise DeployError(f"descriptor registry references unknown descriptor {name!r}")
        activated[name] = desc
        for dependency in desc.implies:
            implied_by.setdefault(dependency, []).append(name)
            queue.append(dependency)
    return activated, implied_by


def _trigger_prefixes(trigger_dlls: Iterable[str], closure: dict[str, Path]) -> list[Path]:
    """Return the ordered, deduplicated prefixes anchored by the given DLLs."""
    prefixes: list[Path] = []
    for dll in trigger_dlls:
        origin = closure.get(dll.lower())
        if origin is not None:
            prefix = derive_prefix(origin)
            if prefix not in prefixes:
                prefixes.append(prefix)
    return prefixes


def descriptor_search_prefixes(
    desc: Descriptor,
    closure: dict[str, Path],
    known_prefixes: Sequence[Path],
    implied_by: dict[str, list[str]],
    registry: dict[str, Descriptor],
) -> tuple[list[Path], bool]:
    """Return ``(prefixes to search, anchored)`` for a descriptor.

    DLL-anchored descriptors search the prefixes derived from their own
    trigger DLLs found in the closure. Data-only descriptors search the
    prefixes of the components that implied them first, then all known
    prefixes.
    """
    anchored = _trigger_prefixes(desc.trigger_dlls, closure)
    if anchored:
        return anchored, True
    ordered: list[Path] = []
    for parent_name in implied_by.get(desc.name, []):
        for prefix in _trigger_prefixes(registry[parent_name].trigger_dlls, closure):
            if prefix not in ordered:
                ordered.append(prefix)
    for prefix in known_prefixes:
        if prefix not in ordered:
            ordered.append(prefix)
    return ordered, False


def _resolve_cache_path(staging: Path, pattern: str) -> Path | None:
    """Resolve a cache-file pattern (one ``*`` segment allowed) inside staging.

    When the cache file itself does not exist yet, resolve the parent pattern
    instead and return the would-be path inside the first matching directory.
    """
    if "*" not in pattern:
        return staging / pattern
    matches = sorted(staging.glob(pattern))
    if matches:
        return matches[0]
    parent_pattern, _, name = pattern.rpartition("/")
    for parent in sorted(staging.glob(parent_pattern)):
        return parent / name
    return None


def default_tool_runner(argv: Sequence[str]) -> str:
    """Run a cache-generation tool, returning stdout; raise DeployError on failure."""
    proc = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise DeployError(
            f"cache tool {argv[0]} failed with exit code {proc.returncode}:\n"
            f"{proc.stderr.strip()}"
        )
    return proc.stdout


def run_cache_fixups(
    stager: Stager,
    activated: dict[str, Descriptor],
    closure: dict[str, Path],
    known_prefixes: Sequence[Path],
    implied_by: dict[str, list[str]],
    registry: dict[str, Descriptor],
    tool_runner: ToolRunner,
    warnings: list[str],
) -> None:
    source_strings = [str(prefix) for prefix in known_prefixes]
    for desc in activated.values():
        search, _ = descriptor_search_prefixes(
            desc, closure, known_prefixes, implied_by, registry
        )
        for fixup in desc.cache_fixups:
            target = stager.root / fixup.target_dir
            if not target.is_dir():
                continue
            tool = next(
                (prefix / fixup.tool for prefix in search if (prefix / fixup.tool).is_file()),
                None,
            )
            if tool is None:
                warnings.append(
                    f"{desc.name}: {fixup.tool} not found in any prefix; "
                    f"skipping cache regeneration for {fixup.target_dir}"
                )
                continue
            argv = [str(tool), *[arg.replace("{target}", str(target)) for arg in fixup.args]]
            output = tool_runner(argv)
            cache_path = _resolve_cache_path(stager.root, fixup.cache_file)
            if fixup.stdout_to_cache:
                if cache_path is None:
                    warnings.append(
                        f"{desc.name}: cannot locate {fixup.cache_file} in staging; "
                        "skipping cache write"
                    )
                    continue
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(output, encoding="utf-8")
            if not fixup.relativize:
                continue
            if cache_path is None or not cache_path.is_file():
                warnings.append(
                    f"{desc.name}: expected cache {fixup.cache_file} was not generated"
                )
                continue
            try:
                text = cache_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                warnings.append(
                    f"{desc.name}: {fixup.cache_file} is not UTF-8 text; "
                    "skipping path relativization"
                )
                continue
            rewritten = cachefix.relativize_cache_text(
                text,
                source_prefixes=source_strings,
                cache_file=cache_path.relative_to(stager.root),
            )
            if rewritten != text:
                cache_path.write_text(rewritten, encoding="utf-8")


def scan_for_leaks(staging: Path, source_prefixes: Sequence[Path]) -> list[str]:
    """Scan staged text files for absolute source-prefix paths.

    Candidate files are chosen by a suffix allowlist plus a size cap; binaries
    and oversized files are skipped. Returns one ``file: line`` string per hit.
    """
    needles = [str(prefix) for prefix in source_prefixes]
    problems: list[str] = []
    for path in sorted(staging.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.stat().st_size > LEAK_SCAN_MAX_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in cachefix.find_leaks(text, source_prefixes=needles):
            rel = path.relative_to(staging).as_posix()
            problems.append(f"{rel}: {line.strip()}")
    return problems


@dataclass
class DeployOptions:
    """User-supplied deployment parameters (mirrors the CLI options)."""

    exes: list[Path]
    destdir: Path
    dll_dirs: list[Path] = field(default_factory=list)
    app_tree: Path | None = None
    includes: list[str] = field(default_factory=list)
    icons: str = "full"
    locale_mode: str = "deps"
    locale_langs: list[str] | None = None
    gettext_domains: list[str] = field(default_factory=list)
    zip: bool = False


@dataclass
class DeployReport:
    """Summary of a completed deployment."""

    exes: list[str]
    dlls: dict[str, Path]
    prefixes: list[Path]
    descriptors: list[str]
    collisions: list[str]
    overrides: list[str]
    warnings: list[str]
    staged_files: int
    output_size: int
    zip_path: Path | None = None


def deploy(
    options: DeployOptions,
    *,
    imports_provider: ImportsProvider | None = None,
    tool_runner: ToolRunner | None = None,
    registry: dict[str, Descriptor] | None = None,
) -> DeployReport:
    """Run the full deployment and return a report.

    The fixpoint loop alternates closure resolution and descriptor mirroring:
    DLLs staged by mirroring (gio modules, pixbuf loaders, GStreamer plugins)
    feed back into the closure until no new files appear.
    """
    registry = REGISTRY if registry is None else registry
    tool_runner = default_tool_runner if tool_runner is None else tool_runner
    staging = options.destdir
    staging.mkdir(parents=True, exist_ok=True)
    stager = Stager(staging)
    warnings: list[str] = []

    known_prefixes: list[Path] = []

    def add_known(prefix: Path) -> None:
        if prefix not in known_prefixes:
            known_prefixes.append(prefix)

    # Application content first: the input exes, then the optional install
    # tree, so that app files win over dependency files on collision.
    exes = [Path(os.path.abspath(exe)) for exe in options.exes]
    binary_queue: deque[Path] = deque()
    for exe in exes:
        anchor = derive_prefix(exe)
        add_known(anchor)
        stager.stage_file(exe, anchor, "app")
        binary_queue.append(exe)
    if options.app_tree is not None:
        app_tree = Path(options.app_tree)
        for path in sorted(app_tree.rglob("*")):
            if path.is_file():
                stager.stage_file(path, app_tree, "app-tree")

    resolver = ClosureResolver(dll_dirs=options.dll_dirs, imports_provider=imports_provider)

    icon_filter = icon_file_filter(options.icons)
    mirrored: set[str] = set()
    includes_done = False
    activated: dict[str, Descriptor] = {}
    implied_by: dict[str, list[str]] = {}

    while True:
        progress = False
        while binary_queue:
            binary = binary_queue.popleft()
            for origin in resolver.resolve_imports(binary):
                prefix = derive_prefix(origin)
                add_known(prefix)
                stager.stage_file(origin, prefix, "dll")
                binary_queue.append(origin)
                progress = True

        activated, implied_by = resolve_activation(registry, resolver.closure.keys())
        for name, desc in activated.items():
            if name in mirrored:
                continue
            mirrored.add(name)
            search, anchored = descriptor_search_prefixes(
                desc, resolver.closure, known_prefixes, implied_by, registry
            )
            for rel_dir in desc.mirror_dirs:
                if anchored:
                    # Merge every anchored prefix that contains the directory.
                    for prefix in search:
                        stager.mirror_dir(prefix, rel_dir, name, icon_filter)
                else:
                    # Data-only: first prefix containing the directory wins.
                    for prefix in search:
                        if (prefix / rel_dir).is_dir():
                            stager.mirror_dir(prefix, rel_dir, name, icon_filter)
                            break
            for alternatives in desc.stage_files:
                for prefix in search:
                    hit = next(
                        (prefix / alt for alt in alternatives if (prefix / alt).is_file()),
                        None,
                    )
                    if hit is not None:
                        stager.stage_file(hit, prefix, name)
                        break
            progress = True

        if options.includes and not includes_done:
            includes_done = True
            for rel_dir in options.includes:
                for prefix in known_prefixes:
                    if (prefix / rel_dir).is_dir():
                        stager.mirror_dir(prefix, rel_dir, "include", icon_filter)
                        break
            progress = True

        # Feed newly staged PE files back into the closure.
        for src in stager.new_sources:
            if src.suffix.lower() in PE_SUFFIXES and src not in resolver.scanned:
                binary_queue.append(src)
                progress = True
        stager.new_sources.clear()

        if not progress:
            break

    domains = sorted(
        {domain for desc in activated.values() for domain in desc.gettext_domains}
        | set(options.gettext_domains)
    )
    mirror_locales(
        stager, known_prefixes, domains, mode=options.locale_mode, langs=options.locale_langs
    )

    run_cache_fixups(
        stager,
        activated,
        resolver.closure,
        known_prefixes,
        implied_by,
        registry,
        tool_runner,
        warnings,
    )

    problems = scan_for_leaks(staging, known_prefixes)
    if problems:
        raise LeakError(problems)

    zip_path = None
    if options.zip:
        zip_path = Path(shutil.make_archive(str(staging), "zip", root_dir=staging))

    output_size = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
    return DeployReport(
        exes=[exe.relative_to(derive_prefix(exe)).as_posix() for exe in exes],
        dlls=dict(resolver.closure),
        prefixes=known_prefixes,
        descriptors=list(activated),
        collisions=stager.collisions,
        overrides=stager.overrides,
        warnings=warnings,
        staged_files=len(stager.index),
        output_size=output_size,
        zip_path=zip_path,
    )
