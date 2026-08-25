"""JSON-GLib: locales only."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="jsonglib",
    trigger_dlls=frozenset({"libjson-glib-1.0-0.dll"}),
    gettext_domains=("json-glib-1.0",),
)
