"""End-to-end engine tests on synthetic fake prefix trees (no real PE files)."""

import pytest

from gnome_windeploy import pe
from gnome_windeploy.engine import DeployOptions, LeakError, Stager, deploy
from util import provider_of, touch


def build_fake_stack(prefix):
    """Create a synthetic GNOME prefix; return (app exe, import graph, fake System32)."""
    app = touch(prefix / "bin/app.exe")
    gtk = touch(prefix / "bin/libgtk-4-1.dll")
    glib = touch(prefix / "bin/libglib-2.0-0.dll")
    gdkpixbuf = touch(prefix / "bin/libgdk_pixbuf-2.0-0.dll")
    gio_module = touch(prefix / "lib/gio/modules/libgiognutls.dll")
    loader = touch(prefix / "lib/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-png.dll")
    touch(prefix / "bin/glib-compile-schemas.exe")
    touch(prefix / "bin/gio-querymodules.exe")
    touch(prefix / "bin/gdk-pixbuf-query-loaders.exe")
    touch(prefix / "share/glib-2.0/schemas/org.example.gschema.xml", "<schemalist/>")
    touch(prefix / "share/icons/Adwaita/index.theme", "[Icon Theme]")
    touch(prefix / "share/icons/Adwaita/scalable/apps/foo.svg", "<svg/>")
    touch(prefix / "share/icons/Adwaita/16x16/apps/foo.png", "png")
    touch(prefix / "share/icons/hicolor/index.theme", "[Icon Theme]")
    touch(prefix / "share/mime/packages/freedesktop.org.xml", "<mime-info/>")
    touch(prefix / "share/mime/globs", "dep version")
    touch(prefix / "share/locale/de/LC_MESSAGES/glib20.mo")
    touch(prefix / "share/locale/de/LC_MESSAGES/gtk40.mo")
    touch(prefix / "share/locale/zh_CN/LC_MESSAGES/glib20.mo")
    graph = {
        app: ["libgtk-4-1.dll", "kernel32.dll"],
        gtk: ["libglib-2.0-0.dll", "libgdk_pixbuf-2.0-0.dll"],
        gdkpixbuf: ["libglib-2.0-0.dll"],
        glib: [],
        gio_module: ["libglib-2.0-0.dll"],
        loader: ["libgdk_pixbuf-2.0-0.dll", "libglib-2.0-0.dll"],
    }
    system32 = prefix.parent / "System32"
    touch(system32 / "kernel32.dll")
    return app, graph, system32


