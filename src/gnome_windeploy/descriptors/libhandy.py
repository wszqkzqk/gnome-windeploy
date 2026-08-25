"""libhandy: locales only."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="libhandy",
    trigger_dlls=frozenset({"libhandy-1-0.dll"}),
    gettext_domains=("libhandy",),
)
