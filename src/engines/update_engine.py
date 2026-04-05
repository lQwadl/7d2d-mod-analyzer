from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

_DISABLED_PREFIX = "__DISABLED__"
_ORDER_PREFIX_RE = re.compile(r"^(\d+)_")

# Similar to logic.load_order.dedupe_keep_latest
_BASE_RE = re.compile(r"^(.*?)(?:[-_ ]v?\d[\w\.-]*)$")


def _strip_disabled(name: str) -> str:
    if (name or "").startswith(_DISABLED_PREFIX):
        return name[len(_DISABLED_PREFIX) :]
    return name or ""


def _strip_order_prefix(name: str) -> str:
    n = _strip_disabled(name)
    m = _ORDER_PREFIX_RE.match(n)
    if not m:
        return n
    return n[len(m.group(0)) :]


def _base_identity_from_folder(folder_name: str) -> str:
    raw = _strip_order_prefix(folder_name).strip()
    m = _BASE_RE.match(raw)
    base = (m.group(1) if m else raw).strip()
    return base.lower()


def _parse_modinfo_name_version(modinfo_path: Path) -> Tuple[str, str]:
    """Best-effort parse of ModInfo.xml -> (Name value, Version value)."""

    if not modinfo_path.exists():
        return "", ""

    try:
        tree = ET.parse(str(modinfo_path))
        root = tree.getroot()
    except Exception:
        return "", ""

    name_val = ""
    ver_val = ""
    try:
        for elem in root.iter():
            tag = (elem.tag or "").lower()
            if tag == "name" and not name_val:
                name_val = str(elem.attrib.get("value") or "").strip()
            elif tag == "version" and not ver_val:
                ver_val = str(elem.attrib.get("value") or "").strip()
    except Exception:
        pass

    return name_val, ver_val


def _version_key(v: str) -> Tuple:
    """Comparable key for versions.

    - Numeric parts sort numerically.
    - Non-numeric parts sort lexicographically after numeric.
    - Empty version sorts lowest.
    """

    s = (v or "").strip().lower()
    if not s:
        return tuple()

    # Split on non-alphanumeric boundaries; keep alnum chunks
    chunks = [c for c in re.split(r"[^0-9a-z]+", s) if c]
    out: List[Tuple[int, Any]] = []
    for c in chunks:
        if c.isdigit():
            out.append((0, int(c)))
        else:
            out.append((1, c))
    return tuple(out)


@dataclass
class Install:
    folder_name: str
    path: str
    enabled: bool
    base_id: str
    modinfo_name: str = ""
    modinfo_version: str = ""
    mtime: float = 0.0


@dataclass
class UpdateCandidate:
    base_id: str
    installs: List[Install]
    keep: Install
    to_disable: List[Install]
    to_enable: List[Install]


def _install_from_mod(mod: Any) -> Install:
    folder_name = str(getattr(mod, "name", "") or "")
    path = str(getattr(mod, "path", "") or "")
    try:
        enabled = not bool(getattr(mod, "user_disabled", False))
    except Exception:
        enabled = not folder_name.startswith(_DISABLED_PREFIX)

    # Back-compat: folder prefix always implies disabled
    if folder_name.startswith(_DISABLED_PREFIX):
        enabled = False

    modinfo_path = Path(path) / "ModInfo.xml"
    mi_name, mi_ver = _parse_modinfo_name_version(modinfo_path)

    base_id = mi_name.strip().lower() if mi_name.strip() else _base_identity_from_folder(folder_name)

    try:
        mt = os.path.getmtime(path)
    except Exception:
        mt = 0.0

    return Install(
        folder_name=folder_name,
        path=path,
        enabled=enabled,
        base_id=base_id,
        modinfo_name=mi_name,
        modinfo_version=mi_ver,
        mtime=mt,
    )


def detect_local_updates(mods: Iterable[Any]) -> List[UpdateCandidate]:
    """Detect local update situations (multiple installs of same base_id).

    The recommended action is:
    - keep the newest version (by ModInfo Version when available, else newest mtime)
    - disable older installs by renaming with __DISABLED__
    - if the newest is disabled but an older is enabled, we plan a safe swap.
    """

    installs = [_install_from_mod(m) for m in (mods or []) if getattr(m, "path", None)]

    groups: Dict[str, List[Install]] = {}
    for ins in installs:
        groups.setdefault(ins.base_id, []).append(ins)

    candidates: List[UpdateCandidate] = []
    for base_id, items in groups.items():
        if len(items) <= 1:
            continue

        def sort_key(i: Install):
            vk = _version_key(i.modinfo_version)
            # prefer version; fallback to mtime
            return (vk, i.mtime)

        items_sorted = sorted(items, key=sort_key, reverse=True)
        keep = items_sorted[0]

        to_disable = [i for i in items_sorted[1:] if i.enabled]
        to_enable = [keep] if (not keep.enabled and any(i.enabled for i in items_sorted[1:])) else []

        candidates.append(
            UpdateCandidate(
                base_id=base_id,
                installs=items_sorted,
                keep=keep,
                to_disable=to_disable,
                to_enable=to_enable,
            )
        )

    # stable ordering for UI
    candidates.sort(key=lambda c: c.base_id)
    return candidates


def _unique_name(parent: Path, desired: str) -> str:
    if not (parent / desired).exists():
        return desired
    stem = desired
    suffix = 1
    while True:
        cand = f"{stem}__{suffix}"
        if not (parent / cand).exists():
            return cand
        suffix += 1


def _rename_folder(old_path: Path, new_name: str) -> Path:
    parent = old_path.parent
    new_name = _unique_name(parent, new_name)
    new_path = parent / new_name
    old_path.rename(new_path)
    return new_path


def apply_update_actions(*, mods_root: str, candidates: List[UpdateCandidate]) -> List[str]:
    """Apply update actions by renaming folders (disable/swap). Returns human-readable actions."""
    actions: List[str] = []

    for cand in candidates:
        # Enable keep if needed
        for ins in cand.to_enable:
            p = Path(ins.path)
            if not p.exists():
                continue
            if not p.name.startswith(_DISABLED_PREFIX):
                continue
            new_name = p.name[len(_DISABLED_PREFIX) :]
            new_path = _rename_folder(p, new_name)
            actions.append(f"ENABLE: {p.name} -> {new_path.name}")
            # Update ins.path for any follow-on rename decisions (best-effort)
            ins.path = str(new_path)
            ins.folder_name = new_path.name
            ins.enabled = True

        # Disable older enabled installs
        for ins in cand.to_disable:
            p = Path(ins.path)
            if not p.exists():
                continue
            if p.name.startswith(_DISABLED_PREFIX):
                continue
            new_name = _DISABLED_PREFIX + p.name
            new_path = _rename_folder(p, new_name)
            actions.append(f"DISABLE: {p.name} -> {new_path.name}")
            ins.path = str(new_path)
            ins.folder_name = new_path.name
            ins.enabled = False

    return actions
