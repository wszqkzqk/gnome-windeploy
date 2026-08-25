"""glib-networking: gio modules are already mirrored by the glib descriptor; locales only."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="glib-networking",
    trigger_dlls=frozenset(
        {
            "libgiognutls.dll",
            "libgioopenssl.dll",
            "libgiognomeproxy.dll",
            "libgiolibproxy.dll",
        }
    ),
    gettext_domains=("glib-networking",),
)
