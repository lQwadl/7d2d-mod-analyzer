from __future__ import annotations

import os
import re
import heapq
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from logic.conflict_memory import normalize_mod_id
except ModuleNotFoundError:
    # When executed directly (e.g. `python logic/load_order_engine.py`), Python's
    # import root becomes the `logic/` folder, so `import logic.*` fails.
    # Fix by temporarily adding the project root to sys.path.
    if __name__ == "__main__" and (not __package__):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from logic.conflict_memory import normalize_mod_id
    else:
        raise


TIER_ORDER: Tuple[str, ...] = (
    # Earlier tiers load first; Patch Mods must load last.
    "Core Frameworks",
    "API / Backend Systems",
    # Gameplay tier (mechanics + general content; keep before FPV frameworks).
    "Gameplay Overhauls",
    "Content Additions",
    # Animation/FPV frameworks must load before weapon packs.
    "Weapon Frameworks & Animation",
    "Weapon Packs",
    # Visuals before worldgen; QoL after worldgen.
    "Visual / Audio Mods",
    "Worldgen / POI Mods",
    "Utility / QoL Mods",
    "Patch Mods",
)

SEMANTIC_ORDER: Tuple[str, ...] = (
    "Global System Changes",
    "Additive Content",
    "Presentation Layer",
    "Destructive Changes",
)


FRAMEWORK_KIND_ORDER: Tuple[str, ...] = (
    "Harmony",
    "Core Libraries",
    "Community Frameworks",
)


@dataclass(frozen=True)
class OrderingEdge:
    before: str
    after: str
    layer: str
    reason: str


@dataclass
class LoadOrderReport:
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    applied_edges: List[OrderingEdge] = field(default_factory=list)
    dropped_edges: List[OrderingEdge] = field(default_factory=list)
    debug: Dict[str, Any] = field(default_factory=dict)

    def confidence_level(self) -> str:
        if self.errors:
            return "low"
        if self.warnings:
            return "medium"
        return "high"


_ORDER_PREFIX_RE = re.compile(r"^(\d+)_")


def _parse_order_prefix(folder_name: str) -> Optional[int]:
    """Return numeric load-order prefix (0-999) if present, else None."""
    try:
        if not folder_name:
            return None
        name = str(folder_name)
        if name.startswith("__DISABLED__"):
            name = name[len("__DISABLED__") :]
        m = _ORDER_PREFIX_RE.match(name)
        if not m:
            return None
        return int(m.group(1))
    except Exception:
        return None


def _mod_files_for_diagnostics(mod: Any, *, file_cache: Dict[str, List[Path]]) -> List[Path]:
    """Return bounded file list for a mod, cached by mod.path."""

    path_str = str(getattr(mod, "path", "") or "").strip()
    if not path_str:
        return []
    cached = file_cache.get(path_str)
    if cached is not None:
        return cached
    try:
        p = Path(path_str)
        if not p.is_dir():
            file_cache[path_str] = []
        else:
            file_cache[path_str] = _safe_list_files(p)
    except Exception:
        file_cache[path_str] = []
    return file_cache[path_str]


