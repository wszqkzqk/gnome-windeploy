"""libpanel: locales only."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="libpanel",
    trigger_dlls=frozenset({"libpanel-1-1.dll"}),
    gettext_domains=("libpanel",),
)
