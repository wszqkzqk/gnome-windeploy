"""GLib / GIO: always active (every GNOME app depends on it)."""

from gnome_windeploy.descriptors.base import CacheFixup, Descriptor

descriptor = Descriptor(
    name="glib",
    always=True,
    trigger_dlls=frozenset({"libglib-2.0-0.dll"}),
    mirror_dirs=(
        "share/glib-2.0/schemas",
        "lib/gio/modules",
    ),
    cache_fixups=(
        # gschemas.compiled is a binary blob without paths: no relativization.
        CacheFixup(
            tool="bin/glib-compile-schemas.exe",
            args=("{target}",),
            target_dir="share/glib-2.0/schemas",
            cache_file="share/glib-2.0/schemas/gschemas.compiled",
            relativize=False,
        ),
        # gio-querymodules writes giomodule.cache in place, with absolute paths.
        CacheFixup(
            tool="bin/gio-querymodules.exe",
            args=("{target}",),
            target_dir="lib/gio/modules",
            cache_file="lib/gio/modules/giomodule.cache",
        ),
    ),
    gettext_domains=("glib20",),
)
