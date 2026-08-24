"""NSIS installer script rendering: a thin shell over the finished bundle."""

from __future__ import annotations

from pathlib import Path

TEMPLATE = """\
Unicode true
!define APP_NAME "{app_name}"
!define APP_VERSION "{version}"
!define UNINST_KEY "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}"

Name "${{APP_NAME}}"
OutFile "{out_file}"
InstallDir "$PROGRAMFILES64\\${{APP_NAME}}"

!include "MUI2.nsh"
{license_page}!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"
    File /r "{bundle}\\*"
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    CreateDirectory "$SMPROGRAMS\\${{APP_NAME}}"
    CreateShortcut "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk" "$INSTDIR\\{main_exe}"
    WriteRegStr HKLM "${{UNINST_KEY}}" "DisplayName" "${{APP_NAME}}"
    WriteRegStr HKLM "${{UNINST_KEY}}" "DisplayVersion" "${{APP_VERSION}}"
    WriteRegStr HKLM "${{UNINST_KEY}}" "UninstallString" "$INSTDIR\\uninstall.exe"
SectionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk"
    RMDir "$SMPROGRAMS\\${{APP_NAME}}"
    DeleteRegKey HKLM "${{UNINST_KEY}}"
SectionEnd
"""


def render_script(
    *,
    app_name: str,
    version: str,
    bundle: Path,
    out_file: Path,
    main_exe: str,
    license_file: Path | None = None,
) -> str:
    """Render the NSIS script installing *bundle* with a Start Menu shortcut."""
    license_page = f'!insertmacro MUI_PAGE_LICENSE "{license_file}"\n' if license_file else ""
    return TEMPLATE.format(
        app_name=app_name,
        version=version,
        bundle=bundle,
        out_file=out_file,
        main_exe=main_exe.replace("/", "\\"),
        license_page=license_page,
    )
