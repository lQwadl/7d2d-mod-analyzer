import json
import re


def extract_mod_id(mod_name: str):
    """
    Extract Nexus mod ID from a mod folder or display name.
    Example:
    HemSoft QoL v1.9.0-9332-1-9-0-1768810638 -> 9332
    """
    match = re.search(r"-(\d{3,6})-", mod_name)
    return match.group(1) if match else None


def generate_vortex_rules(ordered_mods):
    """
    Convert ordered mods into Vortex dependency rules.
    Uses modId + referenceModId (REQUIRED by Vortex).
    """
    rules = []

    for i in range(1, len(ordered_mods)):
        current_mod = ordered_mods[i]
        previous_mod = ordered_mods[i - 1]

        current_id = extract_mod_id(current_mod.name)
        previous_id = extract_mod_id(previous_mod.name)

        # Skip mods Vortex can't identify
        if not current_id or not previous_id:
            continue

        rules.append({"type": "after", "modId": current_id, "referenceModId": previous_id})

    return rules


def export_vortex_rules(path, ordered_mods):
    """
    Write Vortex-compatible rules.json file.
    """
    rules = generate_vortex_rules(ordered_mods)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)


def export_load_order(mods, path):
    """
    Human-readable TXT export (grouped by category).
    """
    with open(path, "w", encoding="utf-8") as f:
        current_category = None

        for mod in mods:
            if mod.category != current_category:
                current_category = mod.category
                f.write(f"\n# === {current_category.upper()} ===\n")

            f.write(mod.name + "\n")