def _add_poi_spawn_diagnostics(
    ordered_mods: Sequence[Any],
    *,
    report: LoadOrderReport,
    file_cache: Dict[str, List[Path]],
) -> None:
    """Emit targeted, actionable diagnostics for RWG/POI spawning issues.

    This is heuristic and intentionally conservative; it should help users
    identify common causes of “POIs not spawning” without deep XML diffing.
    """

    if not ordered_mods:
        return

    entries: List[Dict[str, Any]] = []

    for m in ordered_mods:
        try:
            files = _mod_files_for_diagnostics(m, file_cache=file_cache)
        except Exception:
            files = []
        basenames = _basename_set(files)
        name_raw = str(getattr(m, "name", "") or "")
        name_l = name_raw.lower()

        has_rwgmixer = "rwgmixer.xml" in basenames
        has_prefabs_xml = "prefabs.xml" in basenames
        has_prefabs_dir = _has_any_rel_fragment(files, "/prefabs/")
        has_biomes = "biomes.xml" in basenames
        has_worldglobal = "worldglobal.xml" in basenames

        is_spawn_all = ("spawn_all_poi" in name_l) or ("spawn all poi" in name_l) or ("spawnallpoi" in name_l)
        is_better_gen = ("better generation" in name_l) or ("bettergen" in name_l) or ("better_generation" in name_l)

        is_worldgen_editor = bool(has_rwgmixer or has_biomes or has_worldglobal)
        is_poi_packish = bool(has_prefabs_dir or has_prefabs_xml or ("poi" in name_l) or ("prefab" in name_l))

        entries.append(
            {
                "mod": m,
                "name": normalize_mod_id(name_raw) or name_raw,
                "name_l": name_l,
                "files": files,
                "basenames": basenames,
                "has_rwgmixer": has_rwgmixer,
                "has_prefabs_dir": has_prefabs_dir,
                "has_prefabs_xml": has_prefabs_xml,
                "is_spawn_all": is_spawn_all,
                "is_better_gen": is_better_gen,
                "is_worldgen_editor": is_worldgen_editor,
                "is_poi_packish": is_poi_packish,
            }
        )

    any_poi_related = any(e["is_poi_packish"] or e["is_worldgen_editor"] for e in entries)
    if not any_poi_related:
        return

    # Current order (as installed) if numeric prefixes/load_order appear meaningful.
    def _current_order_value(mod: Any) -> int:
        lo = getattr(mod, "load_order", None)
        if isinstance(lo, int) and lo:
            return lo
        pref = _parse_order_prefix(str(getattr(mod, "name", "") or ""))
        if isinstance(pref, int):
            return pref
        return 10_000

    current_sorted = list(ordered_mods)
    current_sorted.sort(key=lambda m: (_current_order_value(m), str(getattr(m, "name", "") or "").lower()))

    meaningful_current = any(_current_order_value(m) != 10_000 for m in current_sorted)
    idx_current: Dict[int, int] = {id(m): i for i, m in enumerate(current_sorted)}

    rwgmixer_mods = [e for e in entries if e["has_rwgmixer"]]
    spawn_all_mods = [e for e in entries if e["is_spawn_all"]]
    better_gen_mods = [e for e in entries if e["is_better_gen"]]
    prefab_only_packs = [
        e for e in entries if e["has_prefabs_dir"] and (not e["has_rwgmixer"]) and (not e["is_spawn_all"])
    ]
    poi_packish = [
        e
        for e in entries
        if e["is_poi_packish"]
        and (not e["is_worldgen_editor"])
        and (not e["is_spawn_all"])
        and (not e["is_better_gen"])
    ]

    # Always provide the checklist when POI/worldgen content is present.
    report.warnings.append(
        "POIs not spawning — common causes:\n"
        "  1) New world required: POI packs inject during RWG world generation. If you added/reordered worldgen or POI mods, delete the generated world folder and regenerate.\n"
        "  2) rwgmixer overwrite: If a mod that ships rwgmixer.xml loads after your injector/POI packs, it can remove them from spawn lists.\n"
        "  3) Missing injection: Some POI packs only add prefabs (no rwgmixer.xml). They won’t spawn unless another mod injects them (e.g., spawn_all_POIs/CompoPack) or you place them manually.\n"
        "Recommended order (for RWG/POIs): Core frameworks → Worldgen (Better Generation/Biomes) → spawn_all_POIs → POI packs → everything else; then regenerate the world."
    )

    if len(rwgmixer_mods) >= 2:
        names = ", ".join(e["name"] for e in rwgmixer_mods[:10])
        extra = "" if len(rwgmixer_mods) <= 10 else f" (+{len(rwgmixer_mods) - 10} more)"
        report.warnings.append(
            "Worldgen/POI order risk: multiple mods include rwgmixer.xml. Only the last effective rwgmixer edits win, so load order is critical. "
            f"Found: {names}{extra}."
        )

    if meaningful_current:
        # Better Generation after POI packs: likely overwriting.
        if better_gen_mods and poi_packish:
            bg = better_gen_mods[0]
            bg_idx = idx_current.get(id(bg["mod"]))
            if bg_idx is not None:
                earlier_packs = [p for p in poi_packish if idx_current.get(id(p["mod"]), 10**9) < bg_idx]
                if earlier_packs and bg.get("has_rwgmixer"):
                    sample = ", ".join(p["name"] for p in earlier_packs[:5])
                    report.warnings.append(
                        "POI spawn issue likely: a worldgen mod (e.g., Better Generation) appears to load AFTER one or more POI packs in your current order, which can overwrite rwgmixer.xml and prevent POIs from spawning. "
                        f"Worldgen mod: {bg['name']}; earlier POI packs include: {sample}."
                    )

        # spawn_all_POIs overwritten by later rwgmixer mods
        if spawn_all_mods and rwgmixer_mods:
            sp = spawn_all_mods[0]
            sp_idx = idx_current.get(id(sp["mod"]))
            if sp_idx is not None:
                later_rwgmixer = [
                    e for e in rwgmixer_mods if (idx_current.get(id(e["mod"]), -1) > sp_idx) and (not e["is_spawn_all"])
                ]
                if later_rwgmixer:
                    sample = ", ".join(e["name"] for e in later_rwgmixer[:5])
                    report.warnings.append(
                        "POI spawn issue likely: spawn_all_POIs appears to load BEFORE another mod that also edits rwgmixer.xml, so its injection may be overwritten. "
                        f"spawn_all_POIs: {sp['name']}; later rwgmixer mods include: {sample}."
                    )

    if prefab_only_packs:
        sample = ", ".join(e["name"] for e in prefab_only_packs[:8])
        extra = "" if len(prefab_only_packs) <= 8 else f" (+{len(prefab_only_packs) - 8} more)"
        report.warnings.append(
            "Prefab-only POI packs detected (no rwgmixer.xml found). These typically won’t spawn naturally unless another mod injects them (spawn_all_POIs/CompoPack) or you place them manually. "
            f"Examples: {sample}{extra}."
        )

    # Prefab name collisions (best-effort, bounded)
    prefab_to_mods: Dict[str, set[str]] = {}
    for e in entries:
        if not e["has_prefabs_dir"]:
            continue
        try:
            for p in e["files"]:
                rel = str(p).replace("\\", "/").lower()
                if "/prefabs/" not in rel:
                    continue
                fn = p.name
                if not fn:
                    continue
                base = fn.split(".")[0].strip().lower()
                if not base or base in {"readme", "license"}:
                    continue
                prefab_to_mods.setdefault(base, set()).add(e["name"])
        except Exception:
            continue

    collisions = [(k, v) for k, v in prefab_to_mods.items() if len(v) >= 2]
    collisions.sort(key=lambda kv: (-len(kv[1]), kv[0]))
    if collisions:
        top = collisions[:8]
        parts = []
        for prefab, mods in top:
            mods_sorted = sorted(mods)
            shown = ", ".join(mods_sorted[:3])
            more = "" if len(mods_sorted) <= 3 else f" (+{len(mods_sorted) - 3} more)"
            parts.append(f"{prefab} → {shown}{more}")
        extra = "" if len(collisions) <= 8 else f" (+{len(collisions) - 8} more collisions)"
        report.warnings.append(
            "Possible prefab name collisions: multiple mods contain a prefab with the same name, and later-loading packs can silently overwrite earlier ones. "
            f"Examples: {'; '.join(parts)}{extra}."
        )

    if len(poi_packish) >= 6:
        report.warnings.append(
            "POI density caution: you have many POI packs enabled. 7DTD RWG has limited city/hub slots per tag/tier, so some POIs may be excluded even with correct injection."
        )


def is_patch_mod_name(folder_name: str) -> bool:
    try:
        nm = (folder_name or "").lower()
        return nm.startswith("999_conflictpatch_") or nm.startswith("conflictpatch_")
    except Exception:
        return False


def enforce_framework_load_order(mods: Sequence[Any]) -> List[Any]:
    """Force known framework mods to the front of the list.

    Some framework/base mods intentionally ship full UI XML files and can be
    misclassified as "late" UI mods by heuristic tiering. This step ensures
    frameworks load first so UI patch mods can safely apply after them.
    """

    mods_list = list(mods or [])
    ordered: List[Any] = []
    seen: set[int] = set()

    def _pull(predicate) -> None:
        for m in mods_list:
            try:
                if not predicate(m):
                    continue
            except Exception:
                continue
            mid = id(m)
            if mid in seen:
                continue
            seen.add(mid)
            ordered.append(m)

    def _name_l(m: Any) -> str:
        try:
            return str(getattr(m, "name", "") or "").lower()
        except Exception:
            return ""

    _pull(lambda m: "scor" in _name_l(m))
    _pull(lambda m: "uiframework" in _name_l(m))
    _pull(lambda m: "xuircore" in _name_l(m))
    # Any other frameworks flagged via metadata should also load early.
    _pull(lambda m: bool(getattr(m, "is_framework", False)))

    for m in mods_list:
        mid = id(m)
        if mid in seen:
            continue
        seen.add(mid)
        ordered.append(m)

    return ordered


