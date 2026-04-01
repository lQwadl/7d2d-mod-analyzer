"""Script-style tests for local UpdateEngine.

Run:
  python tests/update_engine_local_test.py
"""

import os
from pathlib import Path

import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.update_engine import detect_local_updates, apply_update_actions
from tests._test_tmp import temp_dir


def _write_mod(mod_dir: Path, *, modinfo_name: str, modinfo_version: str) -> None:
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "Config").mkdir(parents=True, exist_ok=True)
    (mod_dir / "ModInfo.xml").write_text(
        f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xml>
  <ModInfo>
    <Name value=\"{modinfo_name}\"/>
    <Description value=\"test\"/>
    <Author value=\"test\"/>
    <Version value=\"{modinfo_version}\"/>
  </ModInfo>
</xml>
""",
        encoding="utf-8",
    )


class _Mod:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path


def main():
    with temp_dir("update_engine_") as root:
        mods_root = root / "Mods"
        mods_root.mkdir(parents=True, exist_ok=True)

        # Case 1: two enabled versions; newest should be kept, older disabled
        v1 = mods_root / "001_MyMod-1.0.0"
        v2 = mods_root / "002_MyMod-2.0.0"
        _write_mod(v1, modinfo_name="MyMod", modinfo_version="1.0.0")
        _write_mod(v2, modinfo_name="MyMod", modinfo_version="2.0.0")

        mods = [_Mod(v1.name, str(v1)), _Mod(v2.name, str(v2))]
        cands = detect_local_updates(mods)
        assert len(cands) == 1
        assert cands[0].keep.folder_name == v2.name
        assert any(i.folder_name == v1.name for i in cands[0].to_disable)

        actions = apply_update_actions(mods_root=str(mods_root), candidates=cands)
        assert any(a.startswith("DISABLE:") for a in actions)
        assert (mods_root / ("__DISABLED__" + v1.name)).exists(), "older version should be disabled"

        # Case 2: newest exists but is disabled; should swap (enable newest, disable older)
        # Create a new mod base
        old = mods_root / "010_OtherMod-1.0.0"
        new_disabled = mods_root / "__DISABLED__020_OtherMod-2.0.0"
        _write_mod(old, modinfo_name="OtherMod", modinfo_version="1.0.0")
        _write_mod(new_disabled, modinfo_name="OtherMod", modinfo_version="2.0.0")

        mods2 = [_Mod(old.name, str(old)), _Mod(new_disabled.name, str(new_disabled))]
        cands2 = detect_local_updates(mods2)
        assert len(cands2) == 1
        assert cands2[0].keep.folder_name == new_disabled.name
        assert cands2[0].to_enable, "should plan enabling newest"
        assert any(i.folder_name == old.name for i in cands2[0].to_disable)

        actions2 = apply_update_actions(mods_root=str(mods_root), candidates=cands2)
        assert (mods_root / "020_OtherMod-2.0.0").exists(), "newest should be enabled"
        assert (mods_root / ("__DISABLED__" + old.name)).exists(), "older should be disabled"
        assert actions2, "expected actions"

    print("PASS")


if __name__ == "__main__":
    main()
