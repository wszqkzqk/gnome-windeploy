"""GStreamer: all plugins (v0 ships everything) plus the plugin scanner."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="gstreamer",
    trigger_dlls=frozenset({"libgstreamer-1.0-0.dll"}),
    mirror_dirs=("lib/gstreamer-1.0",),
    stage_files=(
        # gst-plugin-scanner lives in libexec on most layouts, in bin on some.
        (
            "libexec/gstreamer-1.0/gst-plugin-scanner.exe",
            "bin/gst-plugin-scanner.exe",
        ),
    ),
    gettext_domains=(
        "gstreamer-1.0",
        "gst-plugins-base-1.0",
        "gst-plugins-good-1.0",
        "gst-plugins-bad-1.0",
    ),
)
