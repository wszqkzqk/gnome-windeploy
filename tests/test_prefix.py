"""Tests for DLL-anchored prefix derivation."""

from pathlib import Path

from gnome_windeploy.prefix import derive_prefix


def test_bin_anchor():
    assert derive_prefix(Path("/ucrt64/bin/libgtk-4-1.dll")) == Path("/ucrt64")


def test_lib_anchor():
    assert derive_prefix(Path("/ucrt64/lib/foo.dll")) == Path("/ucrt64")


def test_anchor_dir_name_is_case_insensitive():
    assert derive_prefix(Path("C:/gnome-custom/BIN/x.dll")) == Path("C:/gnome-custom")
    assert derive_prefix(Path("C:/gnome-custom/Lib/x.dll")) == Path("C:/gnome-custom")


def test_nonstandard_anchor_is_own_directory():
    assert derive_prefix(Path("/odd/stuff/x.dll")) == Path("/odd/stuff")
