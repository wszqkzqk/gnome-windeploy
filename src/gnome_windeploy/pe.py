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

# Windows system DLLs that are never bundled. Stored without the ".dll" suffix,
# except where the canonical name uses a different extension (winspool.drv).
SYSTEM_DLL_BASENAMES: frozenset[str] = frozenset(
    {
        "advapi32",
        "avrt",
        "bcrypt",
        "cfgmgr32",
        "combase",
        "comctl32",
        "comdlg32",
        "crypt32",
        "d3d9",
        "d3d11",
        "d3d12",
        "dbghelp",
        "dnsapi",
        "dwmapi",
        "dwrite",
        "dxgi",
        "gdi32",
        "gdiplus",
        "glu32",
        "imm32",
        "iphlpapi",
        "kernel32",
        "msasn1",
        "msimg32",
        "msvcrt",
        "netapi32",
        "normaliz",
        "ntdll",
        "ole32",
        "oleacc",
        "oleaut32",
        "oledlg",
        "opengl32",
        "powrprof",
        "psapi",
        "rpcrt4",
        "secur32",
        "setupapi",
        "shcore",
        "shell32",
        "shlwapi",
        "sspicli",
        "ucrtbase",
        "user32",
        "userenv",
        "uxtheme",
        "version",
        "winhttp",
        "winmm",
        "winspool.drv",
        "wintrust",
        "wlanapi",
        "ws2_32",
        "wtsapi32",
    }
)

# Prefixes of virtual API-set DLL names resolved internally by the Windows loader.
SYSTEM_DLL_PREFIXES: tuple[str, ...] = (
    "api-ms-win-",
    "api-ms-wcr-",
    "ext-ms-win-",
    "ext-ms-wcr-",
)

# A provider maps a binary path to the names of the DLLs it imports.
ImportsProvider = Callable[[Path], Iterable[str]]


class MissingDependencyError(Exception):
    """A non-system DLL import could not be resolved in any candidate directory."""

    def __init__(self, dll_name: str, importer: Path) -> None:
        self.dll_name = dll_name
        self.importer = Path(importer)
        super().__init__(f"cannot resolve dependency {dll_name!r} imported by {self.importer}")


def is_system_dll(name: str) -> bool:
    """Return True if *name* (a DLL file name, any casing) is a Windows system DLL."""
    lowered = name.lower()
    if lowered.startswith(SYSTEM_DLL_PREFIXES):
        return True
    base = lowered[:-4] if lowered.endswith(".dll") else lowered
    return base in SYSTEM_DLL_BASENAMES or lowered in SYSTEM_DLL_BASENAMES


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


def _list_files_lower(directory: Path) -> dict[str, Path]:
    """Map lower-cased file name to path for every file directly in *directory*."""
    try:
        entries = list(directory.iterdir())
    except OSError:
        return {}
    return {entry.name.lower(): entry for entry in entries if entry.is_file()}


class ClosureResolver:
    """Incrementally resolve PE imports following Windows loader search order.

    Candidate search directories start with the importing binary's own
    directory; every newly resolved DLL adds its own directory to the
    candidates; user-supplied ``dll_dirs`` are appended last. DLL name matching
    is case-insensitive.
    """

    def __init__(
        self,
        *,
        dll_dirs: Iterable[Path] = (),
        imports_provider: ImportsProvider | None = None,
    ) -> None:
        self._provider = imports_provider or default_imports_provider
        self.candidates: list[Path] = []
        self._candidate_keys: set[str] = set()
        self._dir_cache: dict[Path, dict[str, Path]] = {}
        self.closure: dict[str, Path] = {}
        self.scanned: set[Path] = set()
        for directory in dll_dirs:
            self.add_candidate(Path(directory))

    def add_candidate(self, directory: Path) -> None:
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
        """Resolve one binary's imports; return the newly resolved DLL origins.

        Raises :class:`MissingDependencyError` for the first unresolvable
        import that is not a Windows system DLL.
        """
        binary = Path(binary)
        if binary in self.scanned:
            return []
        self.scanned.add(binary)
        search_dirs = [binary.parent]
        search_dirs.extend(c for c in self.candidates if c != binary.parent)
        newly: list[Path] = []
        for name in self._provider(binary):
            lower = name.lower()
            if lower in self.closure or is_system_dll(lower):
                continue
            found = self._find(lower, search_dirs)
            if found is None:
                raise MissingDependencyError(name, binary)
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
    imports_provider: ImportsProvider | None = None,
) -> dict[str, Path]:
    """Compute the transitive DLL dependency closure over *seeds*.

    Returns an insertion-ordered mapping of lower-cased DLL name to its origin
    path. Unresolvable Windows system DLLs are skipped silently; any other
    unresolvable import raises :class:`MissingDependencyError` naming the DLL
    and the binary that imports it.
    """
    resolver = ClosureResolver(dll_dirs=dll_dirs, imports_provider=imports_provider)
    resolver.scan(seeds)
    return dict(resolver.closure)
