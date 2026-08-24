"""Tests for the descriptor registry and activation logic."""

from pathlib import Path

from gnome_windeploy.descriptors import REGISTRY
from gnome_windeploy.descriptors.base import Descriptor
from gnome_windeploy.engine import descriptor_search_prefixes, resolve_activation


def synthetic_registry():
    gtk = Descriptor(name="gtk", trigger_dlls=frozenset({"libgtk.dll"}), implies=("data",))
    data = Descriptor(name="data", mirror_dirs=("share/data",))
    return {"gtk": gtk, "data": data}


def test_glib_is_always_active():
    activated, _ = resolve_activation(REGISTRY, [])
    assert "glib" in activated
    assert len(activated) == 1


def test_trigger_activation():
    activated, _ = resolve_activation(REGISTRY, ["libgtk-4-1.dll", "KERNEL32.DLL"])

    assert set(activated) == {"glib", "gtk4"}


def test_multiple_triggers_activate_independently():
    activated, _ = resolve_activation(REGISTRY, ["libadwaita-1-0.dll", "libgtk-4-1.dll"])

    assert {"glib", "gtk4", "libadwaita"} <= set(activated)


def test_gtk3_does_not_activate_gtk4():
    activated, _ = resolve_activation(REGISTRY, ["libgtk-3-0.dll"])

    assert "gtk3" in activated
    assert "gtk4" not in activated


def test_implies_and_data_only_activation():
    activated, implied_by = resolve_activation(synthetic_registry(), ["libgtk.dll"])

    assert set(activated) == {"gtk", "data"}
    assert implied_by["data"] == ["gtk"]


def test_dll_anchored_search_prefixes():
    closure = {"libgtk-4-1.dll": Path("/stack/bin/libgtk-4-1.dll")}
    _, implied_by = resolve_activation(REGISTRY, closure.keys())

    search, anchored = descriptor_search_prefixes(
        REGISTRY["gtk4"], closure, [Path("/hint")], implied_by, REGISTRY
    )

    assert anchored
    assert search == [Path("/stack")]


def test_data_only_search_prefixes_order():
    registry = synthetic_registry()
    closure = {"libgtk.dll": Path("/stack/bin/libgtk.dll")}
    known = [Path("/hint"), Path("/other")]
    _, implied_by = resolve_activation(registry, closure.keys())

    search, anchored = descriptor_search_prefixes(
        registry["data"], closure, known, implied_by, registry
    )

    assert not anchored
    assert search == [Path("/stack"), Path("/hint"), Path("/other")]