def _safe_list_files(mod_path: Path) -> List[Path]:
    """Best-effort, bounded file listing.

    The load order engine only needs light evidence (selected XML names, presence
    of DLLs, and a handful of content folders). Fully recursive `rglob` over large
    mod trees can be extremely slow and can freeze the GUI during load-order
    generation.
    """

    out: List[Path] = []

    # Fast probe: capture high-signal files early (avoids missing DLLs/XMLs
    # in very large mod trees when the bounded full walk hits limits).
    try:
        probe_dirs: List[Path] = [mod_path]
        for rel in (
            "Config",
            "config",
            "Dll",
            "dll",
            "Scripts",
            "scripts",
        ):
            try:
                p = mod_path / rel
                if p.is_dir():
                    probe_dirs.append(p)
            except Exception:
                continue

        seen_probe: set[str] = set()
        for d in probe_dirs:
            try:
                for ent in os.scandir(str(d)):
                    try:
                        if not ent.is_file():
                            continue
                        bn = (ent.name or "").lower()
                        suf = (Path(ent.name).suffix or "").lower()
                        if suf in {".xml", ".dll"} or bn in {
                            "modinfo.xml",
                            "rwgmixer.xml",
                            "biomes.xml",
                            "worldglobal.xml",
                            "prefabs.xml",
                        }:
                            key = ent.path.lower()
                            if key in seen_probe:
                                continue
                            seen_probe.add(key)
                            out.append(Path(ent.path))
                    except Exception:
                        continue
            except Exception:
                continue

        # One-level deep probe for DLLs/XMLs in arbitrary subfolders.
        try:
            for ent in os.scandir(str(mod_path)):
                try:
                    if not ent.is_dir():
                        continue
                    for ent2 in os.scandir(ent.path):
                        try:
                            if not ent2.is_file():
                                continue
                            bn = (ent2.name or "").lower()
                            suf = (Path(ent2.name).suffix or "").lower()
                            if suf in {".xml", ".dll"} or bn in {
                                "modinfo.xml",
                                "rwgmixer.xml",
                                "biomes.xml",
                                "worldglobal.xml",
                                "prefabs.xml",
                            }:
                                key = ent2.path.lower()
                                if key in seen_probe:
                                    continue
                                seen_probe.add(key)
                                out.append(Path(ent2.path))
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
    except Exception:
        pass

    # Hard bounds to keep UI responsive on huge mod folders.
    max_scanned = 25_000
    max_kept = 5_000

    relevant_suffixes = {
        ".xml",
        ".dll",
        ".dds",
        ".png",
        ".jpg",
        ".wav",
        ".ogg",
        ".shader",
    }
    relevant_basenames = {
        "modinfo.xml",
        "rwgmixer.xml",
        "biomes.xml",
        "worldglobal.xml",
        "prefabs.xml",
        "progression.xml",
        "entityclasses.xml",
        "gamestages.xml",
        "buffs.xml",
        "perks.xml",
        "loot.xml",
        "items.xml",
        "blocks.xml",
        "recipes.xml",
        "vehicles.xml",
        "quests.xml",
        "windows.xml",
        "ui.xml",
        "materials.xml",
    }
    relevant_dir_markers = {
        "xui",
        "localization",
        "prefabs",
        "textures",
        "audio",
        "particles",
        "shaders",
    }

    scanned = 0
    try:
        # Use os.walk to avoid creating Path objects for every entry via rglob.
        for root, dirs, files in os.walk(str(mod_path)):
            # Prune obvious junk / caches.
            try:
                dirs[:] = [
                    d for d in dirs if d not in {".git", ".svn", "__pycache__"} and not d.lower().endswith(".bak")
                ]
            except Exception:
                pass

            root_lower = root.replace("\\", "/").lower()
            in_relevant_dir = any(f"/{m}/" in (root_lower + "/") for m in relevant_dir_markers)

            for fn in files:
                scanned += 1
                if scanned > max_scanned or len(out) >= max_kept:
                    raise StopIteration

                try:
                    bn = (fn or "").lower()
                    suffix = (Path(fn).suffix or "").lower()
                    if (suffix in relevant_suffixes) or (bn in relevant_basenames) or in_relevant_dir:
                        out.append(Path(root) / fn)
                except Exception:
                    continue
    except StopIteration:
        pass
    except Exception:
        return []

    out.sort(key=lambda p: str(p).lower())
    return out


def _has_any_suffix(files: Sequence[Path], suffixes: Sequence[str]) -> bool:
    suf = {s.lower() for s in suffixes}
    for p in files:
        if p.suffix.lower() in suf:
            return True
    return False


def _has_any_rel_fragment(files: Sequence[Path], fragment: str) -> bool:
    frag = (fragment or "").replace("\\", "/").lower()
    if not frag:
        return False
    for p in files:
        rel = str(p).replace("\\", "/").lower()
        if frag in rel:
            return True
    return False


def _basename_set(files: Sequence[Path]) -> set[str]:
    return {p.name.lower() for p in files}


def parse_declared_dependencies(mod_path: Path) -> List[str]:
    """Best-effort parse of ModInfo.xml dependencies.

    7DTD mod ecosystems are inconsistent; this parser is tolerant and returns
    a list of dependency identifiers (usually folder/display names).
    """

    modinfo = mod_path / "ModInfo.xml"
    if not modinfo.exists():
        return []

    try:
        tree = ET.parse(str(modinfo))
        root = tree.getroot()
    except Exception:
        return []

    deps: List[str] = []

    # Common shapes:
    #   <Dependencies>
    #     <Dependency name="Foo" />
    #     <Dependency value="Foo" />
    #     <Mod name="Foo" />
    #   </Dependencies>
    # Also seen:
    #   <RequiredMod name="Foo" />
    #   <RequiredMods><RequiredMod value="Foo"/></RequiredMods>
    for elem in root.iter():
        tag = (elem.tag or "").strip().lower()
        if tag in {
            "dependency",
            "depend",
            "mod",
            "requiredmod",
            "requiredmods",
            "requiremod",
            "requiremods",
            "required",
            "requires",
        }:
            # ModInfo.xml in the wild often varies attribute casing (e.g. Name vs name).
            attrib = {}
            try:
                attrib = {str(k).strip().lower(): v for k, v in (elem.attrib or {}).items()}
            except Exception:
                attrib = {}

            for k in ("name", "value", "mod", "id", "modid"):
                v = str(attrib.get(k) or "").strip()
                if v:
                    deps.append(v)
                    break

    out: List[str] = []
    seen = set()
    for d in deps:
        d2 = normalize_mod_id(d)
        key = d2.lower()
        if not d2 or key in seen:
            continue
        seen.add(key)
        out.append(d2)
    return out


