"""libadwaita: no extra runtime data of its own; locales only."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="libadwaita",
    trigger_dlls=frozenset({"libadwaita-1-0.dll"}),
    gettext_domains=("libadwaita-1",),
)
