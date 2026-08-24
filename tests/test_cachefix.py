"""Tests for cache relativization and the leak scanner (pure text helpers)."""

from pathlib import Path

from gnome_windeploy.cachefix import find_leaks, relativize_cache_text

PREFIX = "C:\\msys64\\ucrt64"
CACHE_FILE = Path("lib/gdk-pixbuf-2.0/2.10.0/loaders.cache")


def test_relativize_mixed_separators_and_case():
    text = (
        '"C:/msys64/ucrt64/lib/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-png.dll"\n'
        '"C:\\MSYS64\\UCRT64\\lib\\gdk-pixbuf-2.0\\2.10.0\\loaders\\libpixbufloader-svg.dll"\n'
    )

    out = relativize_cache_text(text, source_prefixes=[PREFIX], cache_file=CACHE_FILE)

    assert out == (
        '"loaders/libpixbufloader-png.dll"\n"loaders/libpixbufloader-svg.dll"\n'
    )


def test_relativize_collapses_to_dot_when_next_to_cache():
    text = "C:/msys64/ucrt64/lib/gio/modules/libgiognutls.dll\n"

    out = relativize_cache_text(
        text,
        source_prefixes=[PREFIX],
        cache_file=Path("lib/gio/modules/giomodule.cache"),
    )

    assert out == "libgiognutls.dll\n"


def test_relativize_cache_at_staging_root():
    text = "C:/msys64/ucrt64/lib/x.dll\n"

    out = relativize_cache_text(text, source_prefixes=[PREFIX], cache_file=Path("giomodule.cache"))

    assert out == "lib/x.dll\n"


def test_relativize_bare_prefix_points_at_staging_root():
    text = "prefix=C:/msys64/ucrt64\n"

    out = relativize_cache_text(
        text, source_prefixes=[PREFIX], cache_file=Path("lib/pkgconfig/foo.pc")
    )

    assert out == "prefix=../..\n"


def test_relativize_longer_prefix_wins():
    text = "C:/msys64/ucrt64/custom/share/x.dat\n"

    out = relativize_cache_text(
        text,
        source_prefixes=["C:/msys64", "C:/msys64/ucrt64/custom"],
        cache_file=Path("share/x.cache"),
    )

    assert out == "x.dat\n"


def test_relativize_does_not_match_longer_unrelated_paths():
    text = "C:/msys64/ucrt64-extra/bin/x.dll\n"

    out = relativize_cache_text(text, source_prefixes=["C:/msys64/ucrt64"], cache_file=Path("c"))

    # "ucrt64-extra" is a different directory: the prefix must not match there.
    assert out == text


def test_find_leaks_reports_offending_lines():
    text = (
        "ok line\n"
        "C:/msys64/ucrt64/lib/x.dll\n"
        "also ok\n"
        "c:\\MSYS64\\UCRT64\\share\\y\n"
    )

    hits = find_leaks(text, source_prefixes=[PREFIX])

    assert hits == ["C:/msys64/ucrt64/lib/x.dll", "c:\\MSYS64\\UCRT64\\share\\y"]


def test_find_leaks_clean_text():
    assert find_leaks("loaders/foo.dll\n../share/x\n", source_prefixes=[PREFIX]) == []
