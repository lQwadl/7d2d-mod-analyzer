from __future__ import annotations

import os
import re
from typing import Optional, Tuple


_XP_ATTR_RE = re.compile(r"@([a-zA-Z_][\w\-\.]*)")
_ORDER_PREFIX_RE = re.compile(r"^(\d+)_")


def _norm_path(p: str) -> str:
    return str(p or "").replace("\\", "/").strip().lower()


def _split_target(target: str) -> Tuple[str, str]:
    t = str(target or "").strip()
    if not t:
        return "", ""
    if "/" not in t:
        return t, ""
    head, tail = t.split("/", 1)
    return head, tail


def xpath_to_target(xpath: str) -> str:
    """Best-effort conversion from an XPath to our stable target format.

    Kept intentionally compatible with `scanner.xml_analyzer._target_from_xpath`,
    but placed in logic so engines can format simulator xpaths without importing
    scanner internals.
    """

    if not xpath:
        return ""

    xp = str(xpath).strip()
    xp = xp.lstrip("/")
    segs = [s for s in xp.split("/") if s and s not in (".", "..")]

    parts = []
    for seg in segs:
        seg = (seg or "").strip()
        if not seg:
            continue

        if seg.startswith("@") and len(seg) > 1:
            parts.append(f"attr:{seg[1:]}")
            continue

        tag = seg
        predicate = ""
        if "[" in seg and "]" in seg:
            tag, rest = seg.split("[", 1)
            predicate = rest.rsplit("]", 1)[0]
        tag = (tag or "").strip()
        if not tag:
            continue

        ident = None
        if predicate:
            for key in ("name", "id", "key"):
                m = re.search(rf"@{key}\s*=\s*(['\"])(.*?)\1", predicate)
                if m:
                    ident = m.group(2)
                    break

        parts.append(f"{tag}:{ident}" if ident else tag)

    if not parts:
        return str(xpath).strip()

    if parts[-1].startswith("attr:") and len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"

    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"

    return parts[-1]


def format_target_display(*, file: str = "", target: str = "") -> str:
    """Human-friendly target label for UI; does not need to be stable."""

    f = _norm_path(file)
    t = str(target or "").strip()
    if not t:
        return ""

    # Assets: target is `asset:<relpath>`
    if t.lower().startswith("asset:"):
        rel = t.split(":", 1)[1].strip().replace("\\", "/")
        base = os.path.basename(rel)
        ext = os.path.splitext(base)[1].lower()
        kind = "asset"
        if ext in {".png", ".jpg", ".jpeg", ".tga", ".dds"}:
            kind = "texture"
        elif ext in {".wav", ".ogg", ".mp3"}:
            kind = "audio"
        elif ext in {".mesh", ".prefab", ".unity3d", ".blocks.nim", ".ins", ".tts"}:
            kind = "model/prefab"
        return f"{kind}: {base}"

    # Simulator xpaths: show a compact derived label
    if t.startswith("/") or t.startswith("//"):
        tt = xpath_to_target(t)
        if tt and tt != t:
            return format_target_display(file=file, target=tt)
        return f"XPath: {t}"

    head, tail = _split_target(t)
    head = head.strip()
    tail = tail.strip()

    node_type = head
    node_id = ""
    if ":" in head:
        node_type, node_id = head.split(":", 1)

    node_type_l = (node_type or "").strip().lower()
    label_map = {
        "item": "Item",
        "items": "Item",
        "recipe": "Recipe",
        "recipes": "Recipe",
        "lootgroup": "Loot group",
        "lootcontainer": "Loot container",
        "block": "Block",
        "buff": "Buff",
        "perk": "Perk",
        "progression": "Progression",
        "entity": "Entity",
        "entityclass": "Entity",
        "entityclasses": "Entity",
        "entity_class": "Entity",
    }
    label = label_map.get(node_type_l, node_type or "Target")

    out = label
    if node_id:
        out += f" {node_id}"

    if tail:
        nice = tail
        nice = nice.replace("property:", "property ")
        nice = nice.replace("attr:", "attr ")
        nice = nice.replace("/", " → ")
        out += f" → {nice}"

    # File-based hints (when target doesn't carry a strong prefix)
    if not node_id and f in {"recipes.xml", "items.xml", "entityclasses.xml", "progression.xml", "loot.xml"}:
        out = f"{os.path.basename(f)} → {out}"

    return out.strip()
