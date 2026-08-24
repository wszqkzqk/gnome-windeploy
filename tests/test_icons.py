"""Tests for the full/scalable/symbolic icon policies on a fake theme tree."""

import pytest

from gnome_windeploy.engine import Stager, icon_file_filter
from util import touch


@pytest.fixture
def theme_prefix(tmp_path):
    prefix = tmp_path / "p"
    touch(prefix / "share/icons/Adwaita/index.theme")
    touch(prefix / "share/icons/Adwaita/scalable/apps/foo.svg")
    touch(prefix / "share/icons/Adwaita/scalable/apps/foo-symbolic.svg")
    touch(prefix / "share/icons/Adwaita/scalable/ui/bar-symbolic.svg")
    touch(prefix / "share/icons/Adwaita/16x16/apps/foo.png")
    touch(prefix / "share/icons/Adwaita/48x48/apps/foo-symbolic.png")
    touch(prefix / "share/icons/hicolor/index.theme")
    touch(prefix / "share/icons/hicolor/32x32/apps/baz.png")
    return prefix


def _mirror(policy, prefix, staging):
    stager = Stager(staging)
    stager.mirror_dir(prefix, "share/icons", "test", icon_file_filter(policy))
    return set(stager.index)


def test_full_policy_keeps_everything(theme_prefix, tmp_path):
    keys = _mirror("full", theme_prefix, tmp_path / "out")

    assert len(keys) == 8


def test_scalable_policy_keeps_index_and_scalable_subtrees(theme_prefix, tmp_path):
    keys = _mirror("scalable", theme_prefix, tmp_path / "out")

    assert keys == {
        "share/icons/Adwaita/index.theme",
        "share/icons/Adwaita/scalable/apps/foo.svg",
        "share/icons/Adwaita/scalable/apps/foo-symbolic.svg",
        "share/icons/Adwaita/scalable/ui/bar-symbolic.svg",
        "share/icons/hicolor/index.theme",
    }


def test_symbolic_policy_keeps_only_symbolic_svgs(theme_prefix, tmp_path):
    keys = _mirror("symbolic", theme_prefix, tmp_path / "out")

    assert keys == {
        "share/icons/Adwaita/index.theme",
        "share/icons/Adwaita/scalable/apps/foo-symbolic.svg",
        "share/icons/Adwaita/scalable/ui/bar-symbolic.svg",
        "share/icons/hicolor/index.theme",
    }


def test_unknown_policy_rejected():
    with pytest.raises(ValueError, match="unknown icon policy"):
        icon_file_filter("minimal")
