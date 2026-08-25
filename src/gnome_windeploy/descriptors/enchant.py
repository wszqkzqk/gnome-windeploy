"""enchant: spell-checker providers are dlopened, invisible to PE imports."""

from gnome_windeploy.descriptors.base import Descriptor

descriptor = Descriptor(
    name="enchant",
    trigger_dlls=frozenset({"libenchant-2-2.dll"}),
    mirror_dirs=("lib/enchant-2", "share/enchant-2"),
)
