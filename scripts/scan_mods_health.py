"""Quick health scan for a 7 Days to Die Mods folder.

Focus:
- Mods that will NOT load in-game (missing ModInfo.xml and not a prefab-only POI pack)
- Wrapper/container folders that likely came from an extra zip nesting level
- Worldgen / POI signals (rwgmixer/biomes/worldglobal/prefabs)

Usage:
  python scripts/scan_mods_health.py
  python scripts/scan_mods_health.py --mods-path "D:/Steam/steamapps/common/7 Days To Die/Mods"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


PREFAB_EXTS = {".blocks.nim", ".mesh", ".ins", ".tts"}
WORLDGEN_HINT_FILES = {"rwgmixer.xml", "biomes.xml", "worldglobal.xml", "radiation.xml"}


@dataclass(frozen=True)
class Entry:
    name: str
    path: Path
    has_modinfo: bool
    is_poi_prefab_only: bool
    nested_modinfos: List[Path]
    has_prefabs_dir: bool
    worldgen_files: List[str]


def _load_config_mods_path(repo_root: Path) -> Optional[str]:
    cfg_path = repo_root / "config.json"
    if not cfg_path.exists():
        return None
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            raw = data.get("mods_path")
            if raw and str(raw).strip():
                return str(raw)
    except Exception:
        return None
    return None


def _iter_children(mods_dir: Path) -> Iterable[Path]:
    try:
        for child in mods_dir.iterdir():
            if child.is_dir():
                # Skip internal temp folders if present
                if child.name.startswith("__TMP_RENAME__"):
                    continue
                yield child
    except Exception:
        return


def _is_poi_prefab_only(mod_dir: Path) -> bool:
    # Mirrors gui/app.py is_poi_prefab_mod(), but keeps runtime bounded.
    has_prefab_assets = False
    has_prefab_xml = False

    try:
        for root, dirs, files in os.walk(str(mod_dir)):
            for fn in files:
                name_lower = fn.lower()
                if name_lower.endswith(".xml") and name_lower != "modinfo.xml":
                    has_prefab_xml = True
                _, ext = os.path.splitext(fn)
                if ext.lower() in PREFAB_EXTS:
                    has_prefab_assets = True
            for d in dirs:
                if d.lower() in {"prefabs", "poi", "pois"}:
                    has_prefab_assets = True
            # short-circuit
            if has_prefab_assets and has_prefab_xml:
                return True
    except Exception:
        return False

    return has_prefab_assets and has_prefab_xml


def _find_nested_modinfos(mod_dir: Path, *, max_depth: int = 2) -> List[Path]:
    out: List[Path] = []

    def _depth(rel: Path) -> int:
        # depth of relative path parts
        return len(rel.parts)

    try:
        for p in mod_dir.rglob("ModInfo.xml"):
            try:
                rel = p.relative_to(mod_dir)
            except Exception:
                continue
            if _depth(rel) <= max_depth + 1:  # include file itself
                out.append(p)
    except Exception:
        return []

    # Exclude the root ModInfo.xml if present
    root = mod_dir / "ModInfo.xml"
    out = [p for p in out if p.resolve() != root.resolve()]
    out.sort(key=lambda p: str(p).lower())
    return out


def _worldgen_files(mod_dir: Path) -> List[str]:
    cfg = mod_dir / "Config"
    if not cfg.is_dir():
        return []
    found: List[str] = []
    try:
        for fn in WORLDGEN_HINT_FILES:
            p = cfg / fn
            if p.is_file():
                found.append(fn)
    except Exception:
        return []
    return found


def _scan_entry(mod_dir: Path) -> Entry:
    has_modinfo = (mod_dir / "ModInfo.xml").is_file()
    nested = _find_nested_modinfos(mod_dir, max_depth=2)
    is_poi = (not has_modinfo) and _is_poi_prefab_only(mod_dir)
    has_prefabs_dir = (mod_dir / "Prefabs").is_dir() or (mod_dir / "prefabs").is_dir()
    wg = _worldgen_files(mod_dir)
    return Entry(
        name=mod_dir.name,
        path=mod_dir,
        has_modinfo=has_modinfo,
        is_poi_prefab_only=is_poi,
        nested_modinfos=nested,
        has_prefabs_dir=has_prefabs_dir,
        worldgen_files=wg,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods-path", default=None, help="Path to the 7DTD Mods folder")
    args = ap.parse_args()

    mods_path = args.mods_path or _load_config_mods_path(_REPO_ROOT)
    if not mods_path:
        raise SystemExit("No mods path provided and config.json has no mods_path")

    mods_dir = Path(mods_path)
    if not mods_dir.exists() or not mods_dir.is_dir():
        raise SystemExit(f"Mods path does not exist or is not a folder: {mods_dir}")

    entries: List[Entry] = []
    for child in _iter_children(mods_dir):
        entries.append(_scan_entry(child))

    not_loadable = [e for e in entries if (not e.has_modinfo) and (not e.is_poi_prefab_only)]
    wrappers = [e for e in not_loadable if e.nested_modinfos]
    poi_like = [e for e in entries if (e.is_poi_prefab_only or e.has_prefabs_dir)]
    worldgen_like = [e for e in entries if e.worldgen_files]

    print(f"Mods folder: {mods_dir}")
    print(f"Folders scanned: {len(entries)}")
    print(f"Worldgen-like (rwgmixer/biomes/etc): {len(worldgen_like)}")
    print(f"POI/prefab-like: {len(poi_like)}")
    print(f"NOT loadable (no ModInfo.xml, not prefab-only POI): {len(not_loadable)}")
    print(f"Likely wrapper/container folders (contain nested ModInfo.xml): {len(wrappers)}")

    if worldgen_like:
        print("\n=== Worldgen signals ===")
        for e in sorted(worldgen_like, key=lambda x: x.name.lower()):
            print(f"- {e.name}: {', '.join(e.worldgen_files)}")

    if poi_like:
        print("\n=== POI/Prefab signals ===")
        for e in sorted(poi_like, key=lambda x: x.name.lower()):
            tags = []
            if e.is_poi_prefab_only:
                tags.append("prefab-only")
            if e.has_prefabs_dir:
                tags.append("Prefabs/")
            if e.worldgen_files:
                tags.append("worldgen")
            print(f"- {e.name} ({', '.join(tags) if tags else 'detected'})")

    if not_loadable:
        print("\n=== NOT LOADABLE (will not deploy/load in 7DTD) ===")
        for e in sorted(not_loadable, key=lambda x: x.name.lower()):
            print(f"- {e.name}")
            if e.nested_modinfos:
                # show up to a few nested ModInfo.xml paths
                for p in e.nested_modinfos[:3]:
                    try:
                        rel = p.relative_to(e.path)
                        print(f"    contains: {rel.as_posix()}")
                    except Exception:
                        print(f"    contains: {p.name}")
        print("\nFix suggestions:")
        print("- If it’s a wrapper folder: move the inner folder that contains ModInfo.xml up into the Mods root.")
        print(
            "- If it’s supposed to be a POI pack: ensure it actually contains prefab assets + XML (or install the correct version)."
        )
        print("- If it’s a normal mod: ensure ModInfo.xml is in the mod folder root.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
