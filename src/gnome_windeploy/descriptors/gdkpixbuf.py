"""gdk-pixbuf: image loaders plus their regenerated, relativized cache."""

from gnome_windeploy.descriptors.base import CacheFixup, Descriptor

descriptor = Descriptor(
    name="gdkpixbuf",
    trigger_dlls=frozenset({"libgdk_pixbuf-2.0-0.dll"}),
    mirror_dirs=("lib/gdk-pixbuf-2.0",),
    cache_fixups=(
        # The cache lives in a versioned directory (e.g. 2.10.0) next to the
        # loaders/ subtree; the tool prints it to stdout with absolute paths.
        CacheFixup(
            tool="bin/gdk-pixbuf-query-loaders.exe",
            target_dir="lib/gdk-pixbuf-2.0",
            cache_file="lib/gdk-pixbuf-2.0/*/loaders.cache",
            stdout_to_cache=True,
        ),
    ),
    gettext_domains=("gdk-pixbuf",),
)
