"""Registry of all known deployable GNOME components."""

from gnome_windeploy.descriptors import (
    enchant,
    fontconfig,
    gdkpixbuf,
    glib,
    glib_networking,
    gspell,
    gstreamer,
    gtk3,
    gtk4,
    gtksourceview3,
    gtksourceview4,
    gtksourceview5,
    jsonglib,
    libadwaita,
    libhandy,
    libpanel,
    libsoup3,
    libspelling,
)
from gnome_windeploy.descriptors.base import CacheFixup, Descriptor

_MODULES = (
    glib,
    gdkpixbuf,
    gstreamer,
    gtk4,
    gtk3,
    libadwaita,
    fontconfig,
    gtksourceview5,
    gtksourceview4,
    gtksourceview3,
    enchant,
    gspell,
    libspelling,
    glib_networking,
    jsonglib,
    libsoup3,
    libhandy,
    libpanel,
)

REGISTRY: dict[str, Descriptor] = {module.descriptor.name: module.descriptor for module in _MODULES}

__all__ = ["REGISTRY", "CacheFixup", "Descriptor"]
