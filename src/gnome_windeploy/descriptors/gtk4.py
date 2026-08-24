"""GTK 4: icon themes, optional themes/settings dirs."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="gtk4",
    trigger_dlls=frozenset({"libgtk-4-1.dll"}),
    mirror_dirs=(
        "share/icons/Adwaita",
        "share/icons/hicolor",
        "share/gtk-4.0",
        "share/themes/Adwaita",
    ),
    gettext_domains=("gtk40",),
)
