"""NSIS script rendering and installer integration tests."""

import shutil
from pathlib import Path

import pytest

from gnome_windeploy import nsis
from gnome_windeploy.engine import DeployError, DeployOptions, deploy
from util import provider_of, touch


def test_render_script_contains_installer_metadata(tmp_path):
    script = nsis.render_script(
        app_name="Hello App",
        version="1.2.3",
        bundle=tmp_path / "dist",
        out_file=tmp_path / "dist-setup.exe",
        main_exe="bin/hello.exe",
    )

    assert '!define APP_NAME "Hello App"' in script
    assert '!define APP_VERSION "1.2.3"' in script
    assert '"$INSTDIR\\bin\\hello.exe"' in script
    assert "MUI_PAGE_LICENSE" not in script


def test_render_script_with_license_page(tmp_path):
    license_file = touch(tmp_path / "LICENSE", "text")

    script = nsis.render_script(
        app_name="x",
        version="0",
        bundle=tmp_path,
        out_file=tmp_path / "s.exe",
        main_exe="app.exe",
        license_file=license_file,
    )

    assert f'!insertmacro MUI_PAGE_LICENSE "{license_file}"' in script


def test_nsis_installer_built_after_bundle(monkeypatch, tmp_path):
    prefix = tmp_path / "stack"
    app = touch(prefix / "bin/app.exe")
    makensis = str(touch(tmp_path / "tools/makensis"))
    monkeypatch.setattr(shutil, "which", lambda name: makensis)
    calls = []

    def fake_runner(argv):
        calls.append(list(argv))
        Path(argv[1]).with_suffix(".exe").write_bytes(b"")
        return ""

    report = deploy(
        DeployOptions(exes=[app], destdir=tmp_path / "dist", nsis=True),
        imports_provider=provider_of({app: []}),
        tool_runner=fake_runner,
    )

    script = tmp_path / "dist-setup.nsi"
    assert calls == [[makensis, str(script)]]
    assert '!define APP_NAME "app"' in script.read_text(encoding="utf-8")
    assert report.installer_path == tmp_path / "dist-setup.exe"
    assert report.installer_path.is_file()


def test_nsis_without_makensis_fails(monkeypatch, tmp_path):
    prefix = tmp_path / "stack"
    app = touch(prefix / "bin/app.exe")
    monkeypatch.setattr(shutil, "which", lambda name: None)

    with pytest.raises(DeployError):
        deploy(
            DeployOptions(exes=[app], destdir=tmp_path / "dist", nsis=True),
            imports_provider=provider_of({app: []}),
            tool_runner=lambda argv: "",
        )
