import os
import xml.etree.ElementTree as ET
import re

SYSTEM_MAP = {
    "progression.xml": "Progression",
    "loot.xml": "Loot",
    "blocks.xml": "Blocks",
    "entityclasses.xml": "Entities",
    "items.xml": "Items",
    "ui.xml": "UI",
    "windows.xml": "UI",
}


def _identify_element_base(elem):
    # Prefer 'name' attribute, then id/key attributes as identifier
    for key in ("name", "id", "key"):
        if key in elem.attrib:
            return f"{elem.tag}:{elem.attrib.get(key)}"
    # Fallback to tag with positionless marker
    return f"{elem.tag}:<unknown>"


def _extract_targets_from_tree(root):
    targets = set()

    for elem in root.iter():
        base = _identify_element_base(elem)

        # record attribute changes on this element (excluding name/id/key)
        for attr, val in elem.attrib.items():
            if attr in ("name", "id", "key"):
                continue
            targets.add(f"{base}/attr:{attr}")

        # inspect children that look like properties (have 'name' attrib or are property-like)
        for child in list(elem):
            # child with name attribute
            if "name" in child.attrib:
                child_ident = child.attrib.get("name") or child.tag
                targets.add(f"{base}/{child.tag}:{child_ident}")
                # also include attributes of the child
                for attr in child.attrib:
                    if attr == "name":
                        continue
                    targets.add(f"{base}/{child.tag}:{child_ident}/attr:{attr}")
            else:
                # child without name but with attributes
                if child.attrib:
                    # use child's tag as identifier
                    targets.add(f"{base}/{child.tag}")
                    for attr in child.attrib:
                        targets.add(f"{base}/{child.tag}/attr:{attr}")

    return targets


def _target_from_xpath(xpath: str) -> str:
    """Best-effort conversion from an XPath to the existing target format.

    Examples:
      //items/item[@name='gunAK47']/property[@name='Quality'] -> item:gunAK47/property:Quality
      //lootcontainers/lootgroup[@name='x']/@prob -> lootgroup:x/attr:prob
    """
    if not xpath:
        return ""

    # Strip common prefixes and split into segments
    xp = xpath.strip()
    xp = xp.lstrip("/")
    segs = [s for s in xp.split("/") if s and s not in (".", "..")]

    parts = []
    for seg in segs:
        seg = seg.strip()
        if not seg:
            continue
        # Attribute selector segment: @foo
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
            # Prefer name/id/key selectors
            for key in ("name", "id", "key"):
                m = re.search(rf"@{key}\s*=\s*(['\"])(.*?)\1", predicate)
                if m:
                    ident = m.group(2)
                    break

        parts.append(f"{tag}:{ident}" if ident else tag)

    if not parts:
        return xpath.strip()

    # If the last part is an attr selector, include its parent
    if parts[-1].startswith("attr:") and len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"

    # Use the last two meaningful parts when possible
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return parts[-1]


def analyze_xml(mod):
    mod_root = os.path.join(mod.path)
    if not os.path.isdir(mod_root):
        return

    def _iter_xml_roots() -> list[str]:
        roots = []
        # Canonical 7DTD data patches
        cfg = os.path.join(mod_root, "Config")
        if os.path.isdir(cfg):
            roots.append(cfg)

        # UI/XUi patches commonly live outside Config.
        # We include common top-level folders like XUi, XUI_Common, XUI_Menu, etc.
        try:
            for entry in os.listdir(mod_root):
                full = os.path.join(mod_root, entry)
                if not os.path.isdir(full):
                    continue
                el = (entry or "").strip().lower()
                if el == "xui" or el.startswith("xui_"):
                    roots.append(full)
        except Exception:
            pass

        # Deduplicate while preserving order
        out = []
        seen = set()
        for r in roots:
            k = os.path.normpath(r).lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
        return out

    xml_roots = _iter_xml_roots()
    if not xml_roots:
        return

    for scan_root in xml_roots:
        for root_dir, _, files in os.walk(scan_root):
            for file in files:
                if not str(file).lower().endswith(".xml"):
                    continue

                file_path = os.path.join(root_dir, file)

                # Keying:
                # - For Config patches keep legacy keys (basename lowercase: items.xml, blocks.xml, etc)
                # - For UI/other roots keep relative path from mod root (lowercase, forward slashes)
                try:
                    if os.path.normpath(scan_root).lower().endswith(os.path.normpath("Config").lower()):
                        name = str(file).lower()
                    else:
                        rel = os.path.relpath(file_path, mod_root)
                        name = str(rel).replace("\\", "/").lower()
                except Exception:
                    name = str(file).lower()

                if name.endswith("/modinfo.xml") or name == "modinfo.xml":
                    continue

                if name in SYSTEM_MAP:
                    mod.xml_files.add(name)
                    mod.systems.add(SYSTEM_MAP[name])

                # Attempt to parse XML, extract semantic edits and heuristic targets
                try:
                    tree = ET.parse(file_path)
                    rt = tree.getroot()

                    # If this file contains xpath-based patch operations, prefer those as targets.
                    # This avoids blanket false positives from scanning the patch file structure itself.
                    has_xpath_ops = False
                    for _e in rt.iter():
                        if _e.attrib.get("xpath"):
                            has_xpath_ops = True
                            break

                    if not has_xpath_ops:
                        found = _extract_targets_from_tree(rt)
                        if found:
                            mod.xml_targets.setdefault(name, set()).update(found)

                    # Semantic edits: detect xpath-based patch operations
                    for elem in rt.iter():
                        op = elem.tag.lower()
                        xpath = elem.attrib.get("xpath")
                        if not xpath:
                            continue

                        # Map operation to intent
                        if op in ("append", "insert", "add", "insertbefore", "insertafter"):
                            intent = "extend"
                        elif op in ("set", "update"):
                            intent = "override"
                        elif op in ("replace",):
                            intent = "replace"
                        elif op in ("remove", "delete"):
                            intent = "remove"
                        else:
                            intent = "modify"

                        # Derive a stable target from the xpath for conflict detection
                        try:
                            target = _target_from_xpath(xpath)
                        except Exception:
                            target = xpath.strip()

                        val_text = (elem.text or "").strip()
                        system = SYSTEM_MAP.get(name, None)
                        edit = {
                            "file": name,
                            "system": system,
                            "xpath": xpath,
                            "op": op,
                            "intent": intent,
                            "target": target,
                            "value": val_text,
                        }
                        try:
                            mod.semantic_edits.append(edit)
                        except Exception:
                            # ensure attribute exists even for GUI Mod shim
                            if not hasattr(mod, "semantic_edits"):
                                setattr(mod, "semantic_edits", [])
                            mod.semantic_edits.append(edit)

                        # Also record the xpath-derived target as a heuristic target so we can
                        # still detect overlaps even when another mod lacks semantic edits.
                        try:
                            mod.xml_targets.setdefault(name, set()).add(target)
                        except Exception:
                            pass
                except ET.ParseError:
                    # mark unparsable XML for integrity/status purposes
                    try:
                        setattr(mod, "invalid_xml", True)
                    except Exception:
                        pass
                    continue
