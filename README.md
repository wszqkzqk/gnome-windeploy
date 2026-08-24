# gnome-windeploy

A deployment tool for GNOME-platform desktop apps on Windows — the GNOME
equivalent of Qt's `windeployqt`.

You give it one or more compiled `.exe` files (built in MSYS2/MinGW or any
legal GNOME-stack layout). It produces a redistributable, relocatable
directory containing:

- your executables,
- the full transitive DLL closure (regular *and* delay-load imports),
- all required GNOME runtime data: GLib schemas (compiled), GIO modules,
  gdk-pixbuf loaders (with cache), GStreamer plugins, icon themes,
  shared-mime-info, fontconfig configuration, and the locales of the included
  libraries,

with all caches rewritten to relative paths, so the bundle works from any
location — no installer, no fixed prefix, no environment variables.

Think of the runtime scope as "the contents of `org.gnome.Platform`, but
collected into your app directory on Windows".

## Design pillars

- **GLib relocatability contract.** Every GLib-family DLL resolves its
  installation prefix at runtime from its own module location and finds
  `share/...` and `lib/...` relative to it. Mirroring the source layout into
  the bundle is therefore the *generic* mechanism — the tool never hardcodes
  prefixes.
- **DLL-anchored prefixes.** A DLL in `<prefix>/bin` or `<prefix>/lib` anchors
  `<prefix>`; a DLL anywhere else anchors its own directory (nonstandard but
  legal layouts still work). Multiple prefixes (e.g. MSYS2 plus a custom
  stack) are merged into one tree; same-relative-path collisions are reported
  (first wins).
- **Declarative descriptors.** Everything the engine knows about GLib,
  gdk-pixbuf, GStreamer, GTK 3/4, libadwaita, shared-mime-info and fontconfig
  lives in small pure-data descriptor modules (`descriptors/`): trigger DLLs,
  directories to mirror, caches to regenerate, gettext domains, implied
  components. The engine contains zero per-component logic.
- **Build-time leak detection.** After all caches are regenerated, staged text
  files are scanned for any remaining absolute source-prefix path. A leak is a
  build error, not a runtime surprise on a user's machine.

## Quickstart

```sh
pip install gnome-windeploy   # or: pip install -e . from a checkout

gnome-windeploy /ucrt64/bin/app.exe --destdir dist --zip
```

Result: `dist/` mirrors the prefix layout (`bin/`, `lib/`, `share/`, `etc/`)
and `dist.zip` is ready to ship. Under an MSYS2 UCRT64 shell, `python -m
gnome_windeploy` does the same thing.

## Options

| Option | Meaning |
| --- | --- |
| `EXE ...` (positional, 1+) | Compiled executables to deploy. |
| `--destdir DIR` | Output directory (required; must not exist or be empty). |
| `--dll-dir DIR` | Extra DLL search directory, for exes not co-located with their DLLs (repeatable). |
| `--app-tree DIR` | A `meson install --destdir` tree merged in *before* dependency staging; app files win on collision. |
| `--include RELDIR` | Force-mirror an arbitrary prefix-relative directory (repeatable) — the escape hatch for anything the registry doesn't know. |
| `--icons full\|scalable\|symbolic` | Icon theme policy (default: `full`). |
| `--locale-mode deps\|full\|none` | Locale mirroring mode (default: `deps`). |
| `--locale-langs zh_CN,de` | Language filter for `deps` locale mode. |
| `--gettext-domain NAME` | Add your app's own gettext domain for locale mirroring (repeatable). |
| `--zip` | Also create `<destdir>.zip`. |
| `-v`, `--verbose` | Verbose output (full DLL origin list). |

## Resource policy defaults (and opt-in trims)

- **Icons: full copy.** `share/icons/Adwaita` and `share/icons/hicolor` are
  mirrored completely. `--icons=scalable` keeps `index.theme` plus the
  `scalable/` subtrees; `--icons=symbolic` additionally keeps only
  `*-symbolic.svg` files. GTK tolerates missing subdirectories referenced by
  `index.theme`, so no index rewrite is needed.
- **Locales: dependencies only.** In `deps` mode the bundle ships
  `share/locale/<lang>/LC_MESSAGES/<domain>.mo` for the gettext domains of the
  activated components (e.g. `glib20`, `gtk40`) plus any `--gettext-domain`
  you add — every language present is included unless `--locale-langs`
  restricts it. `--locale-mode=full` mirrors all of `share/locale`;
  `--locale-mode=none` ships nothing.
- **MIME data: full.** `share/mime` is mirrored whenever GTK is in the
  closure.
- **GStreamer: all plugins.** v0 mirrors `lib/gstreamer-1.0` wholesale and
  stages `gst-plugin-scanner.exe` (detected in `libexec/gstreamer-1.0/` or
  `bin/`).

## Roadmap

- GStreamer plugin subsets (only ship the plugins you actually use)
- Icon allowlists (ship only named icons)
- NSIS / Inno Setup / MSIX packaging exits
- More descriptors: libsoup / glib-networking, gtksourceview, VTE, gspell,
  GJS / typelib
- gvsbuild / MSVC-built stack support

## Development

```sh
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -e '.[dev]'
pytest
ruff check .
```

The test suite runs anywhere (Linux, macOS, Windows) — PE parsing is isolated
behind an injectable `imports_provider`, so tests use fake dependency graphs
and synthetic prefix trees instead of real binaries. CI additionally runs an
end-to-end deployment of a real GTK 4 + GStreamer executable inside MSYS2
UCRT64.

## License

[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0)
