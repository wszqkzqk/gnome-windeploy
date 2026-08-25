"""libspelling: locales only; the actual spell-checking backends come from enchant."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="libspelling",
    trigger_dlls=frozenset({"libspelling-1-2.dll"}),
    gettext_domains=("libspelling",),
)
