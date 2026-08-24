"""End-to-end tests against a real MinGW GNOME stack; skipped on other hosts."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from gnome_windeploy.engine import DeployOptions, deploy

PREFIX = Path(
    os.environ.get("GNOME_WINDEPLOY_TEST_PREFIX") or os.environ.get("MSYSTEM_PREFIX") or "."
)


def _have_stack() -> bool:
    if os.name != "nt" or not PREFIX.is_dir():
        return False
    pkgconf = shutil.which("pkg-config") or shutil.which("pkgconf")
    if not shutil.which("gcc") or not pkgconf:
        return False
    probe = subprocess.run([pkgconf, "--exists", "gtk4", "gstreamer-1.0"], check=False)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(not _have_stack(), reason="needs a MinGW GTK4 + GStreamer stack")

HELLO_C = r"""
#include <gtk/gtk.h>
#include <gst/gst.h>
int main(void) {
    g_print("gtk %u.%u.%u\n",
            gtk_get_major_version(), gtk_get_minor_version(), gtk_get_micro_version());
    gst_init(NULL, NULL);
    g_print("gstreamer %s\n", gst_version_string());
    return 0;
}
"""


def _pkg_config(*args: str) -> list[str]:
    pkgconf = shutil.which("pkg-config") or shutil.which("pkgconf")
    out = subprocess.check_output([pkgconf, *args, "gtk4", "gstreamer-1.0"], text=True)
    return out.split()


def test_deploy_real_gtk_gstreamer_app(tmp_path):
    src = tmp_path / "hello.c"
    src.write_text(HELLO_C, encoding="utf-8")
    exe = tmp_path / "app" / "bin" / "hello.exe"
    exe.parent.mkdir(parents=True)
    subprocess.run(
        ["gcc", "-o", str(exe), str(src), *_pkg_config("--cflags", "--libs")], check=True
    )

    gst_inspect = PREFIX / "bin" / "gst-inspect-1.0.exe"
    exes = [exe, gst_inspect] if gst_inspect.is_file() else [exe]
    destdir = tmp_path / "dist"

    report = deploy(
        DeployOptions(exes=exes, destdir=destdir, dll_dirs=[PREFIX / "bin"], zip=True)
    )

    assert (destdir / "bin" / "hello.exe").is_file()
    assert (destdir / "bin" / "libgtk-4-1.dll").is_file()
    assert (destdir / "bin" / "libgstreamer-1.0-0.dll").is_file()
    assert (destdir / "lib" / "gstreamer-1.0").is_dir()
    assert (destdir / "share" / "glib-2.0" / "schemas" / "gschemas.compiled").is_file()
    assert report.zip_path is not None and report.zip_path.is_file()
    assert not [line for line in report.warnings if "libgtk" in line or "libgst" in line]

    staged_inspect = destdir / "bin" / "gst-inspect-1.0.exe"
    if staged_inspect.is_file():
        probe = subprocess.run([str(staged_inspect), "--version"], capture_output=True, check=False)
        assert probe.returncode == 0
