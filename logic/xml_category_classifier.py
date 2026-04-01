from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from logic.category_policy import (
    choose_primary_category,
    normalize_category,
    sort_categories,
)

# Filenames -> high-level domains. (Basename match, case-insensitive)
FILE_DOMAIN = {
    "items.xml": "items",
    "entityclasses.xml": "entities",
    "recipes.xml": "recipes",
    "buffs.xml": "gameplay",
    "perks.xml": "gameplay",
    "quests.xml": "quests",
    "vehicles.xml": "vehicles",
    "ui.xml": "ui",
    "windows.xml": "ui",
    "blocks.xml": "world",
    "worldglobal.xml": "world",
    "prefabs.xml": "world",
    "materials.xml": "visuals",
}

_WEAPON_NAME_RE = re.compile(
    r"(gun|pistol|rifle|shotgun|bow|ammo|ar(\d+)?|ak(\d+)?|m(\d+)|sniper|smg|melee|sword|knife|club|bat|spear)",
    re.I,
)


def _iter_xml_files(mod_path: Path) -> List[Path]:
    out: List[Path] = []
    for p in mod_path.rglob("*.xml"):
        try:
            if not p.is_file():
                continue
            if p.name.lower() == "modinfo.xml":
                continue
            out.append(p)
        except Exception:
            continue
    out.sort(key=lambda p: str(p).lower())
    return out


def _file_kind(path: Path) -> str:
    return path.name.lower()


def _has_xpath_ops(root: ET.Element) -> bool:
    try:
        for e in root.iter():
            if e.attrib.get("xpath"):
                return True
        return False
    except Exception:
        return False


def _looks_like_direct_definitions(root: ET.Element) -> bool:
    """Best-effort: returns True if XML appears to define real config nodes (not just patch ops)."""
    try:
        for e in root.iter():
            tag = (e.tag or "").lower()
            if tag in {
                "append",
                "insert",
                "add",
                "set",
                "update",
                "replace",
                "remove",
                "delete",
            } and e.attrib.get("xpath"):
                continue
            # Common definition nodes in 7DTD configs
            if tag in {
                "item",
                "block",
                "entity_class",
                "entityclass",
                "buff",
                "perk",
                "recipe",
                "quest",
                "vehicle",
                "material",
            }:
                return True
        return False
    except Exception:
        return False


def _classify_items_tree(root: ET.Element) -> Tuple[bool, bool]:
    """Return (has_weapons, has_food) based on evidence inside items.xml."""
    has_weapons = False
    has_food = False

    try:
        for item in root.iter():
            if (item.tag or "").lower() != "item":
                continue
            nm = str(item.attrib.get("name") or "")
            if nm and _WEAPON_NAME_RE.search(nm):
                has_weapons = True

            for prop in list(item):
                if (prop.tag or "").lower() != "property":
                    continue
                pname = str(prop.attrib.get("name") or "")
                pval = str(prop.attrib.get("value") or "")
                if pname.lower() == "tags" and ("food" in pval.lower() or "drink" in pval.lower()):
                    has_food = True
                if pname.lower().startswith("action") or pname.lower() in {
                    "holdingtype",
                    "weapontype",
                }:
                    has_weapons = True
                if pname.lower() in {
                    "foodhealth",
                    "foodwater",
                    "foodstamina",
                    "foodpoison",
                }:
                    has_food = True

            if has_weapons and has_food:
                break
    except Exception:
        return has_weapons, has_food

    return has_weapons, has_food


def _classify_entityclasses_tree(root: ET.Element) -> bool:
    """Return True if evidence suggests zombies; False means creatures."""
    try:
        for e in root.iter():
            tag = (e.tag or "").lower()
            if tag not in {"entity_class", "entityclass", "entity"}:
                continue
            nm = str(e.attrib.get("name") or "")
            if "zombie" in nm.lower() or "undead" in nm.lower():
                return True
        # fallback: any mention of zombie in text/attrs
        for e in root.iter():
            if any("zombie" in str(v).lower() for v in e.attrib.values()):
                return True
        return False
    except Exception:
        return False


