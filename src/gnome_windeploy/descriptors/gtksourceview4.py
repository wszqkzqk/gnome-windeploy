"""GtkSourceView 4: language definitions and style schemes live as files."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="gtksourceview4",
    trigger_dlls=frozenset({"libgtksourceview-4-0.dll"}),
    mirror_dirs=("share/gtksourceview-4",),
    gettext_domains=("gtksourceview-4",),
)