def infer_tier(mod: Any, *, file_cache: Optional[Dict[str, List[Path]]] = None) -> str:
    """Infer tier from categories + file evidence.

    No numeric scoring: returns a canonical tier string.
    """

    name = str(getattr(mod, "name", "") or "")
    path_str = str(getattr(mod, "path", "") or "").strip()
    path = Path(path_str) if path_str else None

    if is_patch_mod_name(name) or bool(getattr(mod, "is_patch", False)):
        return "Patch Mods"

    cats = [str(c) for c in (getattr(mod, "categories", None) or [])]
    cat = str(getattr(mod, "category", "") or "")
    cats_lower = {c.lower() for c in cats + ([cat] if cat else [])}

    # Fast positive signals from XML-derived categorization
    if any("overhaul" in c for c in cats_lower) or bool(getattr(mod, "is_overhaul", False)):
        return "Gameplay Overhauls"

    # File heuristics
    files = None
    try:
        if file_cache is not None:
            files = file_cache.get(str(path))
    except Exception:
        files = None
    if files is None:
        # Important: if path is missing/invalid, do NOT scan "." (workspace root).
        if path is None or not path.is_dir():
            files = []
        else:
            files = _safe_list_files(path)
            if file_cache is not None:
                file_cache[str(path)] = files

    basenames = _basename_set(files)

    name_l = name.lower()

    def _has_name_kw(*kws: str) -> bool:
        try:
            return any((kw or "").lower() in name_l for kw in kws)
        except Exception:
            return False

    # Weapon frameworks / animation bases (FPV rigs, controllers, etc.)
    weapon_fw_kws = (
        "weapon framework",
        "fpv",
        "rig",
        "animation",
        "anim",
        "nva",
        "izy",
        "izayo",
        "cls",
        "arms",
    )

    # Frameworks / backend systems (DLL-based)
    if _has_any_suffix(files, [".dll"]):
        # Core frameworks should load first (Harmony, core libs, community frameworks).
        if _has_name_kw(
            "harmony",
            "kfcommon",
            "kflib",
            "score",
            "ocb",
            "core",
            "utilitylib",
            "customparticleloader",
        ) and not _has_name_kw(*weapon_fw_kws):
            return "Core Frameworks"
        # Everything else with DLLs is treated as backend/system layer.
        return "API / Backend Systems"

    # UI: XUi, windows.xml, localization
    if (
        "windows.xml" in basenames
        or "ui.xml" in basenames
        or _has_any_rel_fragment(files, "/xui/")
        or _has_any_rel_fragment(files, "/localization/")
    ):
        return "Utility / QoL Mods"

    # Worldgen / POI: prefabs, rwgmixer, biomes
    if (
        "prefabs.xml" in basenames
        or "rwgmixer.xml" in basenames
        or "biomes.xml" in basenames
        or "worldglobal.xml" in basenames
        or _has_any_rel_fragment(files, "/prefabs/")
    ):
        return "Worldgen / POI Mods"

    # Visual / Audio
    if (
        "materials.xml" in basenames
        or _has_any_suffix(files, [".dds", ".png", ".jpg", ".wav", ".ogg"])
        or _has_any_rel_fragment(files, "/textures/")
        or _has_any_rel_fragment(files, "/audio/")
        or _has_any_rel_fragment(files, "/particles/")
    ):
        return "Visual / Audio Mods"

    # Gameplay Overhauls (core mechanics)
    if any(
        f in basenames
        for f in (
            "progression.xml",
            "entityclasses.xml",
            "gamestages.xml",
            "buffs.xml",
            "perks.xml",
            "loot.xml",
        )
    ):
        # If it looks like a weapon/animation base, keep it in the weapon framework bucket.
        if _has_name_kw(*weapon_fw_kws) and any(f in basenames for f in ("items.xml", "entityclasses.xml")):
            return "Weapon Frameworks & Animation"
        return "Gameplay Overhauls"

    # Content Additions (items/blocks/etc)
    if any(
        f in basenames
        for f in (
            "items.xml",
            "blocks.xml",
            "recipes.xml",
            "vehicles.xml",
            "quests.xml",
        )
    ):
        # Weapon packs should come after weapon frameworks.
        if _has_name_kw(
            "weapon",
            "gun",
            "guns",
            "firearm",
            "rifle",
            "pistol",
            "shotgun",
            "smg",
            "sniper",
            "arsenal",
            "pack",
        ):
            return "Weapon Packs"
        # Weapon ecosystems often omit explicit keywords; catch common family names.
        if _has_name_kw("izy", "izayo", "cls") and "items.xml" in basenames:
            return "Weapon Packs"

        # Block/world packs tend to impact worldgen; keep them later.
        if "blocks.xml" in basenames and (
            _has_name_kw("biome", "world", "poi", "prefab", "terrain")
            or "rwgmixer.xml" in basenames
            or "biomes.xml" in basenames
        ):
            return "Worldgen / POI Mods"

        return "Content Additions"

    # Fall back to category hints
    if any("ui" == c or "qol" in c or "utility" in c for c in cats_lower):
        return "Utility / QoL Mods"
    if any("visual" in c or "graphic" in c or "audio" in c for c in cats_lower):
        return "Visual / Audio Mods"
    if any("prefab" in c or "poi" in c or "map" in c or "world" in c for c in cats_lower):
        return "Worldgen / POI Mods"
    if any("weapon" in c for c in cats_lower):
        return "Weapon Packs"

    return "Content Additions"


def infer_semantic_impact(mod: Any, *, file_cache: Optional[Dict[str, List[Path]]] = None) -> str:
    """Infer semantic impact (global/additive/presentation/destructive)."""

    name = str(getattr(mod, "name", "") or "")
    path_str = str(getattr(mod, "path", "") or "").strip()
    path = Path(path_str) if path_str else None

    if is_patch_mod_name(name) or bool(getattr(mod, "is_patch", False)):
        return "Additive Content"

    files = None
    try:
        if file_cache is not None:
            files = file_cache.get(str(path))
    except Exception:
        files = None
    if files is None:
        # Important: if path is missing/invalid, do NOT scan "." (workspace root).
        if path is None or not path.is_dir():
            files = []
        else:
            files = _safe_list_files(path)
            if file_cache is not None:
                file_cache[str(path)] = files

    basenames = _basename_set(files)

    destructive = any(
        f in basenames
        for f in (
            "rwgmixer.xml",
            "biomes.xml",
            "worldglobal.xml",
        )
    ) or _has_any_rel_fragment(files, "/prefabs/")

    if destructive:
        return "Destructive Changes"

    global_system = any(
        f in basenames
        for f in (
            "progression.xml",
            "entityclasses.xml",
            "gamestages.xml",
        )
    )
    if global_system:
        return "Global System Changes"

    presentation = (
        "windows.xml" in basenames
        or "ui.xml" in basenames
        or _has_any_rel_fragment(files, "/xui/")
        or _has_any_suffix(files, [".dds", ".png", ".jpg", ".wav", ".ogg"])
    )
    if presentation:
        return "Presentation Layer"

    return "Additive Content"


