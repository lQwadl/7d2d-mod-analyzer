import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

from logic.conflict_memory import normalize_mod_id

PATCH_PREFIX = "999_ConflictPatch_"


def _is_patch_mod_name(name: str) -> bool:
    try:
        return (name or "").lower().startswith(PATCH_PREFIX.lower())
    except Exception:
        return False


def _timestamp() -> str:
    # Windows-safe, sortable timestamp
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_unique_dir(parent: Path, base_name: str) -> Path:
    candidate = parent / base_name
    if not candidate.exists():
        return candidate
    # If created twice in the same second
    for i in range(1, 1000):
        cand = parent / f"{base_name}_{i}"
        if not cand.exists():
            return cand
    raise RuntimeError("Unable to allocate unique patch folder name")


def _write_modinfo(mod_dir: Path, name: str, description: str, *, dependencies: list[str] | None = None) -> None:
    modinfo = mod_dir / "ModInfo.xml"

    root = ET.Element("xml")
    mi = ET.SubElement(root, "ModInfo")
    ET.SubElement(mi, "Name").set("value", name)
    ET.SubElement(mi, "Description").set("value", description)
    ET.SubElement(mi, "Author").set("value", "7DTD Mod Manager")
    ET.SubElement(mi, "Version").set("value", "1.0.0")

    deps = []
    for d in dependencies or []:
        dd = normalize_mod_id(str(d or "")).strip()
        if dd:
            deps.append(dd)
    # Deduplicate (case-insensitive) but keep stable order.
    out_deps: list[str] = []
    seen = set()
    for d in deps:
        k = d.lower()
        if k in seen:
            continue
        seen.add(k)
        out_deps.append(d)

    if out_deps:
        deps_elem = ET.SubElement(mi, "Dependencies")
        for d in out_deps:
            ET.SubElement(deps_elem, "Dependency").set("name", d)

    tree = ET.ElementTree(root)
    tree.write(str(modinfo), encoding="utf-8", xml_declaration=True)


def create_conflict_patch(mods_root: str, conflicts, prefer: str, *, output_root: str | None = None) -> Path:
    """Create a patch mod for a list of ConflictTrace.

    - Creates: Mods/999_ConflictPatch_<timestamp>/ModInfo.xml + Config/<file>.xml
    - Uses <set xpath="...">winner_value</set> per conflict

    Returns the created patch directory.

    Raises RuntimeError on hard-fail conditions.
    """
    if prefer not in ("A", "B"):
        raise RuntimeError(f"Invalid prefer value: {prefer}")

    if not conflicts:
        raise RuntimeError("No conflicts selected")

    mods_root_p = Path(mods_root)
    if not mods_root_p.exists() or not mods_root_p.is_dir():
        raise RuntimeError(f"Mods path does not exist: {mods_root}")

    out_root = Path(output_root) if output_root else mods_root_p
    if not out_root.exists():
        out_root.mkdir(parents=True, exist_ok=True)
    if not out_root.is_dir():
        raise RuntimeError(f"Patch output root is not a directory: {out_root}")

    # Only support XML override conflicts from mock deploy for now.
    supported = []
    for ct in conflicts:
        kind = getattr(ct, "kind", None)
        if kind != "override":
            raise RuntimeError(f"Unsupported conflict type: {kind}")
        if not getattr(ct, "file", None) or not getattr(ct, "xpath", None):
            raise RuntimeError("Conflict missing file/xpath")
        if not getattr(ct, "first", None) or not getattr(ct, "second", None):
            raise RuntimeError("Conflict missing involved mods")
        if _is_patch_mod_name(getattr(ct.first, "mod", "")) or _is_patch_mod_name(getattr(ct.second, "mod", "")):
            # Don't generate patches against patch mods
            continue
        supported.append(ct)

    if not supported:
        raise RuntimeError("No supported conflicts to patch")

    base_name = f"{PATCH_PREFIX}{_timestamp()}"
    patch_dir = _ensure_unique_dir(out_root, base_name)

    try:
        patch_dir.mkdir(parents=True, exist_ok=False)
        cfg_dir = patch_dir / "Config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Failed to create patch folder: {e}")

    summaries = []
    deps_set: list[str] = []
    deps_seen = set()
    # group by file
    by_file = {}
    for ct in supported:
        winner = ct.first if prefer == "A" else ct.second
        winner_mod = getattr(winner, "mod", "")
        loser_mod = ct.second.mod if prefer == "A" else ct.first.mod
        summaries.append(f"{ct.file}:{ct.xpath} — {winner_mod} wins over {loser_mod}")
        by_file.setdefault(ct.file, []).append((ct.xpath, str(getattr(winner, "value", ""))))

        # Add both involved mods as dependencies so the patch loads after them.
        for raw in (getattr(ct.first, "mod", ""), getattr(ct.second, "mod", "")):
            dep = normalize_mod_id(str(raw or "")).strip()
            if not dep:
                continue
            k = dep.lower()
            if k in deps_seen:
                continue
            deps_seen.add(k)
            deps_set.append(dep)

    description = f"Auto-generated conflict patch ({len(supported)} fixes)"
    _write_modinfo(patch_dir, patch_dir.name, description, dependencies=deps_set)

    wrote_any = False
    for file_name, entries in by_file.items():
        root = ET.Element("configs")
        for xpath, value in entries:
            node = ET.SubElement(root, "set")
            node.set("xpath", xpath)
            node.text = value
        tree = ET.ElementTree(root)
        out_path = cfg_dir / file_name
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tree.write(str(out_path), encoding="utf-8", xml_declaration=True)
            wrote_any = True
        except Exception as e:
            raise RuntimeError(f"Failed to write patch XML '{file_name}': {e}")

    if not wrote_any:
        raise RuntimeError("No XML nodes were extracted")

    # Final verification
    if not (patch_dir / "ModInfo.xml").exists():
        raise RuntimeError("ModInfo.xml was not written")

    return patch_dir


