"""libsoup 3: locales only."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="libsoup3",
    trigger_dlls=frozenset({"libsoup-3.0-0.dll"}),
    gettext_domains=("libsoup-3.0",),
)