def infer_framework_kind(
    mod: Any,
    *,
    tier: Optional[str] = None,
    file_cache: Optional[Dict[str, List[Path]]] = None,
) -> str:
    """Infer framework sub-priority.

    Used only when tier is Core Frameworks.
    """

    if tier is None:
        try:
            tier = infer_tier(mod, file_cache=file_cache)
        except Exception:
            tier = ""
    if tier != "Core Frameworks":
        return ""

    name = str(getattr(mod, "name", "") or "").lower()
    path_str = str(getattr(mod, "path", "") or "").strip()
    path = Path(path_str) if path_str else None

    files = None
    try:
        if file_cache is not None:
            files = file_cache.get(str(path))
    except Exception:
        files = None
    if files is None:
        # Important: if path is missing/invalid, do NOT scan "." (workspace root).
        if path is None or not path.is_dir():
            files = []
        else:
            files = _safe_list_files(path)
            if file_cache is not None:
                file_cache[str(path)] = files

    # Harmony
    try:
        if "harmony" in name:
            return "Harmony"
        for p in files:
            bn = p.name.lower()
            if bn in {"0harmony.dll", "harmony.dll"} or "harmony" in bn:
                return "Harmony"
    except Exception:
        pass

    # Core libraries (heuristic)
    try:
        if any(k in name for k in ("core", "library", "lib")):
            return "Core Libraries"
    except Exception:
        pass

    return "Community Frameworks"


def _tier_key(tier: str) -> Tuple[int, str]:
    try:
        return (TIER_ORDER.index(tier), tier)
    except ValueError:
        return (len(TIER_ORDER), tier)


def _semantic_key(impact: str) -> Tuple[int, str]:
    try:
        return (SEMANTIC_ORDER.index(impact), impact)
    except ValueError:
        return (len(SEMANTIC_ORDER), impact)


def _stable_base_key(
    mod: Any,
    *,
    tier: Optional[str] = None,
    impact: Optional[str] = None,
    framework_kind: Optional[str] = None,
    ui_kind: Optional[str] = None,
) -> Tuple[int, int, int, int, str]:
    """Deterministic ordering key used as the engine's default preference.

    IMPORTANT: Tier/semantic/framework precedence are treated as *preferences* via
    this key, not as explicit O(n^2) constraint edges. Hard constraints (dependency,
    patch parents, user rules) are encoded as edges.
    """

    t = str(tier or "")
    s = str(impact or "")
    fk = str(framework_kind or "")

    try:
        tier_idx = TIER_ORDER.index(t)
    except ValueError:
        tier_idx = len(TIER_ORDER)

    try:
        semantic_idx = SEMANTIC_ORDER.index(s)
    except ValueError:
        semantic_idx = len(SEMANTIC_ORDER)

    # Only meaningful within Core Frameworks
    if t == "Core Frameworks":
        try:
            framework_idx = FRAMEWORK_KIND_ORDER.index(fk)
        except ValueError:
            framework_idx = len(FRAMEWORK_KIND_ORDER)
    else:
        framework_idx = len(FRAMEWORK_KIND_ORDER)

    # UI preference: ensure HUD mods tend to load later than other UI mods.
    # (Last loaded wins for XUi/windows.xml overrides.)
    uk = str(ui_kind or "").strip().lower()
    ui_rank_map = {
        "framework": 0,
        "extension": 1,
        "hud": 2,
        "": -1,
        "unknown": -1,
    }
    ui_rank = int(ui_rank_map.get(uk, -1))

    # Deterministic tie-breaker: normalized id then original name
    mid = normalize_mod_id(str(getattr(mod, "name", "") or "")).lower()
    name = str(getattr(mod, "name", "") or "").lower()
    return (tier_idx, framework_idx, semantic_idx, ui_rank, mid or name)


def infer_ui_kind(mod: Any, *, file_cache: Optional[Dict[str, List[Path]]] = None) -> str:
    """Infer UI sub-kind: framework | extension | hud | unknown.

    This is a light heuristic used only to improve deterministic ordering
    preferences inside the same tier/impact bucket.
    """

    name = str(getattr(mod, "name", "") or "")
    name_l = name.lower()

    # Strong name signals first
    if any(k in name_l for k in ("uiframework", "ui framework", "xuircore")):
        return "framework"
    if "hud" in name_l:
        return "hud"

    path_str = str(getattr(mod, "path", "") or "").strip()
    path = Path(path_str) if path_str else None

    files = None
    try:
        if file_cache is not None:
            files = file_cache.get(str(path))
    except Exception:
        files = None
    if files is None:
        if path is None or (not path.is_dir()):
            files = []
        else:
            files = _safe_list_files(path)
            if file_cache is not None:
                file_cache[str(path)] = files

    basenames = _basename_set(files)

    # Framework-ish file signals
    try:
        for fp in files:
            s = str(fp).replace("\\", "/").lower()
            if "/xui_common/" in s and (s.endswith("styles.xml") or s.endswith("controls.xml")):
                return "framework"
    except Exception:
        pass

    # HUD-ish file signals
    if _has_any_rel_fragment(files, "/xui_menu/"):
        return "hud"

    # General UI signal
    if (
        "windows.xml" in basenames
        or "ui.xml" in basenames
        or _has_any_rel_fragment(files, "/xui/")
        or _has_any_rel_fragment(files, "/localization/")
    ):
        return "extension"

    return "unknown"