def detect_categories_for_mod(mod_path: Path) -> Tuple[List[str], str, Dict[str, Any]]:
    """Deterministic, evidence-based category detection.

    Returns: (categories_sorted, primary_category, evidence)
    """

    categories: Set[str] = set()
    evidence: Dict[str, Any] = {
        "files": [],
        "domains": [],
        "patch_only": False,
        "invalid_xml": [],
        "signals": {},
    }

    xml_files = _iter_xml_files(mod_path)
    evidence["files"] = [str(p.relative_to(mod_path)).replace("\\", "/") for p in xml_files]

    any_direct_def = False
    any_xpath_ops = False

    domains_touched: Set[str] = set()

    for p in xml_files:
        base = _file_kind(p)
        dom = FILE_DOMAIN.get(base)
        if dom:
            domains_touched.add(dom)

        try:
            tree = ET.parse(str(p))
            root = tree.getroot()
        except ET.ParseError:
            evidence["invalid_xml"].append(str(p.relative_to(mod_path)).replace("\\", "/"))
            continue
        except Exception:
            continue

        if _has_xpath_ops(root):
            any_xpath_ops = True
        if _looks_like_direct_definitions(root):
            any_direct_def = True

        # Domain-specific deep evidence
        if base == "items.xml":
            has_weapons, has_food = _classify_items_tree(root)
            evidence["signals"].setdefault("items.xml", {})
            evidence["signals"]["items.xml"]["weapons"] = bool(has_weapons)
            evidence["signals"]["items.xml"]["food"] = bool(has_food)

        if base == "entityclasses.xml":
            is_zombies = _classify_entityclasses_tree(root)
            evidence["signals"].setdefault("entityclasses.xml", {})
            evidence["signals"]["entityclasses.xml"]["zombies"] = bool(is_zombies)

    evidence["domains"] = sorted(domains_touched)

    # --- Category mapping by concrete evidence ---
    # Patch-only mods: all XML is xpath patch ops and none look like direct defs.
    patch_only = bool(xml_files) and any_xpath_ops and not any_direct_def
    evidence["patch_only"] = patch_only
    if patch_only:
        categories.add("XML Edits")

    # File-based categories
    files_present = {p.name.lower() for p in xml_files}

    if "recipes.xml" in files_present:
        categories.add("Crafting")

    if "buffs.xml" in files_present or "perks.xml" in files_present:
        categories.add("Gameplay")

    if "quests.xml" in files_present:
        categories.add("Quests")

    if "vehicles.xml" in files_present:
        categories.add("Vehicles")

    if "ui.xml" in files_present or "windows.xml" in files_present:
        categories.add("UI")

    if "prefabs.xml" in files_present or "worldglobal.xml" in files_present or "blocks.xml" in files_present:
        # Prefabs vs Maps split
        if "worldglobal.xml" in files_present:
            categories.add("Maps")
        if "prefabs.xml" in files_present or "blocks.xml" in files_present:
            categories.add("Prefabs / POIs")

    # Visual evidence
    if "materials.xml" in files_present:
        categories.add("Visuals & Graphics")

    # shader-ish evidence (non-xml)
    try:
        for q in mod_path.rglob("*"):
            if not q.is_file():
                continue
            nm = q.name.lower()
            rel = str(q.relative_to(mod_path)).replace("\\", "/").lower()
            if nm.endswith(".shader") or "/shaders/" in ("/" + rel + "/"):
                categories.add("Visuals & Graphics")
                break
    except Exception:
        pass

    # Items.xml sub-classification
    if "items.xml" in files_present:
        categories.add("Items & Loot")
        sig = (evidence.get("signals") or {}).get("items.xml") or {}
        if sig.get("weapons"):
            categories.add("Weapons")
        if sig.get("food"):
            categories.add("Food")

    # EntityClasses => Zombies/Creatures
    if "entityclasses.xml" in files_present:
        categories.add("Zombies / Creatures")

    # Overhaul detection (XML evidence only): touches many domains.
    if len(domains_touched) >= 4:
        categories.add("Overhauls")

    if not categories:
        categories.add("Miscellaneous")

    categories_sorted = sort_categories(categories)
    primary = choose_primary_category(categories_sorted)
    primary = normalize_category(primary)

    return categories_sorted, primary, evidence
