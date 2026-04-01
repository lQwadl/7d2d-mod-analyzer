def detect_redundancy(mods):
    overhauls = [m for m in mods if m.is_overhaul]

    for mod in mods:
        if mod.is_overhaul:
            continue

        name = mod.name.lower()

        # If mod looks like a content pack, skip redundancy
        content_keywords = ["weapon", "pack", "ammo", "gun", "melee", "remastered"]
        if any(k in name for k in content_keywords):
            continue

        for ov in overhauls:
            if mod.xml_files and mod.xml_files.issubset(ov.xml_files):
                mod.redundant_reason = f"Overhaul '{ov.name}' already replaces the same systems"
