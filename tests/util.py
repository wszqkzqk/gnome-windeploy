"""Shared helpers for building synthetic prefix trees in tests."""

from collections.abc import Callable
from pathlib import Path


def touch(path: Path, content: str | bytes = b"") -> Path:
    """Create *path* (with parents) containing *content*; return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)
    return path


def provider_of(graph: dict) -> Callable:
    """Turn a {path: [dll names]} fake import graph into an imports_provider."""
    return lambda path: graph.get(path, [])
