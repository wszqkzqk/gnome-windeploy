"""Tests for locale mirroring on fake prefix trees."""

from gnome_windeploy.engine import Stager, mirror_locales
from util import touch


def _make_locales(prefix):
    touch(prefix / "share/locale/de/LC_MESSAGES/glib20.mo")
    touch(prefix / "share/locale/de/LC_MESSAGES/gtk40.mo")
    touch(prefix / "share/locale/zh_CN/LC_MESSAGES/glib20.mo")
    touch(prefix / "share/locale/fr/LC_MESSAGES/gtk40.mo")


def test_deps_mode_mirrors_only_requested_domains(tmp_path):
    prefix = tmp_path / "p"
    _make_locales(prefix)
    stager = Stager(tmp_path / "out")

    mirror_locales(stager, [prefix], ["glib20"], mode="deps")

    assert set(stager.index) == {
        "share/locale/de/LC_MESSAGES/glib20.mo",
        "share/locale/zh_CN/LC_MESSAGES/glib20.mo",
    }


def test_deps_mode_language_filter(tmp_path):
    prefix = tmp_path / "p"
    _make_locales(prefix)
    stager = Stager(tmp_path / "out")

    mirror_locales(stager, [prefix], ["glib20", "gtk40"], mode="deps", langs=["de"])

    assert set(stager.index) == {
        "share/locale/de/LC_MESSAGES/glib20.mo",
        "share/locale/de/LC_MESSAGES/gtk40.mo",
    }


def test_full_mode_mirrors_whole_locale_tree(tmp_path):
    prefix = tmp_path / "p"
    _make_locales(prefix)
    touch(prefix / "share/locale/locale.alias")
    stager = Stager(tmp_path / "out")

    mirror_locales(stager, [prefix], ["glib20"], mode="full")

    assert set(stager.index) == {
        "share/locale/de/LC_MESSAGES/glib20.mo",
        "share/locale/de/LC_MESSAGES/gtk40.mo",
        "share/locale/zh_CN/LC_MESSAGES/glib20.mo",
        "share/locale/fr/LC_MESSAGES/gtk40.mo",
        "share/locale/locale.alias",
    }


def test_none_mode_mirrors_nothing(tmp_path):
    prefix = tmp_path / "p"
    _make_locales(prefix)
    stager = Stager(tmp_path / "out")

    mirror_locales(stager, [prefix], ["glib20"], mode="none")

    assert stager.index == {}


def test_deps_mode_merges_multiple_prefixes(tmp_path):
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    touch(p1 / "share/locale/de/LC_MESSAGES/glib20.mo", "first")
    touch(p2 / "share/locale/de/LC_MESSAGES/glib20.mo", "second")
    touch(p2 / "share/locale/ja/LC_MESSAGES/glib20.mo", "ja")
    stager = Stager(tmp_path / "out")

    mirror_locales(stager, [p1, p2], ["glib20"], mode="deps")

    assert set(stager.index) == {
        "share/locale/de/LC_MESSAGES/glib20.mo",
        "share/locale/ja/LC_MESSAGES/glib20.mo",
    }
    # Same-relative-path collision: first prefix wins.
    assert (tmp_path / "out/share/locale/de/LC_MESSAGES/glib20.mo").read_text() == "first"
