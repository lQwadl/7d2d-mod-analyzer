from pathlib import Path
from ..models.mod import Mod

from ..path_safety import is_appdata_path


def scan_mods(mods_path: str):
    mods_dir = Path(mods_path)

    # Hard guardrail: never scan AppData.
    if is_appdata_path(mods_dir):
        return []

    if not mods_dir.exists():
        return []

    mods = []

    for mod_folder in mods_dir.iterdir():
        if not mod_folder.is_dir():
            continue

        real_path = str(mod_folder.resolve())

        # Do NOT follow symlinks/junctions into AppData.
        # This prevents accidental scans of Vortex/AppData staging or temp folders.
        if mod_folder.is_symlink() and is_appdata_path(real_path):
            continue

        modinfo = mod_folder / "ModInfo.xml"

        mod_obj = Mod(mod_folder.name, real_path)

        if mod_folder.is_symlink():
            mod_obj.is_symlink = True
            mod_obj.symlink_target = real_path
            rp_lower = real_path.lower()
            if "vortex" in rp_lower or "appdata" in rp_lower or "staging" in rp_lower:
                mod_obj.source = "Vortex"

        mods.append(mod_obj)

    return mods