def _topo_sort(
    nodes: List[str],
    edges: List[OrderingEdge],
    *,
    base_order_key: Dict[str, Tuple[int, int, int, str]],
    report: LoadOrderReport,
    hard_layers: Iterable[str],
    drop_layers_order: Sequence[str],
) -> List[str]:
    """Topological sort with deterministic cycle breaking.

    - Layers in `hard_layers` are never dropped unless no other choice.
    - `drop_layers_order` is evaluated from lowest authority to highest; we drop edges
      from earlier entries first.
    """

    node_set = set(nodes)
    active_edges = [e for e in edges if e.before in node_set and e.after in node_set and e.before != e.after]

    hard_layers_set = set(hard_layers)
    layer_rank = {layer: i for i, layer in enumerate(drop_layers_order)}

    def node_sort_key(n: str) -> Tuple[int, int, int, str, str]:
        nl = n.lower()
        base = base_order_key.get(n)
        if base is None:
            base = (999, 999, 999, nl)
        return (base[0], base[1], base[2], base[3], nl)

    # Deterministic edge ordering
    active_edges.sort(
        key=lambda e: (
            layer_rank.get(e.layer, 999),
            e.before.lower(),
            e.after.lower(),
            e.reason,
        )
    )

    def build_graph(cur_edges: List[OrderingEdge]):
        out_edges: Dict[str, List[str]] = {n: [] for n in nodes}
        indeg: Dict[str, int] = {n: 0 for n in nodes}
        for e in cur_edges:
            out_edges[e.before].append(e.after)
            indeg[e.after] += 1
        for n in nodes:
            out_edges[n].sort(key=node_sort_key)
        return out_edges, indeg

    cur = list(active_edges)

    while True:
        out_edges, indeg = build_graph(cur)

        available: List[Tuple[Tuple[int, int, int, str, str], str]] = []
        for n in nodes:
            if indeg.get(n, 0) == 0:
                heapq.heappush(available, (node_sort_key(n), n))

        ordered: List[str] = []
        indeg2 = dict(indeg)

        while available:
            _k, n = heapq.heappop(available)
            ordered.append(n)
            for m in out_edges.get(n, []):
                indeg2[m] -= 1
                if indeg2[m] == 0:
                    heapq.heappush(available, (node_sort_key(m), m))

        if len(ordered) == len(nodes):
            report.applied_edges = list(cur)
            return ordered

        # Cycle: drop a non-hard edge if possible.
        remaining = [e for e in cur if e.layer not in hard_layers_set]
        if not remaining:
            # Can't drop anything else; force a deterministic break.
            report.errors.append("Dependency cycle detected that could not be resolved automatically.")
            nodes_sorted = list(nodes)
            nodes_sorted.sort(key=node_sort_key)
            report.applied_edges = list(cur)
            return nodes_sorted

        # Drop the lowest-authority edge deterministically
        def drop_key(e: OrderingEdge):
            return (
                layer_rank.get(e.layer, 999),
                e.before.lower(),
                e.after.lower(),
                e.reason,
            )

        victim = min(remaining, key=drop_key)
        cur = [e for e in cur if e != victim]
        report.dropped_edges.append(victim)
        report.warnings.append(
            f"Cycle detected; dropped constraint ({victim.layer}): {victim.before} -> {victim.after} ({victim.reason})"
        )


