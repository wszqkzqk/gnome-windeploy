"""Tests for PE dependency closure (fake import graphs, no real PE files)."""

import pytest

from gnome_windeploy import pe
from gnome_windeploy.pe import (
    MissingDependencyError,
    compute_closure,
    default_imports_provider,
    is_system_dll,
)
from util import provider_of, touch


def test_transitive_closure_and_dll_dirs(tmp_path):
    prefix = tmp_path / "prefix"
    app = touch(prefix / "bin" / "app.exe")
    b = touch(prefix / "bin" / "b.dll")
    c = touch(prefix / "lib" / "c.dll")
    graph = {app: ["b.dll"], b: ["c.dll"], c: []}

    closure = compute_closure([app], dll_dirs=[prefix / "lib"], imports_provider=provider_of(graph))

    assert closure == {"b.dll": b, "c.dll": c}


def test_case_insensitive_matching(tmp_path):
    bindir = tmp_path / "bin"
    app = touch(bindir / "app.exe")
    dep = touch(bindir / "DeP.DLL")
    graph = {app: ["dEp.dll"], dep: []}

    closure = compute_closure([app], imports_provider=provider_of(graph))

    # The closure key is the lower-cased import name; the origin keeps its case.
    assert closure == {"dep.dll": dep}


def test_importer_own_directory_wins(tmp_path):
    dir1 = tmp_path / "one"
    dir2 = tmp_path / "two"
    app = touch(dir1 / "app.exe")
    touch(dir1 / "nested.dll")
    dep = touch(dir2 / "dep.dll")
    nested_in_dir2 = touch(dir2 / "nested.dll")
    graph = {app: ["dep.dll"], dep: ["nested.dll"], nested_in_dir2: []}

    closure = compute_closure([app], dll_dirs=[dir2], imports_provider=provider_of(graph))

    # dep.dll lives in dir2, so dir2 is searched before dir1 for its imports.
    assert closure["dep.dll"] == dep
    assert closure["nested.dll"] == nested_in_dir2


def test_newly_resolved_dll_adds_candidate_dir(tmp_path):
    dir1 = tmp_path / "one"
    dir2 = tmp_path / "two"
    app = touch(dir1 / "app.exe")
    dep = touch(dir2 / "dep.dll")
    leaf = touch(dir2 / "leaf.dll")
    graph = {app: ["dep.dll"], dep: ["leaf.dll"], leaf: []}

    # leaf.dll is only reachable because dep.dll's dir became a candidate.
    closure = compute_closure([app], dll_dirs=[dir2], imports_provider=provider_of(graph))

    assert closure == {"dep.dll": dep, "leaf.dll": leaf}


@pytest.mark.parametrize(
    "name",
    [
        "kernel32.dll",
        "KERNEL32.DLL",
        "msvcrt.dll",
        "ucrtbase.dll",
        "winspool.drv",
        "api-ms-win-core-file-l1-1-0.dll",
        "api-ms-wcr-heap-l1-1-0.dll",
        "ext-ms-win-ntuser-window-l1-1-0.dll",
    ],
)
def test_system_dll_detection(name):
    assert is_system_dll(name)


@pytest.mark.parametrize("name", ["libgtk-4-1.dll", "libglib-2.0-0.dll", "zlib1.dll"])
def test_non_system_dll_detection(name):
    assert not is_system_dll(name)


def test_system_dlls_are_skipped(tmp_path):
    bindir = tmp_path / "bin"
    app = touch(bindir / "app.exe")
    graph = {app: ["kernel32.dll", "api-ms-win-core-x-l1-1-0.dll", "ntdll.dll"]}

    closure = compute_closure([app], imports_provider=provider_of(graph))

    assert closure == {}


def test_missing_dll_error_names_dll_and_importer(tmp_path):
    bindir = tmp_path / "bin"
    app = touch(bindir / "app.exe")
    graph = {app: ["nonexistent.dll"]}

    with pytest.raises(MissingDependencyError) as excinfo:
        compute_closure([app], imports_provider=provider_of(graph))

    message = str(excinfo.value)
    assert "nonexistent.dll" in message
    assert "app.exe" in message


def test_default_provider_merges_regular_and_delay_imports(monkeypatch, tmp_path):
    fake = touch(tmp_path / "x.exe")
    monkeypatch.setattr(
        pe,
        "get_pe_imports",
        lambda path: (frozenset({"regular.dll"}), frozenset({"delay.dll"})),
    )

    assert default_imports_provider(fake) == ["delay.dll", "regular.dll"]
