"""PE import parsing and Windows-loader-style dependency closure.

Only :func:`get_pe_imports` parses PE files (via pefile); everything else
operates on plain paths and an injectable ``imports_provider`` so tests can
run without real PE binaries.
"""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Callable, Iterable
from pathlib import Path

import pefile

# Virtual API-set name prefixes resolved internally by the Windows loader;
# they never exist as files to bundle.
API_SET_PREFIXES: tuple[str, ...] = (
    "api-ms-win-",
    "api-ms-wcr-",
    "ext-ms-win-",
    "ext-ms-wcr-",
)

# A provider maps a binary path to the names of the DLLs it imports.
ImportsProvider = Callable[[Path], Iterable[str]]


def is_api_set_dll(name: str) -> bool:
    """Return True for virtual API-set names the Windows loader resolves internally."""
    return name.lower().startswith(API_SET_PREFIXES)


def default_system_dirs() -> list[Path]:
    """Windows system directories used to classify (never bundle) OS-provided DLLs."""
    system_root = os.environ.get("SystemRoot")
    if os.name != "nt" or not system_root:
        return []
    root = Path(system_root)
    return [directory for directory in (root / "System32", root / "SysWOW64") if directory.is_dir()]


def get_pe_imports(path: Path) -> tuple[frozenset[str], frozenset[str]]:
    """Parse a PE file and return ``(regular imports, delay-load imports)``.

    Both sets contain DLL file names exactly as written in the import tables.
    """
    regular: set[str] = set()
    delay: set[str] = set()
    with pefile.PE(str(path), fast_load=True) as pe:
        pe.parse_data_directories(
            directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
            ]
        )
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            regular.add(entry.dll.decode("ascii", errors="replace"))
        for entry in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []):
            delay.add(entry.dll.decode("ascii", errors="replace"))
    return frozenset(regular), frozenset(delay)


def default_imports_provider(path: Path) -> list[str]:
    """Return the combined regular and delay-load imports of a PE binary."""
    regular, delay = get_pe_imports(path)
    return sorted(regular | delay)


def _norm(path: Path) -> Path:
    """Canonicalize *path* so user input (e.g. cygpath -m forward slashes) and
    filesystem results (``iterdir``, OS-native separators) compare equal."""
    return Path(os.path.normpath(path))


def _list_files_lower(directory: Path) -> dict[str, Path]:
    """Map lower-cased file name to path for every file directly in *directory*."""
    try:
        entries = list(directory.iterdir())
    except OSError:
        return {}
    return {entry.name.lower(): _norm(entry) for entry in entries if entry.is_file()}


class ClosureResolver:
    """Incrementally resolve PE imports following Windows loader search order.

    Imports that no candidate directory resolves are skipped when they are
    virtual API sets or are found in ``system_dirs``; anything else lands in
    ``warnings``.
    """

    def __init__(
        self,
        *,
        dll_dirs: Iterable[Path] = (),
        system_dirs: Iterable[Path] | None = None,
        imports_provider: ImportsProvider | None = None,
    ) -> None:
        self._provider = imports_provider or default_imports_provider
        self.candidates: list[Path] = []
        self._candidate_keys: set[str] = set()
        self._dir_cache: dict[Path, dict[str, Path]] = {}
        self.closure: dict[str, Path] = {}
        self.scanned: set[Path] = set()
        self.warnings: list[str] = []
        if system_dirs is None:
            system_dirs = default_system_dirs()
        self.system_dirs = [_norm(Path(directory)) for directory in system_dirs]
        for directory in dll_dirs:
            self.add_candidate(Path(directory))

    def add_candidate(self, directory: Path) -> None:
        directory = _norm(directory)
        key = os.path.normcase(str(directory))
        if key not in self._candidate_keys:
            self._candidate_keys.add(key)
            self.candidates.append(directory)

    def _find(self, lower_name: str, search_dirs: Iterable[Path]) -> Path | None:
        for directory in search_dirs:
            if directory not in self._dir_cache:
                self._dir_cache[directory] = _list_files_lower(directory)
            hit = self._dir_cache[directory].get(lower_name)
            if hit is not None:
                return hit
        return None

    def resolve_imports(self, binary: Path) -> list[Path]:
        """Resolve one binary's imports; return the newly resolved DLL origins."""
        binary = _norm(Path(binary))
        if binary in self.scanned:
            return []
        self.scanned.add(binary)
        search_dirs = [binary.parent]
        search_dirs.extend(c for c in self.candidates if c != binary.parent)
        newly: list[Path] = []
        for name in self._provider(binary):
            lower = name.lower()
            if lower in self.closure or is_api_set_dll(lower):
                continue
            found = self._find(lower, search_dirs)
            if found is None:
                if self._find(lower, self.system_dirs) is None:
                    self.warnings.append(f"unresolved dependency {name!r} imported by {binary}")
                continue
            self.closure[lower] = found
            self.add_candidate(found.parent)
            newly.append(found)
        return newly

    def scan(self, seeds: Iterable[Path]) -> None:
        """Resolve the full transitive closure over *seeds*."""
        queue = deque(seeds)
        while queue:
            queue.extend(self.resolve_imports(queue.popleft()))


def compute_closure(
    seeds: Iterable[Path],
    *,
    dll_dirs: Iterable[Path] = (),
    system_dirs: Iterable[Path] | None = None,
    imports_provider: ImportsProvider | None = None,
) -> dict[str, Path]:
    """Compute the transitive DLL dependency closure over *seeds*.

    Returns an insertion-ordered mapping of lower-cased DLL name to origin
    path; skipped and unresolved imports are dropped (inspect warnings via
    :class:`ClosureResolver` instead).
    """
    resolver = ClosureResolver(
        dll_dirs=dll_dirs, system_dirs=system_dirs, imports_provider=imports_provider
    )
    resolver.scan(seeds)
    return dict(resolver.closure)
