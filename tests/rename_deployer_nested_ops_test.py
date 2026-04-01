import os
from pathlib import Path

from deployment.rename_deployer import two_phase_rename
from tests._test_tmp import temp_dir


def test_two_phase_rename_handles_nested_paths():
    # Simulate a common "wrapper folder" layout:
    # ModsRoot/Wrapper/RealMod  (both might be included in a scan)
    with temp_dir("rename_ops_") as root:
        mods_root = root / "Mods"
        mods_root.mkdir()

        wrapper = mods_root / "Wrapper"
        wrapper.mkdir()

        real_mod = wrapper / "RealMod"
        real_mod.mkdir()
        (real_mod / "ModInfo.xml").write_text("<xml></xml>", encoding="utf-8")

        # Also include a file in wrapper so it's a non-empty dir.
        (wrapper / "readme.txt").write_text("wrapper", encoding="utf-8")

        # Rename both wrapper and the nested mod.
        # The nested mod must be handled before the wrapper to avoid missing-path failures.
        ops = [
            (str(wrapper), str(mods_root / "010_Wrapper")),
            (str(real_mod), str(mods_root / "000_RealMod")),
        ]

        two_phase_rename(str(mods_root), ops)

        assert (mods_root / "010_Wrapper").exists()
        assert (mods_root / "000_RealMod").exists()
        assert not wrapper.exists()
        assert not real_mod.exists()

        # Ensure we didn't accidentally create nested destinations.
        assert os.path.commonpath([str(mods_root), str(mods_root / "000_RealMod")]) == str(mods_root)
