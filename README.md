# gnome-windeploy

`gnome-windeploy` packages GNOME/GTK desktop applications for Windows. Given
one or more compiled PE executables, it resolves their transitive DLL
dependencies and collects the GNOME runtime data covered by the built-in
descriptors into a relocatable application directory. In spirit, it is the
GNOME counterpart to Qt's `windeployqt`.

The project is currently alpha (`0.1.0`) and is primarily designed for
MSYS2/MinGW GNOME stacks.

## What it does

For each input executable, the tool:

- follows regular and delay-load PE imports to build the DLL closure;
- skips Windows system DLLs and Windows API-set DLLs, and reports unresolved
  non-system imports as warnings;
- discovers the source installation prefixes from the binaries and preserves
  their relative layout (`bin/`, `lib/`, `share/`, and `etc/`) in the bundle;
- stages runtime data for the components recognized by the descriptor registry;
- regenerates the caches that need to refer to staged files and rewrites their
  paths to be relative; and
- scans staged text files for absolute paths from the source prefixes and fails
  the deployment if any are left behind.

The built-in descriptors currently cover:

- GLib schemas and GIO modules;
- gdk-pixbuf loaders and their cache;
- GTK 3 and GTK 4 themes, settings, and icon themes;
- GStreamer 1.0 plugins and `gst-plugin-scanner.exe`;
- GtkSourceView 3 and 4 language definitions and style schemes;
- enchant spell-checker providers;
- gettext catalogs for libadwaita and the other registered components; and
- fontconfig configuration.

The dependency resolver copies DLLs, but runtime data for libraries without a
descriptor is not guessed automatically. Use `--include` or `--app-tree` for
application- or stack-specific files.

## Quick start

Install from PyPI:

```sh
python -m pip install gnome-windeploy
```

Or install a checkout in editable mode:

```sh
python -m pip install -e .
```

Deploy an application from an MSYS2 shell:

```sh
gnome-windeploy /ucrt64/bin/my-app.exe --destdir dist --zip
```

This creates `dist/` and, with `--zip`, `dist.zip`. The same command is
available as `python -m gnome_windeploy`.

## Command-line options

| Option | Description |
| --- | --- |
| `EXE ...` | One or more compiled `.exe` files to deploy. |
| `--destdir DIR` | Required destination directory. It may be created automatically, but must not contain files. |
| `--dll-dir DIR` | Additional DLL search directory; repeatable. |
| `--app-tree DIR` | Merge a `meson install --destdir` tree before dependency staging. Application files take precedence on conflicts. |
| `--include RELDIR` | Mirror an additional prefix-relative directory; repeatable. The first known prefix containing it is used. |
| `--icons full\|scalable\|symbolic` | Icon policy. The default is `full`. |
| `--locale-mode deps\|full\|none` | Locale policy. The default is `deps`. |
| `--locale-langs LANGS` | Comma-separated language filter for `deps`, for example `zh_CN,de`. |
| `--gettext-domain NAME` | Add an application gettext domain to locale collection; repeatable. |
| `--zip` | Also create `<destdir>.zip`. |
| `--nsis` | Build `<destdir>-setup.exe` with NSIS. Requires `makensis` on `PATH`. |
| `--app-name NAME` | Installer application name. Defaults to the first executable's filename. |
| `--app-version VER` | Installer version. Defaults to `0.0.0`. |
| `--license FILE` | License text for the NSIS license page. |
| `--installer-icon FILE` | Icon (.ico) for the installer and uninstaller. |
| `-v`, `--verbose` | Print the origin of every resolved DLL. |
| `--version` | Print the installed version and exit. |

## Default resource policies

### Icons

`full` copies the `Adwaita` and `hicolor` icon trees in full. `scalable` keeps
each theme's `index.theme` and its `scalable/` subtree. `symbolic` keeps the
same indexes but only files ending in `-symbolic.svg` inside `scalable/`.

### Locales

In `deps` mode, the tool copies `.mo` files for the gettext domains declared by
the activated descriptors, plus any domains supplied with
`--gettext-domain`. All available languages are included unless
`--locale-langs` is specified. `full` mirrors the entire `share/locale` tree;
`none` omits locales.

### GStreamer

The current policy copies all files under `lib/gstreamer-1.0` and stages
`gst-plugin-scanner.exe` when it is found in the source prefix's
`libexec/gstreamer-1.0/` or `bin/` directory.

## Prefixes, collisions, and portability

A binary in `<prefix>/bin` or `<prefix>/lib` anchors `<prefix>`. For a
non-standard layout, the binary's own directory is used as the anchor. When
dependencies come from multiple prefixes, their files are merged while
preserving prefix-relative paths.

Application files are staged first. If two dependency prefixes provide
different files at the same relative path, the first one is kept and the
collision is reported in the summary. Identical files are not reported as
collisions. This makes the output deterministic, but it is still worth
checking the summary when combining prefixes.

The generated directory is intended to be moved or copied without the original
installation prefix. The tool does not set application-specific environment
variables or infer arbitrary application assets; include those explicitly when
needed.

## Development

```sh
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
pytest
ruff check .
```

Most tests use synthetic prefix trees and injected PE import graphs, so they
run on Linux, macOS, and Windows without a real GNOME stack. The optional
end-to-end test runs only when a real MinGW GTK 4 and GStreamer stack is
available on Windows, or when `GNOME_WINDEPLOY_TEST_PREFIX` points to one.

## License

[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0)
