"""GTK 3: icon themes, optional themes/settings dirs, shared-mime-info."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="gtk3",
    trigger_dlls=frozenset({"libgtk-3-0.dll"}),
    mirror_dirs=(
        "share/icons/Adwaita",
        "share/icons/hicolor",
        "share/gtk-3.0",
        "share/themes/Adwaita",
    ),
    implies=("sharedmime",),
    gettext_domains=("gtk30",),
)
