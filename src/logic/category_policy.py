from __future__ import annotations

from typing import Iterable, List, Optional

# Authoritative, fixed category order used everywhere.
# This is aligned to the desired tier ordering for 7DTD mods:
# Frameworks/Core → Overhauls → Systems/Mechanics → Content → POI/World → Visual → UI/QoL last.
# (We include Food because XML evidence can support it.)
CATEGORY_ORDER: List[str] = [
    "Core / Framework",
    "Overhauls",
    # Systems / mechanics
    "XML Edits",
    "Gameplay",
    "Utilities",
    # Content
    "Crafting",
    "Weapons",
    "Items & Loot",
    "Food",
    "Zombies / Creatures",
    "Vehicles",
    "Quests",
    # POI / world
    "Prefabs / POIs",
    "Maps",
    # Visual
    "Visuals & Graphics",
    "Audio",
    # UI / QoL (late)
    "UI",
    "Cheats",
    "Miscellaneous",
]

CATEGORY_ALIASES = {
    # Common variants
    "core/framework": "Core / Framework",
    "core": "Core / Framework",
    "framework": "Core / Framework",
    "overhaul": "Overhauls",
    "overhauls": "Overhauls",
    "xml": "XML Edits",
    "xml edits": "XML Edits",
    "patch": "XML Edits",
    "patches": "XML Edits",
    "ui": "UI",
    "user interface": "UI",
    "visuals": "Visuals & Graphics",
    "graphics": "Visuals & Graphics",
    "visuals and graphics": "Visuals & Graphics",
    "items": "Items & Loot",
    "items and loot": "Items & Loot",
    "loot": "Items & Loot",
    "prefabs": "Prefabs / POIs",
    "poi": "Prefabs / POIs",
    "pois": "Prefabs / POIs",
    "maps": "Maps",
    "map": "Maps",
    "zombies": "Zombies / Creatures",
    "creatures": "Zombies / Creatures",
    "crafting": "Crafting",
    "recipes": "Crafting",
    "quests": "Quests",
    # Tier-ish labels users might assign manually
    "systems": "Gameplay",
    "system": "Gameplay",
    "mechanics": "Gameplay",
    "mechanic": "Gameplay",
    "qol": "UI",
    "quality of life": "UI",
    "world": "Maps",
    "poi/world": "Prefabs / POIs",
}


def normalize_category(raw: Optional[str]) -> str:
    if not raw:
        return "Miscellaneous"
    key = str(raw).strip()
    if not key:
        return "Miscellaneous"
    mapped = CATEGORY_ALIASES.get(key.lower())
    return mapped or key


def category_index(category: Optional[str]) -> int:
    cat = normalize_category(category)
    try:
        return CATEGORY_ORDER.index(cat)
    except ValueError:
        return len(CATEGORY_ORDER)


def sort_categories(categories: Iterable[str]) -> List[str]:
    unique = []
    seen = set()
    for c in categories or []:
        cc = normalize_category(c)
        if cc.lower() in seen:
            continue
        seen.add(cc.lower())
        unique.append(cc)
    unique.sort(key=lambda c: (category_index(c), c.lower()))
    return unique


def choose_primary_category(categories: Iterable[str]) -> str:
    ordered = sort_categories(categories)
    return ordered[0] if ordered else "Miscellaneous"


# Category impact weights for severity calculation (additive score).
# Higher == more likely save-breaking / high-impact systems.
CATEGORY_IMPACT_WEIGHT = {
    "Core / Framework": 15,
    "Overhauls": 25,
    "XML Edits": 10,
    "Gameplay": 10,
    "Crafting": 6,
    "Weapons": 8,
    "Items & Loot": 6,
    "Food": 4,
    "Zombies / Creatures": 8,
    "Vehicles": 8,
    "Prefabs / POIs": 15,
    "Maps": 18,
    "Quests": 6,
    "Visuals & Graphics": -10,
    "Audio": -10,
    "UI": -6,
    "Utilities": 0,
    "Cheats": 0,
    "Miscellaneous": 0,
}


# Load-order rank is intentionally separate from UI ordering.
# It follows the desired tier ordering:
# Frameworks/Core → Overhauls → Systems/Mechanics → Content → POI/World → Visual → UI/QoL last.
LOAD_ORDER_RANK = {
    # Frameworks / core (early)
    "Core / Framework": 10,
    "Overhauls": 20,
    # Systems / mechanics
    "XML Edits": 30,
    "Gameplay": 35,
    "Utilities": 40,
    # Content
    "Crafting": 45,
    "Weapons": 55,
    "Items & Loot": 55,
    "Food": 55,
    "Zombies / Creatures": 60,
    "Vehicles": 60,
    "Quests": 60,
    # POI / world
    "Prefabs / POIs": 70,
    "Maps": 75,
    # Visual
    "Visuals & Graphics": 80,
    "Audio": 82,
    # UI / QoL (late)
    "UI": 90,
    "Cheats": 95,
    "Miscellaneous": 99,
}


def load_order_rank(category: Optional[str]) -> int:
    cat = normalize_category(category)
    try:
        return int(LOAD_ORDER_RANK.get(cat, 99))
    except Exception:
        return 99