def compute_load_order(
    mods: Sequence[Any],
    *,
    user_rules: Iterable[Any] = (),
    include_disabled: bool = False,
) -> Tuple[List[Any], LoadOrderReport]:
    """Compute deterministic load order using layered rules.

    This engine is constraint-based (no numeric scoring):
      1) Dependency graph
      2) Category precedence (tiers)
      3) Semantic impact level
      4) Conflict overrides (best-effort)
      5) Patch enforcement
      6) User rules
      7) Final stability pass
    """

    report = LoadOrderReport()

    # Filter mods
    active: List[Any] = []
    for m in mods or []:
        if not include_disabled and bool(getattr(m, "disabled", False)):
            continue
        active.append(m)

    # Stable ids
    id_for: Dict[str, Any] = {}
    key_for: Dict[str, str] = {}
    for m in active:
        mid = normalize_mod_id(str(getattr(m, "name", "") or ""))
        if not mid:
            mid = str(getattr(m, "name", "") or "")
        # Deduplicate by id deterministically
        if mid.lower() in id_for:
            # Keep both using disambiguated key
            alt = f"{mid}::{Path(str(getattr(m, 'path', ''))).name}"
            key_for[alt] = mid
            id_for[alt.lower()] = m
        else:
            key_for[mid] = mid
            id_for[mid.lower()] = m

    nodes = list(key_for.keys())

    file_cache: Dict[str, List[Path]] = {}
    dep_cache: Dict[str, List[str]] = {}

    def _declared_deps_for(mod: Any) -> List[str]:
        p = str(getattr(mod, "path", "") or "").strip()
        if not p:
            return []
        cached = dep_cache.get(p)
        if cached is not None:
            return cached
        try:
            pp = Path(p)
            if not pp.is_dir():
                dep_cache[p] = []
            else:
                dep_cache[p] = parse_declared_dependencies(pp)
        except Exception:
            dep_cache[p] = []
        return dep_cache[p]

    # (2) Tier/semantic/framework inference (cached) used for both reporting and
    # deterministic preference ordering.
    tiers_by_node: Dict[str, str] = {}
    impacts_by_node: Dict[str, str] = {}
    framework_kind_by_node: Dict[str, str] = {}
    ui_kind_by_node: Dict[str, str] = {}
    for node in nodes:
        m = id_for.get(node.lower())
        if not m:
            continue
        tier = infer_tier(m, file_cache=file_cache)
        impact = infer_semantic_impact(m, file_cache=file_cache)
        tiers_by_node[node] = tier
        impacts_by_node[node] = impact
        try:
            ui_kind_by_node[node] = infer_ui_kind(m, file_cache=file_cache)
        except Exception:
            ui_kind_by_node[node] = "unknown"
        if tier == "Core Frameworks":
            try:
                framework_kind_by_node[node] = infer_framework_kind(m, tier=tier, file_cache=file_cache)
            except Exception:
                framework_kind_by_node[node] = "Community Frameworks"

    base_order_key: Dict[str, Tuple[int, int, int, str]] = {}
    for node in nodes:
        m = id_for.get(node.lower())
        if not m:
            continue
        base_order_key[node] = _stable_base_key(
            m,
            tier=tiers_by_node.get(node),
            impact=impacts_by_node.get(node),
            framework_kind=framework_kind_by_node.get(node),
            ui_kind=ui_kind_by_node.get(node),
        )

    # Fast lookup: normalized id -> node key (deterministic: first seen wins)
    node_by_norm: Dict[str, str] = {}
    for n in nodes:
        try:
            nn = normalize_mod_id(n).lower()
        except Exception:
            nn = str(n or "").lower()
        if not nn:
            continue
        if nn not in node_by_norm:
            node_by_norm[nn] = n

    # Collect edges
    edges: List[OrderingEdge] = []

    # (1) Dependency graph: Mod must load AFTER its dependencies.
    for node in nodes:
        m = id_for.get(node.lower())
        if not m:
            continue
        deps = _declared_deps_for(m)
        for dep in deps:
            # match by normalized id
            dep_id = normalize_mod_id(dep)
            target_node = node_by_norm.get(dep_id.lower())
            if not target_node:
                report.warnings.append(f"Missing dependency: '{node}' depends on '{dep_id}', but it was not found.")
                continue

            # Dependency edges must always apply.
            # If tiers disagree, record a warning (tier is a preference, not a hard rule).
            try:
                dep_tier = tiers_by_node.get(target_node, "")
                mod_tier = tiers_by_node.get(node, "")
                dep_idx = _tier_key(str(dep_tier or ""))[0]
                mod_idx = _tier_key(str(mod_tier or ""))[0]
                if dep_idx > mod_idx:
                    report.warnings.append(
                        f"Dependency crosses tier preference: '{node}' (tier: {mod_tier}) depends on '{target_node}' (tier: {dep_tier}). Dependency ordering will be enforced."
                    )
            except Exception:
                pass

            edges.append(
                OrderingEdge(
                    before=target_node, after=node, layer="dependency", reason=f"Declared dependency: {dep_id}"
                )
            )

    # (2/3) Tier/semantic/framework precedence are enforced via base_order_key,
    # not via explicit edges (avoids O(n^2) edge explosions on large mod sets).

    # (4) Conflict overrides (best-effort): when both edit same XML node.
    # We use mod.conflicts entries emitted by scanners as a proxy.
    # Rule: later tiers load later (win overrides); Patch Mods should win last.
    def override_rank(node_id: str) -> Tuple[int, str]:
        tier = tiers_by_node.get(node_id, "")
        # Higher rank loads later (wins overrides)
        order = [
            "Core Frameworks",
            "API / Backend Systems",
            "Gameplay Overhauls",
            "Content Additions",
            "Weapon Frameworks & Animation",
            "Weapon Packs",
            "Visual / Audio Mods",
            "Worldgen / POI Mods",
            "Utility / QoL Mods",
            "Patch Mods",
        ]
        try:
            return (order.index(tier), tier)
        except ValueError:
            return (0, tier)

    by_name = {normalize_mod_id(n).lower(): n for n in nodes}
    for node in nodes:
        m = id_for.get(node.lower())
        if not m:
            continue

        # Duplicate IDs are never auto-resolved (requires user decision).
        try:
            for c in getattr(m, "conflicts", []) or []:
                if str(c.get("conflict_type") or "") == "duplicate_id":
                    other = normalize_mod_id(str(c.get("with") or ""))
                    report.errors.append(
                        f"Duplicate ID conflict between '{normalize_mod_id(node)}' and '{other}': manual resolution required (renaming blocked)."
                    )
        except Exception:
            pass

        for c in getattr(m, "conflicts", []) or []:
            try:
                ctype = str(c.get("conflict_type") or "")
                if ctype not in {"xml_override"}:
                    continue
                other = str(c.get("with") or "")
                other_id = normalize_mod_id(other)
                other_node = by_name.get(other_id.lower())
                if not other_node:
                    continue

                # Determine who should load later (winner)
                a = node
                b = other_node
                if a == b:
                    continue

                ra = override_rank(a)
                rb = override_rank(b)
                if ra == rb:
                    continue

                winner = a if ra > rb else b
                loser = b if winner == a else a
                edges.append(
                    OrderingEdge(
                        before=loser,
                        after=winner,
                        layer="conflict",
                        reason=f"Conflict override ({ctype}): {winner} should win",
                    )
                )
            except Exception:
                continue

    # (5) Patch enforcement: patch mods must load after both parents.
    for node in nodes:
        if tiers_by_node.get(node) != "Patch Mods":
            continue
        m = id_for.get(node.lower())
        if not m:
            continue
        deps = _declared_deps_for(m)
        if not deps:
            # Best-effort: allow applying load order even if patch has no explicit parents.
            # We still treat it as a warning; tier-based ordering keeps patches late.
            report.warnings.append(
                f"Patch mod '{node}' has no declared parents in ModInfo.xml (ordering may be less accurate)."
            )
        for dep in deps:
            dep_id = normalize_mod_id(dep)
            parent_node = node_by_norm.get(dep_id.lower())
            if not parent_node:
                report.errors.append(f"Patch mod '{node}' requires '{dep_id}', but it is missing.")
                continue
            edges.append(OrderingEdge(before=parent_node, after=node, layer="patch", reason=f"Patch parent: {dep_id}"))

    # (6) User rules: Load Before / Load After / Never Together.
    # These override everything else.
    for r in user_rules or []:
        try:
            if not bool(getattr(r, "enabled", True)):
                continue
            rtype = str(getattr(r, "type", "") or "")
            a = normalize_mod_id(str(getattr(r, "mod_a", "") or ""))
            b = normalize_mod_id(str(getattr(r, "mod_b", "") or ""))
            if not a or not b:
                continue

            # Resolve to actual node keys
            na = node_by_norm.get(a.lower())
            nb = node_by_norm.get(b.lower())
            if not na or not nb:
                continue

            if rtype == "load_before":
                edges.append(OrderingEdge(before=na, after=nb, layer="user", reason=f"User rule: {a} before {b}"))
            elif rtype == "load_after":
                edges.append(OrderingEdge(before=nb, after=na, layer="user", reason=f"User rule: {a} after {b}"))
            elif rtype == "never_together":
                report.warnings.append(f"User rule: '{a}' and '{b}' should never load together.")
        except Exception:
            continue

    # (6b) Worldgen/POI hard constraints (RWG override rules)
    # These are encoded as edges (not preferences) so the engine can guarantee:
    #   Better Generation < Better Biomes < spawn_all_POIs < POI packs
    # and, more generally, worldgen/RWG mods must load before POI packs.
    try:
        basenames_by_node: Dict[str, set[str]] = {}
        has_prefabs_dir_by_node: Dict[str, bool] = {}

        def _files_for_node(n: str) -> List[Path]:
            mm = id_for.get(n.lower())
            if not mm:
                return []
            return _mod_files_for_diagnostics(mm, file_cache=file_cache)

        def _basenames_for_node(n: str) -> set[str]:
            cached = basenames_by_node.get(n)
            if cached is not None:
                return cached
            files = _files_for_node(n)
            basenames_by_node[n] = _basename_set(files)
            try:
                has_prefabs_dir_by_node[n] = _has_any_rel_fragment(files, "/prefabs/")
            except Exception:
                has_prefabs_dir_by_node[n] = False
            return basenames_by_node[n]

        def _name_l(n: str) -> str:
            mm = id_for.get(n.lower())
            return str(getattr(mm, "name", "") or "").lower() if mm else str(n or "").lower()

        def _is_better_generation(n: str) -> bool:
            nm = _name_l(n)
            return ("better generation" in nm) or ("bettergen" in nm) or ("better_generation" in nm)

        def _is_better_biomes(n: str) -> bool:
            nm = _name_l(n)
            return ("better biomes" in nm) or ("betterbiomes" in nm) or ("better_biomes" in nm)

        def _is_spawn_all_pois(n: str) -> bool:
            nm = _name_l(n)
            return ("spawn_all_poi" in nm) or ("spawn all poi" in nm) or ("spawnallpoi" in nm)

        def _is_worldgen_mod(n: str) -> bool:
            bn = _basenames_for_node(n)
            nm = _name_l(n)
            return (
                ("rwgmixer.xml" in bn)
                or ("biomes.xml" in bn)
                or ("worldglobal.xml" in bn)
                or ("rwg" in nm)
                or ("worldgen" in nm)
                or ("biome" in nm and "better" in nm)
            )

        def _is_poi_pack(n: str) -> bool:
            if _is_better_generation(n) or _is_better_biomes(n) or _is_spawn_all_pois(n):
                return False
            bn = _basenames_for_node(n)
            nm = _name_l(n)
            has_prefabs_dir = bool(has_prefabs_dir_by_node.get(n, False))
            has_prefabs_xml = "prefabs.xml" in bn
            is_packish = has_prefabs_dir or has_prefabs_xml or ("poi" in nm) or ("prefab" in nm)
            if not is_packish:
                return False
            # Worldgen mods are not treated as POI packs even if they ship prefabs.
            if _is_worldgen_mod(n):
                return False
            return True

        bg_nodes = [n for n in nodes if _is_better_generation(n)]
        bb_nodes = [n for n in nodes if _is_better_biomes(n)]
        sp_nodes = [n for n in nodes if _is_spawn_all_pois(n)]
        poi_nodes = [n for n in nodes if _is_poi_pack(n)]
        worldgen_nodes = [n for n in nodes if _is_worldgen_mod(n)]

        # Specific chain constraints
        if bg_nodes and bb_nodes:
            edges.append(
                OrderingEdge(
                    before=bg_nodes[0],
                    after=bb_nodes[0],
                    layer="worldgen",
                    reason="Better Generation must load before Better Biomes",
                )
            )
        if bb_nodes and sp_nodes:
            edges.append(
                OrderingEdge(
                    before=bb_nodes[0],
                    after=sp_nodes[0],
                    layer="worldgen",
                    reason="Better Biomes must load before spawn_all_POIs",
                )
            )
        if sp_nodes and poi_nodes:
            for pn in poi_nodes:
                edges.append(
                    OrderingEdge(
                        before=sp_nodes[0],
                        after=pn,
                        layer="worldgen",
                        reason="spawn_all_POIs must load before POI packs",
                    )
                )

        # General RWG rule: worldgen mods before POI packs
        if worldgen_nodes and poi_nodes:
            for wg in worldgen_nodes:
                for pn in poi_nodes:
                    edges.append(
                        OrderingEdge(
                            before=wg,
                            after=pn,
                            layer="worldgen",
                            reason="Worldgen mods must load before POI packs",
                        )
                    )
    except Exception:
        # Diagnostics should never break ordering.
        pass

    # (7) Final stability pass will be executed after ordering.
    hard_layers = {"dependency", "user", "patch", "worldgen"}

    drop_layers_order = (
        "conflict",
        "worldgen",
        "patch",
        "dependency",
        "user",
    )

    ordered_ids = _topo_sort(
        nodes,
        edges,
        base_order_key=base_order_key,
        report=report,
        hard_layers=hard_layers,
        drop_layers_order=drop_layers_order,
    )

    ordered_mods: List[Any] = []
    for nid in ordered_ids:
        m = id_for.get(nid.lower())
        if m is None:
            continue
        # Attach inferred fields for UI usage
        try:
            setattr(m, "tier", tiers_by_node.get(nid))
        except Exception:
            pass
        try:
            setattr(m, "semantic_impact", impacts_by_node.get(nid))
        except Exception:
            pass
        ordered_mods.append(m)

    # Framework-first enforcement (explicit): keeps base UI frameworks ahead of
    # patch mods even when heuristics misclassify them as late UI.
    ordered_mods = enforce_framework_load_order(ordered_mods)

    # Final stability: dependency validation
    pos = {normalize_mod_id(str(getattr(m, "name", "") or "")): i for i, m in enumerate(ordered_mods)}
    for e in edges:
        if e.layer != "dependency":
            continue
        a = normalize_mod_id(e.before)
        b = normalize_mod_id(e.after)
        if a in pos and b in pos and pos[a] > pos[b]:
            report.errors.append(f"Dependency violation: '{b}' is ordered before its dependency '{a}'.")

    # Destructive change warnings
    for m in ordered_mods:
        if infer_semantic_impact(m, file_cache=file_cache) == "Destructive Changes":
            report.warnings.append(
                f"Worldgen/POI risk: '{normalize_mod_id(str(getattr(m, 'name', '') or ''))}' likely requires a new world."
            )

    # Targeted POI spawning diagnostics
    try:
        _add_poi_spawn_diagnostics(ordered_mods, report=report, file_cache=file_cache)
    except Exception:
        pass

    report.debug["tiers_by_mod"] = dict(tiers_by_node)
    report.debug["semantic_by_mod"] = dict(impacts_by_node)

    # Dependency visualization (DOT)
    try:
        dep_edges = [e for e in edges if e.layer in {"dependency", "patch", "user"}]
        dep_edges.sort(key=lambda e: (e.layer, e.before.lower(), e.after.lower()))
        lines = ["digraph LoadOrder {"]
        for e in dep_edges:
            a = e.before.replace('"', "'")
            b = e.after.replace('"', "'")
            label = f"{e.layer}: {e.reason}".replace('"', "'")
            lines.append(f'  "{a}" -> "{b}" [label="{label}"];')
        lines.append("}")
        report.debug["dependency_dot"] = "\n".join(lines)
    except Exception:
        pass

    return ordered_mods, report
