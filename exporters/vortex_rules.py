import json


def generate_vortex_rules(ordered_mods):
    rules = []

    for i in range(1, len(ordered_mods)):
        current_mod = ordered_mods[i]
        previous_mod = ordered_mods[i - 1]

        rules.append({"type": "after", "mod": current_mod.name, "reference": previous_mod.name})

    return rules


def export_vortex_rules(path, ordered_mods):
    rules = generate_vortex_rules(ordered_mods)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
