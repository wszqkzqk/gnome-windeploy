"""fontconfig: configuration under etc/ and share/."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="fontconfig",
    trigger_dlls=frozenset({"libfontconfig-1.dll"}),
    mirror_dirs=(
        "etc/fonts",
        "share/fontconfig",
    ),
)
