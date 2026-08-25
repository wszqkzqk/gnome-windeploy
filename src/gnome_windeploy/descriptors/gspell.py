"""gspell: locales only; the actual spell-checking backends come from enchant."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="gspell",
    trigger_dlls=frozenset({"libgspell-1-3.dll"}),
    gettext_domains=("gspell-1",),
)
