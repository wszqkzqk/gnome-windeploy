"""shared-mime-info: data-only component, activated via ``implies`` (by GTK)."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="sharedmime",
    mirror_dirs=("share/mime",),
    gettext_domains=("shared-mime-info",),
)
