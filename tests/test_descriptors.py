"""Tests for the descriptor registry and activation logic."""

from pathlib import Path

from gnome_windeploy.descriptors import REGISTRY
from gnome_windeploy.engine import descriptor_search_prefixes, resolve_activation


def test_registry_shape():
    assert set(REGISTRY) == {
        "glib",
        "gdkpixbuf",
        "gstreamer",
        "gtk4",
        "gtk3",
        "libadwaita",
        "sharedmime",
        "fontconfig",
    }
    assert REGISTRY["glib"].always
    assert REGISTRY["gtk4"].implies == ("sharedmime",)
    # sharedmime is data-only: no DLL triggers of its own.
    assert REGISTRY["sharedmime"].trigger_dlls == frozenset()
    assert not REGISTRY["sharedmime"].always


def test_glib_is_always_active():
    activated, _ = resolve_activation(REGISTRY, [])
    assert "glib" in activated
    assert len(activated) == 1


def test_trigger_activation_and_implies_transitivity():
    activated, implied_by = resolve_activation(REGISTRY, ["libgtk-4-1.dll", "KERNEL32.DLL"])

    assert set(activated) == {"glib", "gtk4", "sharedmime"}
    assert implied_by["sharedmime"] == ["gtk4"]


def test_implies_chains_resolve_recursively():
    activated, _ = resolve_activation(REGISTRY, ["libadwaita-1-0.dll", "libgtk-4-1.dll"])

    assert {"glib", "gtk4", "sharedmime", "libadwaita"} <= set(activated)


def test_gtk3_does_not_activate_gtk4():
    activated, _ = resolve_activation(REGISTRY, ["libgtk-3-0.dll"])

    assert "gtk3" in activated
    assert "gtk4" not in activated
    assert "sharedmime" in activated


def test_dll_anchored_search_prefixes():
    closure = {"libgtk-4-1.dll": Path("/stack/bin/libgtk-4-1.dll")}
    _, implied_by = resolve_activation(REGISTRY, closure.keys())

    search, anchored = descriptor_search_prefixes(
        REGISTRY["gtk4"], closure, [Path("/hint")], implied_by, REGISTRY
    )

    assert anchored
    assert search == [Path("/stack")]


def test_data_only_search_prefixes_order():
    closure = {"libgtk-4-1.dll": Path("/stack/bin/libgtk-4-1.dll")}
    known = [Path("/hint"), Path("/other")]
    _, implied_by = resolve_activation(REGISTRY, closure.keys())

    search, anchored = descriptor_search_prefixes(
        REGISTRY["sharedmime"], closure, known, implied_by, REGISTRY
    )

    assert not anchored
    assert search == [Path("/stack"), Path("/hint"), Path("/other")]
