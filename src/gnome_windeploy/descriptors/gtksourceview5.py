"""GtkSourceView 5: language definitions are compiled into the DLL; locales only."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="gtksourceview5",
    trigger_dlls=frozenset({"libgtksourceview-5-0.dll"}),
    gettext_domains=("gtksourceview-5",),
)
