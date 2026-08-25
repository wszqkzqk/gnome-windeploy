"""GtkSourceView 3: language definitions and style schemes live as files."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="gtksourceview3",
    trigger_dlls=frozenset({"libgtksourceview-3.0-1.dll"}),
    mirror_dirs=("share/gtksourceview-3.0",),
    gettext_domains=("gtksourceview-3.0",),
)
