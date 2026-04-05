from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Tuple


def parse_modinfo_name_version(modinfo_path: str) -> Tuple[str, str]:
    """Best-effort parse of ModInfo.xml `Name` and `Version` values.

    Returns (name, version). Empty strings on failure.
    """

    if not modinfo_path:
        return "", ""

    try:
        tree = ET.parse(modinfo_path)
        root = tree.getroot()
    except Exception:
        return "", ""

    mi_name = ""
    mi_ver = ""

    try:
        for elem in root.iter():
            tag = (elem.tag or "").lower()
            if tag == "name" and not mi_name:
                mi_name = str(elem.attrib.get("value") or "").strip()
            elif tag == "version" and not mi_ver:
                mi_ver = str(elem.attrib.get("value") or "").strip()
            if mi_name and mi_ver:
                break
    except Exception:
        return mi_name, mi_ver

    return mi_name, mi_ver