def make_tool_runner(prefix):
    """Stub cache tools: emulate their file/stdout output without executing."""

    def runner(argv):
        tool = argv[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if tool == "glib-compile-schemas.exe":
            with open(f"{argv[1]}/gschemas.compiled", "wb") as handle:
                handle.write(b"\x00compiled")
            return ""
        if tool == "gio-querymodules.exe":
            with open(f"{argv[1]}/giomodule.cache", "w", encoding="utf-8") as handle:
                handle.write(f"{prefix}/lib/gio/modules/libgiognutls.dll\n")
            return ""
        if tool == "gdk-pixbuf-query-loaders.exe":
            return (
                f'"{prefix}/lib/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-png.dll"\n'
                '"png 5 gdk-pixbuf The PNG image format"\n'
            )
        raise AssertionError(f"unexpected tool call: {argv}")

    return runner


def test_end_to_end_synthetic_stack(monkeypatch, tmp_path):
    prefix = tmp_path / "stack"
    app, graph, system32 = build_fake_stack(prefix)
    monkeypatch.setattr(pe, "default_system_dirs", lambda: [system32])
    app_tree = tmp_path / "apptree"
    touch(app_tree / "share/mime/globs", "app version")
    destdir = tmp_path / "dist"

    report = deploy(
        DeployOptions(exes=[app], destdir=destdir, app_tree=app_tree),
        imports_provider=provider_of(graph),
        tool_runner=make_tool_runner(prefix),
    )

    assert (destdir / "bin/app.exe").is_file()
    assert (destdir / "bin/libgtk-4-1.dll").is_file()
    assert (destdir / "bin/libglib-2.0-0.dll").is_file()
    assert (destdir / "bin/libgdk_pixbuf-2.0-0.dll").is_file()
    assert set(report.dlls) == {
        "libgtk-4-1.dll",
        "libglib-2.0-0.dll",
        "libgdk_pixbuf-2.0-0.dll",
    }

    assert (destdir / "lib/gio/modules/libgiognutls.dll").is_file()
    assert (destdir / "lib/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-png.dll").is_file()

    assert (destdir / "share/glib-2.0/schemas/gschemas.compiled").is_file()
    gio_cache = (destdir / "lib/gio/modules/giomodule.cache").read_text(encoding="utf-8")
    assert gio_cache == "libgiognutls.dll\n"
    loaders_cache = (
        destdir / "lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
    ).read_text(encoding="utf-8")
    assert '"loaders/libpixbufloader-png.dll"' in loaders_cache
    assert str(prefix) not in loaders_cache

    assert (destdir / "share/icons/Adwaita/index.theme").is_file()
    assert (destdir / "share/icons/Adwaita/16x16/apps/foo.png").is_file()
    assert (destdir / "share/mime/packages/freedesktop.org.xml").is_file()
    assert (destdir / "share/locale/de/LC_MESSAGES/glib20.mo").is_file()
    assert (destdir / "share/locale/de/LC_MESSAGES/gtk40.mo").is_file()
    assert (destdir / "share/locale/zh_CN/LC_MESSAGES/glib20.mo").is_file()
    assert not (destdir / "share/locale/zh_CN/LC_MESSAGES/gtk40.mo").exists()

    assert (destdir / "share/mime/globs").read_text(encoding="utf-8") == "app version"
    assert any("share/mime/globs" in line for line in report.overrides)

    assert report.exes == ["bin/app.exe"]
    assert report.prefixes == [prefix]
    assert set(report.descriptors) >= {"glib", "gtk4", "gdkpixbuf", "sharedmime"}
    assert report.collisions == []
    assert report.warnings == []
    assert report.output_size > 0


def test_nonstandard_layout_anchors_own_directory(tmp_path):
    tools = tmp_path / "odd" / "tools"
    app = touch(tools / "app.exe")
    glib = touch(tools / "libglib-2.0-0.dll")
    touch(tools / "share/glib-2.0/schemas/x.gschema.xml", "<schemalist/>")
    graph = {app: ["libglib-2.0-0.dll"], glib: []}
    destdir = tmp_path / "dist"

    def no_tool(argv):
        raise AssertionError(f"unexpected tool call: {argv}")

    report = deploy(
        DeployOptions(exes=[app], destdir=destdir),
        imports_provider=provider_of(graph),
        tool_runner=no_tool,
    )

    assert (destdir / "app.exe").is_file()
    assert (destdir / "libglib-2.0-0.dll").is_file()
    assert (destdir / "share/glib-2.0/schemas/x.gschema.xml").is_file()
    assert report.prefixes == [tools]
    assert any("glib-compile-schemas" in line for line in report.warnings)


def test_leak_scan_raises_on_absolute_paths(tmp_path):
    prefix = tmp_path / "p"
    app = touch(prefix / "bin/app.exe")
    graph = {app: []}
    app_tree = tmp_path / "apptree"
    touch(app_tree / "bad.cache", f"{prefix}/lib/forgotten.dll\n")

    with pytest.raises(LeakError) as excinfo:
        deploy(
            DeployOptions(exes=[app], destdir=tmp_path / "dist", app_tree=app_tree),
            imports_provider=provider_of(graph),
            tool_runner=make_tool_runner(prefix),
        )

    assert any("bad.cache" in problem for problem in excinfo.value.problems)


def test_stager_collision_first_wins(tmp_path):
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    first = touch(p1 / "share/x/y.txt", "one")
    second = touch(p2 / "share/x/y.txt", "two")
    stager = Stager(tmp_path / "out")

    assert stager.stage_file(first, p1, "a") is not None
    assert stager.stage_file(second, p2, "b") is None

    assert (tmp_path / "out/share/x/y.txt").read_text(encoding="utf-8") == "one"
    assert len(stager.collisions) == 1
    assert "share/x/y.txt" in stager.collisions[0]


def test_stager_identical_content_is_not_a_collision(tmp_path):
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    first = touch(p1 / "share/x/y.txt", "same")
    second = touch(p2 / "share/x/y.txt", "same")
    stager = Stager(tmp_path / "out")

    stager.stage_file(first, p1, "a")
    stager.stage_file(second, p2, "b")

    assert stager.collisions == []
