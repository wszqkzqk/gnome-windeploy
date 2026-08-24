"""Registry of all known deployable GNOME components."""

from gnome_windeploy.descriptors import (
    fontconfig,
    gdkpixbuf,
    glib,
    gstreamer,
    gtk3,
    gtk4,
    libadwaita,
)
from gnome_windeploy.descriptors.base import CacheFixup, Descriptor

_MODULES = (glib, gdkpixbuf, gstreamer, gtk4, gtk3, libadwaita, fontconfig)

REGISTRY: dict[str, Descriptor] = {module.descriptor.name: module.descriptor for module in _MODULES}

__all__ = ["REGISTRY", "CacheFixup", "Descriptor"]