def create_stabilizing_patch(
    mods_root: str,
    *,
    state,
    conflicts,
    output_root: str | None = None,
) -> Path:
    """Create a stabilizing patch mod from a simulator XMLState.

    Unlike `create_conflict_patch` (which only supports strict override conflicts), this
    patch encodes the simulator's final result per (file,xpath):
      - if final op removes the node: <remove xpath="..." />
      - otherwise: <set xpath="...">final_value</set>

    This is the closest thing we can safely do to "merge compatible nodes" using the
    current simulator model without deep XML AST merging.
    """

    if not conflicts:
        raise RuntimeError("No conflicts selected")
    if state is None:
        raise RuntimeError("Missing simulator state")

    mods_root_p = Path(mods_root)
    if not mods_root_p.exists() or not mods_root_p.is_dir():
        raise RuntimeError(f"Mods path does not exist: {mods_root}")

    out_root = Path(output_root) if output_root else mods_root_p
    if not out_root.exists():
        out_root.mkdir(parents=True, exist_ok=True)
    if not out_root.is_dir():
        raise RuntimeError(f"Patch output root is not a directory: {out_root}")

    # group by file -> list of (op, xpath, value)
    by_file = {}
    deps_set: list[str] = []
    deps_seen = set()

    values = getattr(state, "values", None)
    last_mut = getattr(state, "last_mut", None)
    if not isinstance(values, dict) or not isinstance(last_mut, dict):
        raise RuntimeError("Invalid simulator state: missing values/last_mut")

    supported = []
    for ct in conflicts:
        try:
            if not getattr(ct, "file", None) or not getattr(ct, "xpath", None):
                continue
            if not getattr(ct, "first", None) or not getattr(ct, "second", None):
                continue
            if _is_patch_mod_name(getattr(ct.first, "mod", "")) or _is_patch_mod_name(getattr(ct.second, "mod", "")):
                continue
            supported.append(ct)
        except Exception:
            continue

    if not supported:
        raise RuntimeError("No supported conflicts to stabilize")

    for ct in supported:
        key = (str(getattr(ct, "file", "") or ""), str(getattr(ct, "xpath", "") or ""))
        lm = last_mut.get(key)
        if not lm:
            continue

        final_op = str(getattr(lm, "op", "") or "").strip().lower()
        xpath = str(getattr(ct, "xpath", "") or "")
        file_name = str(getattr(ct, "file", "") or "")

        if final_op == "remove":
            by_file.setdefault(file_name, []).append(("remove", xpath, ""))
        else:
            # set to the final computed value (covers set and append)
            val = str(values.get(key, ""))
            by_file.setdefault(file_name, []).append(("set", xpath, val))

        # dependencies: include all involved mods so patch loads after them
        for raw in (getattr(ct.first, "mod", ""), getattr(ct.second, "mod", "")):
            dep = normalize_mod_id(str(raw or "")).strip()
            if not dep:
                continue
            k = dep.lower()
            if k in deps_seen:
                continue
            deps_seen.add(k)
            deps_set.append(dep)

    # Allocate folder
    base_name = f"{PATCH_PREFIX}{_timestamp()}_stabilized"
    patch_dir = _ensure_unique_dir(out_root, base_name)

    try:
        patch_dir.mkdir(parents=True, exist_ok=False)
        cfg_dir = patch_dir / "Config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Failed to create patch folder: {e}")

    description = f"Auto-generated stabilizing patch ({len(supported)} targets)"
    _write_modinfo(patch_dir, patch_dir.name, description, dependencies=deps_set)

    wrote_any = False
    for file_name, entries in by_file.items():
        root = ET.Element("configs")
        seen_keys = set()
        for op, xpath, value in entries:
            k = (op, xpath)
            if k in seen_keys:
                continue
            seen_keys.add(k)
            node = ET.SubElement(root, op)
            node.set("xpath", xpath)
            if op == "set":
                node.text = value
        tree = ET.ElementTree(root)
        out_path = cfg_dir / file_name
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tree.write(str(out_path), encoding="utf-8", xml_declaration=True)
            wrote_any = True
        except Exception as e:
            raise RuntimeError(f"Failed to write stabilizing patch XML '{file_name}': {e}")

    if not wrote_any:
        raise RuntimeError("No XML nodes were extracted")
    if not (patch_dir / "ModInfo.xml").exists():
        raise RuntimeError("ModInfo.xml was not written")

    return patch_dir
