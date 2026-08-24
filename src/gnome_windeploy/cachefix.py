"""Pure-text helpers for cache relativization and absolute-path leak detection."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Sequence
from pathlib import Path

# A path must not be immediately preceded by a word character or separator, so
# that a prefix never matches the tail of a longer unrelated path.
_LEFT_BOUNDARY = r"(?<![\w/\\])"

# Path characters after the prefix: anything but whitespace or quoting/piping
# characters that would terminate a path inside a cache/config line. The tail
# must begin with a separator, and the whole match must not end mid-component
# (so that e.g. "ucrt64-extra" never matches the prefix "ucrt64").
_TAIL = r"([/\\][^\s\"'<>|]*)?(?![\w.-])"


def _normalize(prefix: str) -> str:
    """Normalize a prefix for matching: POSIX separators, no trailing slash."""
    return prefix.replace("\\", "/").rstrip("/")


def _prefix_regex(normalized_prefix: str) -> re.Pattern[str]:
    """Build a regex matching the prefix with either separator style, any case."""
    body = "[/\\\\]".join(re.escape(segment) for segment in normalized_prefix.split("/"))
    return re.compile(_LEFT_BOUNDARY + body + _TAIL, re.IGNORECASE)


def relativize_cache_text(
    text: str, *, source_prefixes: Sequence[str], cache_file: Path
) -> str:
    """Rewrite absolute source-prefix paths in *text* as relative paths.

    ``cache_file`` is the cache file's path relative to the staging root. Every
    occurrence of ``<prefix>/<tail>`` (either separator style, any casing) is
    replaced by the POSIX relative path from the cache file's own directory to
    ``<staging-root>/<tail>``. A bare prefix occurrence becomes the relative
    path from the cache file's directory to the staging root.
    """
    cache_location = cache_file.as_posix()
    cache_dir = cache_location.rsplit("/", 1)[0] if "/" in cache_location else "."
    prefixes = sorted(
        {normalized for raw in source_prefixes if (normalized := _normalize(raw))},
        key=len,
        reverse=True,
    )
    result = text
    for prefix in prefixes:
        pattern = _prefix_regex(prefix)

        def rewrite(match: re.Match[str], prefix: str = prefix) -> str:
            tail = _normalize(match.group(0))[len(prefix) :].lstrip("/")
            if not tail:
                return posixpath.relpath(".", cache_dir)
            return posixpath.relpath(tail, cache_dir)

        result = pattern.sub(rewrite, result)
    return result


def find_leaks(text: str, *, source_prefixes: Sequence[str]) -> list[str]:
    """Return the lines of *text* that still contain an absolute source prefix.

    Matching is case-insensitive and tolerant of either path separator.
    """
    needles = [
        needle
        for raw in source_prefixes
        if (needle := _normalize(raw).casefold())
    ]
    hits: list[str] = []
    for line in text.splitlines():
        folded = line.replace("\\", "/").casefold()
        if any(needle in folded for needle in needles):
            hits.append(line)
    return hits
